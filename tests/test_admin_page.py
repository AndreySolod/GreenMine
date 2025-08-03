from app import db
import app.models as models
from flask import url_for
from urllib.parse import urlparse
import sqlalchemy as sa
from flask.testing import FlaskClient
from app.helpers.admin_helpers import get_enumerated_objects, get_status_objects
import json
from sqlalchemy.inspection import inspect
import datetime


def test_open_pages(auth_client: FlaskClient):
    index_page = auth_client.get(url_for('admin.index', _external=False))
    assert index_page.status_code == 200, f"Admin index status code is {index_page.status_code}"
    main_page_setting_edit = auth_client.get(url_for('admin.admin_main_info_edit', _external=False))
    assert main_page_setting_edit.status_code == 200, f"Admin page - main page settings status code is {main_page_setting_edit.status_code}"
    object_index = auth_client.get(url_for('admin.object_index', _external=False))
    assert object_index.status_code == 200, f"Admin page - enumerated object index status code is {object_index.status_code}"
    status_index = auth_client.get(url_for('admin.status_index', _external=False))
    assert status_index.status_code == 200, f"Admin page - cannot open status_index page. Status code is {status_index.status_code}"
    issue_template_index = auth_client.get(url_for('admin.issue_template_index', _external=False))
    assert issue_template_index.status_code == 200, f"Admin page - cannot open issue_template index page. Status code is {issue_template_index.status_code}"
    object_template_list = auth_client.get(url_for('admin.object_template_list', _external=False))
    assert object_template_list.status_code == 200, f"Admin page - cannot open object with template list page. Status code is {object_template_list.status_code}"


def test_edit_main_parameters(auth_client: FlaskClient):
    edit_main_page_name = auth_client.post(url_for('admin.admin_main_info_edit', _external=False, edit_elem="main_page_name"), data={'main_page_name': "Test main page"})
    assert edit_main_page_name.status_code == 200, f"Cannot edit main page name - status_code is {edit_main_page_name.status_code}"
    assert edit_main_page_name.json["status"] == 'success', f"Status of edit main page name is not success"
    gs = db.session.scalars(sa.select(models.GlobalSettings)).one()
    assert gs.main_page_name == "Test main page", f"Cannot change main page name in database"
    edit_text_main_page = auth_client.post(url_for('admin.admin_main_info_edit', _external=False, edit_elem='text_main_page'), data={'text_main_page': "Test edit text main page"}, follow_redirects=True)
    assert edit_text_main_page.status_code == 200, f"Cannot edit text main page - status_code is {edit_text_main_page.status_code}"
    assert urlparse(edit_text_main_page.request.url).path == url_for('admin.admin_main_info_edit', _external=False), f"Redirect after edit text_main_page is not to admin main info edit"
    gs = db.session.scalars(sa.select(models.GlobalSettings)).one()
    assert gs.text_main_page == "Test edit text main page", f"Text main page is not changed in database"
    main_parameters = auth_client.post(url_for('admin.admin_main_info_edit', _external=False, edit_elem="main_parameters"), data={'default_language': "1", "m2m_join_symbol": "...", "m2m_max_items": 15, "pagination_element_count_select2": 7}, follow_redirects=True)
    assert main_parameters.status_code == 200, f"Admin page - Cannot edit main parameters of application - status_code of request is {main_parameters.status_code}"
    assert urlparse(main_parameters.request.url).path == url_for('admin.admin_main_info_edit', _external=False), f"Admin page - redirect after edit main parameters are not to main info edit page"
    gs = db.session.scalars(sa.select(models.GlobalSettings)).one()
    assert gs.default_language_id == 1, f"Cannot change default language in database"
    assert gs.m2m_join_symbol == "...", f"Cannot change m2m_join_symbol in database"
    assert gs.m2m_max_items == 15, f"Cannot change m2m_max_items in database"
    assert gs.pagination_element_count_select2 == 7, f"Cannot change pagination_element_count_select2 in database"


def test_open_all_object_type_index(auth_client: FlaskClient):
    for object_type in get_enumerated_objects():
        curr_object_index = auth_client.get(url_for('admin.object_type_index', object_type=object_type.__name__, _external=False))
        assert curr_object_index.status_code == 200, f"Cannot get enumerated object index for object {object_type.__name__}: status_code {curr_object_index.status_code}"
        curr_object_index_data = auth_client.get(url_for('admin.object_type_index_data', _external=False, object_type=object_type.__name__,
                                                    **{"search": "", "limit": 10, "offset": 0})) # ?search=&offset=0&limit=10&filter=%7B%22title%22%3A%22%D0%92%D1%8B%D1%81%22%7D
        assert curr_object_index_data.status_code == 200, f"Cannot get current object index data for {object_type.__name__} without parameters"
        all_curr_object_index_data = auth_client.get(url_for('admin.object_type_index_data', _external=False, object_type=object_type.__name__,
                                                    **{"search": ""}))
        assert all_curr_object_index_data.status_code == 200, f"Cannot get all current object data for {object_type.__name__} without parameters"
        any_object = db.session.scalars(sa.select(object_type)).first()
        attr_name = [i.name for i in inspect(object_type).columns if not i.name.endswith('_id')]
        attr_name += [i.key for i in inspect(object_type).relationships]
        simple_names = [i.name for i in inspect(object_type).columns]
        # test search by all column_index in object
        for column in any_object.Meta.column_index:
            if column in simple_names:
                search_index_data = auth_client.get(url_for('admin.object_type_index_data', _external=False, object_type=object_type.__name__,
                                                        **{"search": str(getattr(any_object, column)), "limit": 10, "offset": 0}))
                assert search_index_data.status_code == 200, f"Cannot get enumerated object index data with search by simple attr {column}"
                if getattr(any_object, column) is not None and not isinstance(getattr(any_object, column), bool):
                    assert int(search_index_data.get_json()["total"]) >= 1, f"search by all column when use field `{column}`for object {object_type.__name__} id {any_object.id} return an {search_index_data.get_json()["total"]} unexpected objects in total"
                assert len(search_index_data.get_json()["rows"]) <= 10, f"search by all column for object {any_object.id} return an {len(search_index_data.get_json()["rows"])}, when expected <= 10"
                search_column_only = auth_client.get(url_for('admin.object_type_index_data', _external=False, object_type=object_type.__name__,
                                                        **{"limit": 10, "offset": 0, "filter": json.dumps({column: getattr(any_object, column)})}))
                assert search_column_only.status_code == 200, f"Cannot get enumerated object index data with search by simple attr column {column}"
                if getattr(any_object, column) is not None and not isinstance(getattr(any_object, column), bool):
                    assert int(search_column_only.get_json()["total"]) >= 1 and getattr(any_object, column) is not None, f"search by one column for object {any_object.id} return an {search_column_only.get_json()["total"]} unexpected results"
                assert len(search_column_only.get_json()["rows"]) <= 10, f"Search by one column for object {any_object.id} return an {len(search_column_only.get_json()["rows"])}, but expected <= 10"
            # relationships - maybe later...

def test_create_new_object_type(auth_client: FlaskClient):
    for object_type in get_enumerated_objects():
        # test open page
        open_request = auth_client.get(url_for('admin.object_type_new', object_type=object_type.__name__, _external=False))
        assert open_request.status_code == 200, f'Cannot open page to add new object type for {object_type}: status_code is {open_request.status_code}'
        # wrong create request
        wrong_create_request = auth_client.post(url_for('admin.object_type_new', _external=False, object_type=object_type.__name__), follow_redirects=True)
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
                options[rel_name] = '1'
            else:
                options[rel_name] = []
        good_create_request = auth_client.post(url_for('admin.object_type_new', _external=False, object_type=object_type.__name__), follow_redirects=True,
                                          data=options)
        assert good_create_request.status_code == 200, f"Status code of good create request for object {object_type.__name__} with options {options} are not 200: {good_create_request.status_code}"
        element_tree = ... # HTML parser - ? - search 'Not a valid choice' and get field name
        assert urlparse(good_create_request.request.url).path == url_for('admin.object_type_index', _external=False, object_type=object_type.__name__), f"Redirect after create object is not to object_type_index for object {object_type.__name__}. Redirect to {urlparse(good_create_request.request.url).path}, options: {options}"
        if hasattr(object_type, 'string_slug'):
            new_objects = db.session.scalars(sa.select(object_type).where(object_type.string_slug == 'test_add_new')).all()
            assert len(new_objects) == 1, f"Length of new created object for {object_type.__name__} is {len(new_objects)}. Options: {options}"
            for option_name, option_value in options.items():
                if option_value == '1' or option_value == []:
                    continue
                assert getattr(new_objects[0], option_name) == option_value, f"Cannot create attribute {option_name} with value {option_value} on object {object_type.__name__}. Current value: {getattr(new_objects[0], option_name)}"

def test_edit_new_object_type(auth_client: FlaskClient):
    # test open page
    for object_type in get_enumerated_objects():
        obj = db.session.scalars(sa.select(object_type)).first()
        open_request = auth_client.get(url_for('admin.object_type_edit', _external=False, object_type=object_type.__name__, object_id=obj.id))
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
                options[rel_name] = '2'
            else:
                options[rel_name] = []
        # test edit our created object
        if hasattr(object_type, 'string_slug'):
            curr_obj = db.session.scalars(sa.select(object_type).where(object_type.string_slug == 'test_add_new')).first()
            assert curr_obj is not None, f"Cannot find object of type {object_type.__name__} with string_slug test_add_new"
            options['id'] = curr_obj.id
            edit_request = auth_client.post(url_for('admin.object_type_edit', _external=False, object_type=object_type.__name__, object_id=curr_obj.id), follow_redirects=True, data=options)
            assert edit_request.status_code == 200, f"Status code of edit enumerated object for object_type {object_type.__name__} is not 200"
            assert urlparse(edit_request.request.url).path == url_for('admin.object_type_index', _external=False, object_type=object_type.__name__), f"Redirect after edit object is not to object_type_index for object {object_type.__name__}. Redirect to {urlparse(edit_request.request.url).path}, options: {options}. Invalid-feedback: {'invalid-feedback' in edit_request.text}"
            new_curr_obj = db.session.scalars(sa.select(object_type).where(object_type.string_slug == 'test_edit_new')).first()
            assert new_curr_obj is not None, f"Cannot find current object of type {object_type.__name__} after edit request"
            for option_name, option_value in options.items():
                if option_value == '2' or option_value == []:
                    continue
                assert getattr(new_curr_obj, option_name) == option_value, f"Cannot change attribute {option_name} to {option_value} to object {object_type.__name__}"
        else:
            curr_obj = db.session.scalars(sa.select(object_type)).first()
            assert curr_obj is not None, f"Cannot find object of type {object_type.__name__} without string_slug"
            options['id'] = curr_obj.id
            edit_request = auth_client.post(url_for('admin.object_type_edit', _external=False, object_type=object_type.__name__, object_id=curr_obj.id), follow_redirects=True, data=options)
            assert edit_request.status_code == 200, f"Status code of edit enumerated object for object_type {object_type.__name__} is not 200"
            assert urlparse(edit_request.request.url).path == url_for('admin.object_type_index', _external=False, object_type=object_type.__name__), f"Redirect after edit object is not to object_type_index for object {object_type.__name__}. Redirect to {urlparse(edit_request.request.url).path}, options: {options}. Invalid-feedback: {'invalid-feedback' in edit_request.text}"
            new_curr_obj = db.session.scalars(sa.select(object_type).where(object_type.id == curr_obj.id)).first()
            assert new_curr_obj is not None, f"Cannot find current object of type {object_type.__name__} after edit request without string_slug. ID: {curr_obj.id}"
            for option_name, option_value in options.items():
                if option_value == '2' or option_value == []:
                    continue
                assert getattr(new_curr_obj, option_name) == option_value, f"Cannot change attribute {option_name} to {option_value} to object {object_type.__name__}"

def test_delete_object_type(auth_client: FlaskClient):
    for object_type in get_enumerated_objects():
        if hasattr(object_type, 'string_slug'):
            obj_id = db.session.scalars(sa.select(object_type.id).where(object_type.string_slug == 'test_edit_new')).first()
        else:
            obj_id = db.session.scalars(sa.select(object_type.id)).first()
        assert obj_id is not None, f"Cannot find any object of type {object_type.__name__}"
        resp = auth_client.post(url_for('admin.object_type_delete', _external=False, object_type=object_type.__name__), follow_redirects=True, data={'id': obj_id})
        assert resp.status_code == 200, f"Cannot redirect to page after delete object {object_type.__name__} with id {obj_id}: Status code == {resp.status_code}"
        assert urlparse(resp.request.url).path == url_for('admin.object_type_index', _external=False, object_type=object_type.__name__), f"Redirect url after delete object {object_type.__name__} is not to object index: {urlparse(resp.request.url).path}"
        obj = db.session.get(object_type, obj_id)
        assert obj is None, f"Object {object_type.__name__} with ID {obj_id} was not deleted from database"


def test_status_objects_open_edit_transits(auth_client: FlaskClient):
    for object_type in get_status_objects():
        edit_transits_page = auth_client.get(url_for('admin.status_type_transits', _external=False, object_type=object_type.__name__))
        assert edit_transits_page.status_code == 200, f"Cannot open Edit transits page for status object {object_type.__name__}: status code is {edit_transits_page.status_code}"

def test_issue_template_new(auth_client: FlaskClient):
    get_req = auth_client.get(url_for('admin.issue_template_new', _external=False))
    assert get_req.status_code == 200, "Admin page - can't open Issue template new page"
    templ_data = {'title': 'Test error', 'string_slug': 'test_error', 'description': 'Test template error',
                  'issue_title': 'New error in application', 'issue_description': 'An error occured in application', 'issue_fix': 'More Money!',
                  'issue_technical': 'Need more Money!', 'issue_riscs': 'IS only', 'issue_references': 'On me', 'issue_cvss': 3.1415, 'issue_cve_id': 0}
    create_req = auth_client.post(url_for('admin.issue_template_new', _external=False), follow_redirects=True, data=templ_data)
    assert create_req.status_code == 200, f"Cannot make request to create issue template"
    new_issue_template = db.session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == 'test_error')).first()
    assert new_issue_template is not None, f"Cannot create new issue template in database"
    assert urlparse(create_req.request.url).path == url_for('admin.issue_template_show', _external=False, template_id = new_issue_template.id), f"Redirect after create issue template is not on show issue template page"
    assert len(create_req.history) == 1, "Not valid redirects count after create new issue_template"
    for keys, values in templ_data.items():
        if keys == 'issue_cve_id' and values == 0 and new_issue_template.issue_cve_id is None:
            continue
        assert getattr(new_issue_template, keys) == values, f"Cannot set attribute {keys} to {values} when create issue template"


def test_create_issue_by_template(auth_client: FlaskClient):
    templ = db.session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == 'test_error')).first()
    issue = templ.create_issue_by_template()


def test_issue_template_edit(auth_client: FlaskClient):
    template = db.session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == 'test_error')).first()
    assert template is not None, "Cannot find new issue template with string_slug 'test_error' in database"
    get_req = auth_client.get(url_for('admin.issue_template_edit', _external=False, template_id=template.id))
    assert get_req.status_code == 200, "Cannot open Issue template edit page"
    templ_data = {'title': 'Real error', 'string_slug': 'real_error', 'description': 'Real template error',
                  'issue_title': 'Real error in application', 'issue_description': 'A real error occured in application', 'issue_fix': 'More Money! Only more money!',
                  'issue_technical': 'Need more and more and more Money!', 'issue_riscs': 'Ka-Boom!', 'issue_references': "Yes, that's the way it is. I'm responsible for the bazaar", 'issue_cvss': 9.9, 'issue_cve_id': 0}
    edit_req = auth_client.post(url_for('admin.issue_template_edit', _external=False, template_id=template.id), follow_redirects=True, data=templ_data)
    assert edit_req.status_code == 200, f"Cannot edit issue template"
    assert len(edit_req.history) == 1, f"Not valid redirects count after edit issue template"
    assert urlparse(edit_req.request.url).path == url_for('admin.issue_template_show', _external=False, template_id=template.id), f"Redirect after edit issue template is not to show page"
    db.session.refresh(template)
    for key, value in templ_data.items():
        if key == 'issue_cve_id' and value == 0 and template.issue_cve_id is None:
            continue
        assert getattr(template, key) == value, f"Cannot set attribute '{key}' to '{value}' when edit issue template"


def test_issue_template_delete(auth_client: FlaskClient):
    template = db.session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == 'real_error')).first()
    assert template is not None, "Cannot find new issue template with string_slug 'real_error' in database"
    delete_template = auth_client.post(url_for('admin.issue_template_delete', _external=False, template_id=template.id), follow_redirects=True)
    assert delete_template.status_code == 200, f"Cannot delete issue template"
    assert len(delete_template.history) == 1, f"Not valid redirects count after delete issue template"
    assert urlparse(delete_template.request.url).path == url_for('admin.issue_template_index', _external=False), f"Redirect after delete template request is not to Issue template index page"
    template = db.session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == 'real_error')).first()
    assert template is None, f"Cannot delete issue template from database"


def test_task_template(auth_client: FlaskClient):
    # Index
    index = auth_client.get(url_for('admin.task_template_index', _external=False))
    assert index.status_code == 200, f"Cannot get task template index page. Status_code is {index.status_code}"
    # Create template
    new_show = auth_client.get(url_for("admin.task_template_new", _external=False))
    assert new_show.status_code == 200, f"Cannot get task template create page. Status code is {new_show.status_code}"
    new_template_data = {'title': "Test new task", "description": "Test add new task template", "string_slug": "new_task_template", "task_title": "Create new task",
                         "task_description": "Tested added new task template", "task_tracker_id": 1, "task_priority_id": 1, "task_estimation_time_cost": 3}
    new_request = auth_client.post(url_for('admin.task_template_new', _external=False), follow_redirects=True, data=new_template_data)
    assert new_request.status_code == 200, "Cannot create new task template"
    new_template = db.session.scalars(sa.select(models.ProjectTaskTemplate).where(models.ProjectTaskTemplate.string_slug == 'new_task_template')).first()
    assert new_template is not None, f"Cannot find new task in database"
    assert urlparse(new_request.request.url).path == url_for('admin.task_template_show', template_id=new_template.id, _external=False), f"Redirect after create new task template is not to template show page"
    assert len(new_request.history) == 1, f"Incorrect count of redirect history after create new task template: {len(new_request.history)}"
    for key, value in new_template_data.items():
        if key == 'task_estimation_time_cost':
            assert new_template.task_estimation_time_cost.seconds == 3 * 60 * 60
        else:
            assert getattr(new_template, key) == value
    # Create task by template
    task = new_template.create_task_by_template()
    del task
    # Edit template
    get_edit = auth_client.get(url_for("admin.task_template_edit", _external=False, template_id=new_template.id))
    assert get_edit.status_code == 200, f"Cannot open edit task template page - status code is {get_edit.status_code}"
    template_edit_data = {'title': "Real new task", "description": "Real add new task template", "string_slug": "edit_task_template", "task_title": "Really new task",
                         "task_description": "Really added new task template", "task_tracker_id": 2, "task_priority_id": 2, "task_estimation_time_cost": 4}
    edit_request = auth_client.post(url_for('admin.task_template_edit', _exernal=False, template_id=new_template.id), follow_redirects=True, data=template_edit_data)
    assert edit_request.status_code == 200, f"Edit task template status code is {edit_request.status_code}"
    assert len(edit_request.history) == 1, f"Incorrect count of redirect history after edit task template: {len(edit_request.history)}"
    assert urlparse(edit_request.request.url).path == url_for('admin.task_template_show', template_id=new_template.id, _external=False), f"Redirect after edit task template is not to template show page"
    db.session.refresh(new_template)
    for key, value in template_edit_data.items():
        if key == 'task_estimation_time_cost':
            assert new_template.task_estimation_time_cost.seconds == 4 * 60 * 60
        else:
            assert getattr(new_template, key) == value
    # Delete template
    delete_request = auth_client.post(url_for('admin.task_template_delete', template_id=new_template.id, _external=False), follow_redirects=True)
    assert delete_request.status_code == 200, f"Cannot delete task template - status code is {delete_request.status_code}"
    assert len(delete_request.history) == 1, f"Incorrect count of redirect history after edit task template: {len(delete_request.history)}"
    assert urlparse(delete_request.request.url).path == url_for('admin.task_template_index', _external=False), f"Redirect after delete task template is not to task template index"
    ct = db.session.scalars(sa.select(models.ProjectTaskTemplate).where(models.ProjectTaskTemplate.id == new_template.id)).first()
    assert ct is None, f"Project task template was not deleted from database after delete request"


def test_project_roles(auth_client: FlaskClient):
    index = auth_client.get(url_for('admin.project_role_index', _external=False))
    assert index.status_code == 200, f"Cannot open index project roles. Status code: {index.status_code}"
    role_new = auth_client.get(url_for("admin.project_role_new", _external=False))
    assert role_new.status_code == 200, f"Cannot open project role new page. Status code: {role_new.status_code}"
    role_data = {'title': 'New role', 'description': 'Created role', 'string_slug': 'new_role'}
    create_role = auth_client.post(url_for('admin.project_role_new', _external=False), follow_redirects=True, data=role_data)
    assert create_role.status_code == 200, f"Cannot create project role. Status code is {create_role.status_code}"
    assert len(create_role.history) == 1, f"Incorrect count of redirect history after create role request: {len(create_role.history)}"
    assert urlparse(create_role.request.url).path == url_for("admin.project_role_index", _external=False), f"Redirect after create role is not to project role index"
    role = db.session.scalars(sa.select(models.ProjectRole).where(models.ProjectRole.string_slug == 'new_role')).first()
    assert role is not None, f"Project role was not added to database after making create request"
    for key, value in role_data.items():
        assert getattr(role, key) == value, f"Cannot set {key} attribute to Project Role"
    edit_role_get = auth_client.get(url_for('admin.project_role_edit', role_id=role.id, _external=False))
    assert edit_role_get.status_code == 200, f"Cannot open project role edit page. Status code: {edit_role_get.status_code}"
    role_data = {'title': 'Real role', 'description': 'Edited role'}
    edit_role = auth_client.post(url_for('admin.project_role_edit', role_id=role.id, _external=False), follow_redirects=True, data=role_data)
    assert edit_role.status_code == 200, f"Cannot edit project role. Status code is {edit_role.status_code}"
    assert len(edit_role.history) == 1, f"Incorrect count of redirect history after edit role request: {len(edit_role.history)}"
    assert urlparse(edit_role.request.url).path == url_for('admin.project_role_index', _external=False), f"Redirect after edit project role is not to project role index"
    db.session.refresh(role)
    for key, value in role_data.items():
        assert getattr(role, key) == value, f"Cannot set project role attribute {key}"
    permissions_get = auth_client.get(url_for('admin.project_role_permissions', _external=False))
    assert permissions_get.status_code == 200, 'Cannot open project role permissions page'
    role_delete = auth_client.post(url_for('admin.project_role_delete', _external=False, role_id=role.id), follow_redirects=True)
    assert role_delete.status_code == 200, f"Cannot delete project role. Status code is {role_delete.status_code}"
    assert len(role_delete.history) == 1, f"Incorrect count of redirect history after delete project role request: {len(role_delete.history)}"
    assert urlparse(role_delete.request.url).path == url_for('admin.project_role_index', _external=False), f"Redirect after delete project role is not to project role index"
    r = db.session.scalars(sa.select(models.ProjectRole).where(models.ProjectRole.id == role.id)).first()
    assert r is None, f"Cannot delete project role from database after make role delete request"


def test_admin_files(auth_client: FlaskClient):
    file_index = auth_client.get(url_for('admin.admin_file_index', _external=False))
    assert file_index.status_code == 200, f"Admin page - cannot open file index page. Status code is {file_index.status_code}"
    file_index_data = auth_client.get(url_for('admin.files_index_data', limit=10, offset=0, search="", _external=False))
    assert file_index_data.status_code == 200, f"Cannot get file index list. Status code is {file_index_data.status_code}"
    random_file = db.session.scalars(sa.select(models.FileData)).first()
    assert random_file is not None, f"Cannot find any file in database"
    file_delete = auth_client.post(url_for('admin.files_delete', _external=False, file_id=random_file.id))
    assert file_delete.status_code == 200, f"Status code of file delete request is {file_delete.status_code}"
    assert file_delete.json["status"] == "success", f"Status of file delete is not success"


def test_report_template(auth_client: FlaskClient):
    template_index = auth_client.get(url_for('admin.report_template_index', _external=False))
    assert template_index.status_code == 200, f"Cannot open report template index page. Status code is {template_index.status_code}"
    template_new_get = auth_client.get(url_for('admin.report_template_new', _external=False))
    assert template_new_get.status_code == 200, f"Cannot open report template new page. Status code is {template_new_get.status_code}"


def test_project_additional_parameters(auth_client: FlaskClient):
    parameters_index = auth_client.get(url_for('admin.project_additional_parameters_index', _external=False))
    assert parameters_index.status_code == 200, f"Cannot open project additional parameters index page. Status code is {parameters_index.status_code}"
    group_id = db.session.scalars(sa.select(models.ProjectAdditionalFieldGroup)).first()
    assert group_id is not None, f"Cannot find any project additional field group id"
    group_fields = auth_client.get(url_for('admin.project_additional_parameters_index_data', _external=False, group_id=group_id.id, search=""))
    assert group_fields.status_code == 200, f"Cannot get any project additional fields group childrens. Request is {group_fields.request.url}, status code: {group_fields.status_code}"
    assert group_fields.json["total"] == db.session.scalars(sa.select(sa.func.count(models.ProjectAdditionalField.id)).where(models.ProjectAdditionalField.group_id == group_id.id)).one(), f"Incorrect total elements for project additional fields group"
    parameter_new_get = auth_client.get(url_for('admin.project_additional_parameters_new', _external=False))
    assert parameter_new_get.status_code == 200, f"Cannot open project additional parametes create page. Status code {parameter_new_get.status_code}"
    parameter_fields = {'title': "New parameter", 'string_slug': "new_parameter", "help_text": "Test created parameter", "description": "This is a new parameter", "field_type": list(models.ProjectAdditionalField.get_all_field_names().keys())[0], "group_id": 1}
    parameter_new = auth_client.post(url_for('admin.project_additional_parameters_new', _external=False), follow_redirects=True, data=parameter_fields)
    assert parameter_new.status_code == 200, f"Cannot create new project additional parameter. Status code {parameter_new.status_code}"
    assert len(parameter_new.history) == 1, f"Incorrect count of redirect history after create new project additional parameter: {len(parameter_new.history)}"
    assert urlparse(parameter_new.request.url).path == url_for("admin.project_additional_parameters_index", _external=False), f"Redirect after create new project additional parameter is not to parameters index page"
    param = db.session.scalars(sa.select(models.ProjectAdditionalField).where(models.ProjectAdditionalField.string_slug == 'new_parameter')).first()
    assert param is not None, f"Cannot find new project additional parameter"
    for key, value in parameter_fields.items():
        assert getattr(param, key) == value, f"Cannot change project additional field parameter {key}"
    edit_get = auth_client.get(url_for('admin.project_additional_parameters_edit', _external=False, parameter_id=param.id))
    assert edit_get.status_code == 200, f"Cannot open project additional parameter edit page. Status code {edit_get.status_code}"
    parameter_fields = {'title': "Edit parameter", 'string_slug': "edit_parameter", "help_text": "Test edited parameter", "description": "This is an edited parameter", "field_type": list(models.ProjectAdditionalField.get_all_field_names().keys())[1], "group_id": 2}
    edit_post = auth_client.post(url_for('admin.project_additional_parameters_edit', parameter_id=param.id, _external=False), follow_redirects=True, data=parameter_fields)
    assert edit_post.status_code == 200, f"Cannot edit project additional parameter. Status code: {edit_post.status_code}"
    assert len(edit_post.history) == 1, f"Incorrect count of redirect history after edit project additional parameter: {len(edit_post.history)}"
    assert urlparse(edit_post.request.url).path == url_for('admin.project_additional_parameters_index', _external=False), "Redirect after edit project additional parameter is not to parameters index page"
    db.session.refresh(param)
    for key, value in parameter_fields.items():
        assert getattr(param, key) == value, f"Cannot change project additional field parameter{key}"
    # Delete request
    delete_req = auth_client.post(url_for('admin.project_additional_parameter_delete', parameter_id=param.id, _external=False), follow_redirects=True)
    assert delete_req.status_code == 200, f"Cannot delete project additional parameter. Status code {delete_req.status_code}"
    assert len(delete_req.history) == 1, f"Incorrect count of redirect history after edit project additional parameter: {len(delete_req.history)}"
    assert urlparse(delete_req.request.url).path == url_for('admin.project_additional_parameters_index', _external=False), f"Redirect after delete project additional parameter is not to parameter index page"
    param_1 = db.session.scalars(sa.select(models.ProjectAdditionalField).where(models.ProjectAdditionalField.id == param.id)).first()
    assert param_1 is None, f"Cannot delete project additional parameter from database"


def test_credential_template_import(auth_client: FlaskClient):
    # Index template
    index = auth_client.get(url_for('admin.credential_template_index', _external=False))
    assert index.status_code == 200, f"Cannot open credential template index page. Status code is: {index.status_code}"
    # Create template
    new_get = auth_client.get(url_for('admin.credential_template_new', _external=False))
    assert new_get.status_code == 200, f"Cannot open credential template import new page. Status code is {new_get.status_code}"
    new_cred_template_data = {"title": "New test", 'string_slug': 'new_test', 'description': 'Hey, this is a test cred import template', 'login_column_number': 2,
                         'password_hash_column_number': 1, 'description_column_number': 3, 'password_column_number': 0, 'static_login': '123', 'static_password_hash': 'aaabbb',
                         'static_hash_type_id': 1, 'static_check_wordlist_id': 2, 'static_description': 'Import description'}
    new_post = auth_client.post(url_for('admin.credential_template_new', _external=False), follow_redirects=True, data=new_cred_template_data)
    assert new_post.status_code == 200, f"Cannot create new credential import template. Status code is {new_post.status_code}"
    assert len(new_post.history) == 1, f"Incorrect count of redirect history after create credential import template: {len(new_post.history)}"
    cred_template = db.session.scalars(sa.select(models.CredentialImportTemplate).where(models.CredentialImportTemplate.string_slug == 'new_test')).first()
    assert cred_template is not None, f"Cannot create new credential template in database"
    assert urlparse(new_post.request.url).path == url_for('admin.credential_template_show', template_id=cred_template.id, _external=False), "Redirect after create new credential import template is not to template show page"
    for key, value in new_cred_template_data.items():
        assert getattr(cred_template, key) == value, f"Cannot set attribute {key} to credential import template object"
    # Edit template
    edit_get = auth_client.get(url_for('admin.credential_template_edit', _external=False, template_id=cred_template.id))
    assert edit_get.status_code == 200, f"Cannot open credential import template edit form. Status code: {edit_get.status_code}"
    edit_data = {"title": "Edit test", 'string_slug': 'edit_test', 'description': 'Hey, this is a test cred import template edit', 'login_column_number': 1,
                 'password_hash_column_number': 2, 'description_column_number': 4, "password_column_number": 7, 'static_login': 'heyhey', 'static_password_hash': '11112222233333',
                 'static_hash_type_id': 2, 'static_check_wordlist_id': 1, 'static_description': "Some description"}
    edit_post = auth_client.post(url_for('admin.credential_template_edit', _external=False, template_id=cred_template.id), follow_redirects=True, data=edit_data)
    assert edit_post.status_code == 200, f"Cannot change credential import template. Status code: {edit_post.status_code}"
    assert len(edit_post.history) == 1, f"Incorrect count of redirect history after edit credential import template: {len(edit_post.history)}"
    assert urlparse(edit_post.request.url).path == url_for('admin.credential_template_show', _external=False, template_id=cred_template.id)
    db.session.refresh(cred_template)
    for key, value in edit_data.items():
        assert getattr(cred_template, key) == value, f"Cannot change {key} attribute of credential import template"
    # Delete template
    delete_post = auth_client.post(url_for('admin.credential_template_delete', template_id=cred_template.id, _external=False), follow_redirects=True)
    assert delete_post.status_code == 200, f"Cannot delete credential import template. Status code: {delete_post.status_code}"
    assert len(delete_post.history) == 1, f"Incorrect count of redirect history after delete credential import template: {len(delete_post.history)}"
    assert urlparse(delete_post.request.url).path == url_for('admin.credential_template_index', _external=False), f"Redirect after delete credential import template is not to credential import template index page"
    ct = db.session.scalars(sa.select(models.CredentialImportTemplate).where(models.CredentialImportTemplate.string_slug == 'edit_test')).first()
    assert ct is None, f"Cannot delete credential import template from database."


def test_password_policy(auth_client: FlaskClient):
    page = auth_client.get(url_for('admin.authentication_password_policy_settings', _external=False))
    assert page.status_code == 200, f"Cannot open authentication password policy page. Status code: {page.status_code}"
    post_data = {'password_min_length': 5, 'password_lifetime': 1234, 'password_lowercase_symbol_require': True, 'password_uppercase_symbol_require': True,
                 'password_numbers_require': True, 'password_special_symbols_require': True}
    policy_post = auth_client.post(url_for('admin.authentication_password_policy_settings', _external=False), follow_redirects=True, data=post_data)
    assert policy_post.status_code == 200, f"Cannot change password policy. Status code: {policy_post.status_code}"
    gs = db.session.scalars(sa.select(models.GlobalSettings)).first()
    for key, value in post_data.items():
        assert getattr(gs, key) == value, f"Cannot set attribute {key} to password policy in global settings"


def test_user_position_actions(auth_client: FlaskClient):
    page = auth_client.get(url_for('admin.user_positions_index', _external=False))
    assert page.status_code == 200, f"Cannot open user positions page. Status code: {page.status_code}"
    # create position
    create_get = auth_client.get(url_for('admin.user_positions_new', _external=False))
    assert create_get.status_code == 200, f"Cannot open user positions create form. Status code: {create_get.status_code}"
    post_data = {'string_slug': 'new_position', 'title': 'New position', 'is_default': True, 'is_administrator': True}
    position_post = auth_client.post(url_for('admin.user_positions_new', _external=False), follow_redirects=True, data=post_data)
    assert position_post.status_code == 200, f"Cannot create new user position. Status code: {position_post.status_code}"
    assert len(position_post.history) == 1, f"Incorrect count of redirect history after create user position: {len(position_post.history)}"
    assert urlparse(position_post.request.url).path == url_for('admin.user_positions_index', _external=False), f"Redirect after create user position is not to user positions index page"
    position = db.session.scalars(sa.select(models.UserPosition).where(models.UserPosition.string_slug == 'new_position')).first()
    assert position is not None, f"Cannot create new user position in database"
    # Edit position
    edit_get = auth_client.get(url_for('admin.user_positions_edit', _external=False, position_id=position.id))
    assert edit_get.status_code == 200, f"Cannot open user position edit form. Status code: {edit_get.status_code}"
    edit_data = {'string_slug': 'new_position', 'title': 'Edit position'}
    edit_post = auth_client.post(url_for('admin.user_positions_edit', _external=False, position_id=position.id), follow_redirects=True, data=edit_data)
    assert edit_post.status_code == 200, f"Cannot change user position. Status code: {edit_post.status_code}"
    assert len(edit_post.history) == 1, f"Incorrect count of redirect history after edit user position: {len(edit_post.history)}"
    assert urlparse(edit_post.request.url).path == url_for('admin.user_positions_index', _external=False), f"Redirect after edit user position is not to user positions index page"
    db.session.refresh(position)
    assert position is not None, f"Cannot edit user position in database"
    # Delete position
    delete_post = auth_client.post(url_for('admin.user_positions_delete', _external=False, position_id=position.id), follow_redirects=True)
    assert delete_post.status_code == 200, f"Cannot delete user position. Status code: {delete_post.status_code}"
    assert len(delete_post.history) == 1, f"Incorrect count of redirect history after delete user position: {len(delete_post.history)}"
    assert urlparse(delete_post.request.url).path == url_for('admin.user_positions_index', _external=False), f"Redirect after delete user position is not to user positions index page"
    position = db.session.scalars(sa.select(models.UserPosition).where(models.UserPosition.string_slug == 'new_position')).first()
    assert position is None, f"Cannot delete user position from database"
    # Edit permissions
    edit_permissions_get = auth_client.get(url_for('admin.user_positions_permissions', _external=False))
    assert edit_permissions_get.status_code == 200, f"Cannot open user position edit permissions form. Status code: {edit_permissions_get.status_code}"