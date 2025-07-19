import pytest
from app import create_app, db
from app.cli import register as register_cli
import app.models as models
from flask.testing import FlaskClient
import sqlalchemy as sa
import os
from config import TestConfig
import shutil
from flask import url_for
from flask_migrate import upgrade
import tempfile
import click
from urllib.parse import urlparse


@pytest.fixture(scope="module")
def client() -> FlaskClient:
    if not os.path.exists(TestConfig.SQLALCHEMY_DATABASE_URI.split(":///", 2)[1].split("?", 2)[0]):
        another_app = create_app(TestConfig)
        with another_app.app_context():
            register_cli(another_app)
            another_app.testing = True
            upgrade()
            with click.Context(another_app.cli.commands['greenmine'].commands['update-database-value']):
                another_app.cli.commands['greenmine'].commands['update-database-value'].callback()
    tmpfile = tempfile.mktemp()
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
    return client

def test_wiki_pages(client: FlaskClient):
    index = client.get(url_for('wiki_pages.pagedirectory_index', _external=False))
    assert index.status_code == 200, f"Cannot open Wiki page index page. Status code is {index.status_code}"
    # Create wiki directory
    new_page_get = client.get(url_for('wiki_pages.pagedirectory_new', _external=False))
    assert new_page_get.status_code == 200, f"Cannot open Wiki pages directory new page. Status code is {new_page_get.status_code}"
    page_data = {"title": "New test page", 'description': 'Page for test', 'parent_directory_id': 0}
    new_pagedirectory_post = client.post(url_for('wiki_pages.pagedirectory_new', _external=False), follow_redirects=True, data=page_data)
    assert new_pagedirectory_post.status_code == 200, f"Cannot create new wiki page directory. Status code is {new_pagedirectory_post.status_code}"
    assert len(new_pagedirectory_post.history) == 1, f"Incorrect count of redirect history after create wiki page directory: {len(new_pagedirectory_post.history)}"
    assert urlparse(new_pagedirectory_post.request.url).path == url_for('wiki_pages.pagedirectory_index', _external=False), f"Incorrect redirect after create new wiki directory page."
    page_directory = db.session.scalars(sa.select(models.WikiDirectory).where(models.WikiDirectory.title == "New test page")).first()
    assert page_directory is not None, f"Cannot create new page directory in database"
    assert "New test page" in new_pagedirectory_post.text, f"New page directory is not on the index page"
    # Create wiki directory via ajax request
    ajax_page_data = {"title": "Another pagedirectory", "description": "Some data", 'parent_dir_id': page_directory.id}
    ajax_new_dir = client.post(url_for('wiki_pages.pagedirectory_ajax_new', _external=False), data=ajax_page_data)
    assert ajax_new_dir.status_code == 200, f"Cannot create new wiki directory via ajax request. Status code: {ajax_new_dir.status_code}. Page_data: {ajax_page_data}, Request: {ajax_new_dir.request.url}"
    assert ajax_new_dir.json["status"] == 'success', f"Unsuccessful create new wiki directory via ajax request"
    assert 'id' in ajax_new_dir.json, f"New directory id not in response after ajax directory create"
    nd = db.session.get(models.WikiDirectory, ajax_new_dir.json["id"])
    assert nd is not None, f"Cannot create new wiki directory via ajax request in database"
    assert getattr(nd, 'title') == ajax_page_data['title'], f"Cannot set a title attribute to wiki directory via ajax request"
    assert getattr(nd, 'description') == ajax_page_data['description'], f"Cannot set a description attribute to wiki directory via ajax request"
    
    index = client.get(url_for('wiki_pages.pagedirectory_index', _external=False))
    assert index.status_code == 200, f"Cannot show wiki directory index page after create wiki directory via ajax. Status code is {index.status_code}"
    # Edit wiki directory
    new_dir_data = {'title': 'Changed title', 'description': "Changed description"}
    edit_post = client.post(url_for('wiki_pages.pagedirectory_edit', _external=False, wikidirectory_id=nd.id), data=new_dir_data)
    assert edit_post.status_code == 200, f"Cannot edit wiki directory. Status code {edit_post.status_code}"
    assert edit_post.json["status"] == 'success', f"Status of change wiki directory is not success"
    db.session.refresh(nd)
    for key, value in new_dir_data.items():
        assert getattr(nd, key) == value, f"Cannot set attribute {key} to wiki directory after edit request"
    # Delete wiki directory
    delete_post = client.post(url_for('wiki_pages.pagedirectory_delete', wikidirectory_id=nd.id, _external=False))
    assert delete_post.status_code == 200, f"Cannot delete wiki directory. Status code is {delete_post.status_code}"
    assert delete_post.json['status'] == 'success', f"Unsuccessfull delete wiki directory after post request"
    updated_nd = db.session.get(models.WikiDirectory, nd.id)
    assert updated_nd == None, f"Cannot delete wiki directory from database"
    # Create wiki page
    