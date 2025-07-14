import pytest
from app import create_app, db
from app.cli import register as register_cli
import app.models as models
from config import TestConfig
from flask_migrate import upgrade
from flask import url_for
from urllib.parse import urlparse
from urllib.parse import parse_qs
import click
import tempfile
import os
import shutil
import sqlalchemy as sa
from typing import Tuple, Generator
from flask.testing import FlaskClient
from pathlib import Path
from app.helpers.admin_helpers import get_enumerated_objects
import json
from sqlalchemy.inspection import inspect
import datetime
from xml.etree import ElementTree


@pytest.fixture(scope="module")
def client() -> Generator[Tuple[FlaskClient, int]]:
    tmpfile = tempfile.mktemp()
    basedir = str(Path(__file__).parent)
    if not os.path.isdir(basedir + '/tmp'):
        os.mkdir(basedir + '/tmp')
    shutil.copy(TestConfig.SQLALCHEMY_DATABASE_URI.split(":///", 2)[1].split("?", 2)[0], tmpfile)
    new_sqlalchemy_database_uri = TestConfig.SQLALCHEMY_DATABASE_URI.split(":///", 2)[0] + ":///" + tmpfile
    if len(TestConfig.SQLALCHEMY_DATABASE_URI.split("?", 2)) == 2:
        new_sqlalchemy_database_uri += "?" + TestConfig.SQLALCHEMY_DATABASE_URI.split("?", 2)[1]
    class CurrentTestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = new_sqlalchemy_database_uri
        ACTIVATE_PASSWORD_POLICY = False
    app = create_app(CurrentTestConfig)
    register_cli(app)
    app.testing = True
    app.config['SERVER_NAME'] = 'localhost'
    app.config['APPLICATION_ROOT'] = '/'
    app.config['ACTIVATE_PASSWORD_POLICY'] = False
    app.app_context().push()
    upgrade()
    app.setting_custom_attributes_for_application()
    client = app.test_client()
    # authorization
    response_with_cookie = client.post(url_for('users.user_login', _external=False), data={'login': 'admin', 'password': 'admin'})
    yield client


def test_open_pages(client: FlaskClient):
    index_page = client.get(url_for('admin.index', _external=False))
    assert index_page.status_code == 200, f"Admin index status code is {index_page.status_code}"
    main_page_setting_edit = client.get(url_for('admin.admin_main_info_edit', _external=False))
    assert main_page_setting_edit.status_code == 200, f"Admin page - main page settings status code is {main_page_setting_edit.status_code}"
    object_index = client.get(url_for('admin.object_index', _external=False))
    assert object_index.status_code == 200, f"Admin page - enumerated object index status code is {object_index.status_code}"


def test_open_all_object_type_index(client: FlaskClient):
    for object_type in get_enumerated_objects():
        curr_object_index = client.get(url_for('admin.object_type_index', object_type=object_type.__name__, _external=False))
        assert curr_object_index.status_code == 200, f"Cannot get enumerated object index for object {object_type.__name__}: status_code {curr_object_index.status_code}"
        curr_object_index_data = client.get(url_for('admin.object_type_index_data', _external=False, object_type=object_type.__name__,
                                                    **{"search": "", "limit": 10, "offset": 0})) # ?search=&offset=0&limit=10&filter=%7B%22title%22%3A%22%D0%92%D1%8B%D1%81%22%7D
        assert curr_object_index_data.status_code == 200, f"Cannot get current object index data for {object_type.__name__} without parameters"
        all_curr_object_index_data = client.get(url_for('admin.object_type_index_data', _external=False, object_type=object_type.__name__,
                                                    **{"search": ""}))
        assert all_curr_object_index_data.status_code == 200, f"Cannot get all current object data for {object_type.__name__} without parameters"
        any_object = db.session.scalars(sa.select(object_type)).first()
        attr_name = [i.name for i in inspect(object_type).columns if not i.name.endswith('_id')]
        attr_name += [i.key for i in inspect(object_type).relationships]
        simple_names = [i.name for i in inspect(object_type).columns]
        # test search by all column_index in object
        for column in any_object.Meta.column_index:
            if column in simple_names:
                search_index_data = client.get(url_for('admin.object_type_index_data', _external=False, object_type=object_type.__name__,
                                                        **{"search": str(getattr(any_object, column)), "limit": 10, "offset": 0}))
                assert search_index_data.status_code == 200, f"Cannot get enumerated object index data with search by simple attr {column}"
                if getattr(any_object, column) is not None and not isinstance(getattr(any_object, column), bool):
                    assert int(search_index_data.get_json()["total"]) >= 1, f"search by all column when use field `{column}`for object {object_type.__name__} id {any_object.id} return an {search_index_data.get_json()["total"]} unexpected objects in total"
                assert len(search_index_data.get_json()["rows"]) <= 10, f"search by all column for object {any_object.id} return an {len(search_index_data.get_json()["rows"])}, when expected <= 10"
                search_column_only = client.get(url_for('admin.object_type_index_data', _external=False, object_type=object_type.__name__,
                                                        **{"limit": 10, "offset": 0, "filter": json.dumps({column: getattr(any_object, column)})}))
                assert search_column_only.status_code == 200, f"Cannot get enumerated object index data with search by simple attr column {column}"
                if getattr(any_object, column) is not None and not isinstance(getattr(any_object, column), bool):
                    assert int(search_column_only.get_json()["total"]) >= 1 and getattr(any_object, column) is not None, f"search by one column for object {any_object.id} return an {search_column_only.get_json()["total"]} unexpected results"
                assert len(search_column_only.get_json()["rows"]) <= 10, f"Search by one column for object {any_object.id} return an {len(search_column_only.get_json()["rows"])}, but expected <= 10"
            # relationships - maybe later...

def test_create_new_object_type(client: FlaskClient):
    for object_type in get_enumerated_objects():
        # test open page
        open_request = client.get(url_for('admin.object_type_new', object_type=object_type.__name__, _external=False))
        assert open_request.status_code == 200, f'Cannot open page to add new object type for {object_type}: status_code is {open_request.status_code}'
        # wrong create request
        wrong_create_request = client.post(url_for('admin.object_type_new', _external=False, object_type=object_type.__name__), follow_redirects=True)
        assert wrong_create_request.status_code == 200, f"We can create an empty object type: {object_type.__name__}"
        assert len(wrong_create_request.history) == 0, f"History length for create empty object type is not 0: {len(wrong_create_request.history)}"
        # good create request
        options = {}
        for column in inspect(object_type).columns:
            if column.name == 'id' or column.name.endswith('_id') or ('on_form' in column.info and not column.info['on_form']):
                continue
            if column.name == 'string_slug':
                options['string_slug'] = 'test_add_new'
            elif column.type.__class__.__name__ == 'String' or column.type.__class__.__name__ == 'LimitedLengthString':
                options[column.name] = 'Test add new'
                if column.type.length is not None:
                    options[column.name] = options[column.name][:column.type.length]
            elif column.type.__class__.__name__ == 'Integer':
                options[column.name] = 42
            elif column.type.__class__.__name__ == 'Float':
                options[column.name] = 3.1415
            elif column.type.__class__.__name__ == 'DateTime':
                options[column.name] = datetime.datetime.now(datetime.UTC)
            elif column.type.__class__.__name__ == 'Boolean':
                pass # Если False - то параметр просто не передаётся с формой. Иначе - передаётся, и что бы в нём не передалось - будет считаться как True
        for rel_name, rel in inspect(object_type).relationships.items():
            if 'on_form' in rel.info and not rel.info['on_form']:
                continue
            if not rel.uselist:
                # Это простая ссылка - т. е. не список. Тогда создаём простой SelectField:
                options[rel_name] = '0'
            else:
                options[rel_name] = []
        good_create_request = client.post(url_for('admin.object_type_new', _external=False, object_type=object_type.__name__), follow_redirects=True,
                                          data=options)
        assert good_create_request.status_code == 200, f"Status code of good create request for object {object_type.__name__} with options {options} are not 200: {good_create_request.status_code}"
        element_tree = ... # HTML parser - ? - search 'Not a valid choice' and get field name
        assert urlparse(good_create_request.request.url).path == url_for('admin.object_type_index', _external=False, object_type=object_type.__name__), f"Redirect after create object is not to object_type_index for object {object_type.__name__}. Redirect to {urlparse(good_create_request.request.url).path}, options: {options}"
        if hasattr(object_type, 'string_slug'):
            new_objects = db.session.scalars(sa.select(object_type).where(object_type.string_slug == 'test_add_new')).all()
            assert len(new_objects) == 1, f"Length of new created object for {object_type.__name__} is {len(new_objects)}. Options: {options}"
            for option_name, option_value in options.items():
                if option_value == '0' or option_value == []:
                    continue
                assert getattr(new_objects[0], option_name) == option_value, f"Cannot create attribute {option_name} with value {option_value} on object {object_type.__name__}. Current value: {getattr(new_objects[0], option_name)}"

def test_edit_new_object_type(client: FlaskClient):
    # test open page
    for object_type in get_enumerated_objects():
        obj = db.session.scalars(sa.select(object_type)).first()
        open_request = client.get(url_for('admin.object_type_edit', _external=False, object_type=object_type.__name__, object_id=obj.id))
        assert open_request.status_code == 200, f"Object of type {object_type.__name__} with id {obj.id} do not open to edit. Status code: {open_request.status_code}"
        options = {}
        for column in inspect(object_type).columns:
            if column.name == 'id' or column.name.endswith('_id') or ('on_form' in column.info and not column.info['on_form']):
                continue
            if column.name == 'string_slug':
                options['string_slug'] = 'test_edit_new'
            elif column.type.__class__.__name__ == 'String' or column.type.__class__.__name__ == 'LimitedLengthString':
                options[column.name] = 'Test another one'
                if column.type.length is not None:
                    options[column.name] = options[column.name][:column.type.length]
            elif column.type.__class__.__name__ == 'Integer':
                options[column.name] = 52
            elif column.type.__class__.__name__ == 'Float':
                options[column.name] = 2.718281828
            elif column.type.__class__.__name__ == 'DateTime':
                options[column.name] = datetime.datetime.now(datetime.UTC)
            elif column.type.__class__.__name__ == 'Boolean':
                options[column.name] = True
        for rel_name, rel in inspect(object_type).relationships.items():
            if 'on_form' in rel.info and not rel.info['on_form']:
                continue
            if not rel.uselist:
                options[rel_name] = '0'
            else:
                options[rel_name] = []
        # test edit our created object
        if hasattr(object_type, 'string_slug'):
            curr_obj = db.session.scalars(sa.select(object_type).where(object_type.string_slug == 'test_add_new')).first()
            assert curr_obj is not None, f"Cannot find object of type {object_type.__name__} with string_slug test_add_new"
            options['id'] = curr_obj.id
            edit_request = client.post(url_for('admin.object_type_edit', _external=False, object_type=object_type.__name__, object_id=curr_obj.id), follow_redirects=True, data=options)
            assert edit_request.status_code == 200, f"Status code of edit enumerated object for object_type {object_type.__name__} is not 200"
            assert urlparse(edit_request.request.url).path == url_for('admin.object_type_index', _external=False, object_type=object_type.__name__), f"Redirect after edit object is not to object_type_index for object {object_type.__name__}. Redirect to {urlparse(edit_request.request.url).path}, options: {options}. Invalid-feedback: {'invalid-feedback' in edit_request.text}"
            new_curr_obj = db.session.scalars(sa.select(object_type).where(object_type.string_slug == 'test_edit_new')).first()
            assert new_curr_obj is not None, f"Cannot find current object of type {object_type.__name__} after edit request"
            for option_name, option_value in options.items():
                if option_value == '0' or option_value == []:
                    continue
                assert getattr(new_curr_obj, option_name) == option_value, f"Cannot change attribute {option_name} to {option_value} to object {object_type.__name__}"
        else:
            curr_obj = db.session.scalars(sa.select(object_type)).first()
            assert curr_obj is not None, f"Cannot find object of type {object_type.__name__} without string_slug"
            options['id'] = curr_obj.id
            edit_request = client.post(url_for('admin.object_type_edit', _external=False, object_type=object_type.__name__, object_id=curr_obj.id), follow_redirects=True, data=options)
            assert edit_request.status_code == 200, f"Status code of edit enumerated object for object_type {object_type.__name__} is not 200"
            assert urlparse(edit_request.request.url).path == url_for('admin.object_type_index', _external=False, object_type=object_type.__name__), f"Redirect after edit object is not to object_type_index for object {object_type.__name__}. Redirect to {urlparse(edit_request.request.url).path}, options: {options}. Invalid-feedback: {'invalid-feedback' in edit_request.text}"
            new_curr_obj = db.session.scalars(sa.select(object_type).where(object_type.id == curr_obj.id)).first()
            assert new_curr_obj is not None, f"Cannot find current object of type {object_type.__name__} after edit request without string_slug. ID: {curr_obj.id}"
            for option_name, option_value in options.items():
                if option_value == '0' or option_value == []:
                    continue
                assert getattr(new_curr_obj, option_name) == option_value, f"Cannot change attribute {option_name} to {option_value} to object {object_type.__name__}"

def test_delete_object_type(client: FlaskClient):
    for object_type in get_enumerated_objects():
        if hasattr(object_type, 'string_slug'):
            obj_id = db.session.scalars(sa.select(object_type.id).where(object_type.string_slug == 'test_edit_new')).first()
        else:
            obj_id = db.session.scalars(sa.select(object_type.id)).first()
        assert obj_id is not None, f"Cannot find any object of type {object_type.__name__}"
        resp = client.post(url_for('admin.object_type_delete', _external=False, object_type=object_type.__name__), follow_redirects=True, data={'id': obj_id})
        assert resp.status_code == 200, f"Cannot redirect to page after delete object {object_type.__name__} with id {obj_id}: Status code == {resp.status_code}"
        assert urlparse(resp.request.url).path == url_for('admin.object_type_index', _external=False, object_type=object_type.__name__), f"Redirect url after delete object {object_type.__name__} is not to object index: {urlparse(resp.request.url).path}"
        obj = db.session.get(object_type, obj_id)
        assert obj is None, f"Object {object_type.__name__} with ID {obj_id} was not deleted from database"