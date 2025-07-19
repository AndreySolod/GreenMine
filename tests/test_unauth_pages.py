import pytest
from app import create_app, db
from app.cli import register as register_cli
from config import TestConfig
from flask_migrate import init, migrate, upgrade
from urllib.parse import urlparse
from urllib.parse import parse_qs
from flask import url_for
import os
import click
import sqlalchemy as sa
import app.models as models
import sqlite3


@pytest.fixture(scope="module")
def app():
    app = create_app(TestConfig)
    app.config['SERVER_NAME'] = 'localhost'
    app.config['APPLICATION_ROOT'] = '/'
    app.app_context().push()
    register_cli(app)
    app.testing = True
    upgrade()
    with click.Context(app.cli.commands['greenmine'].commands['update-database-value']):
        app.cli.commands['greenmine'].commands['update-database-value'].callback()
    app.setting_custom_attributes_for_application()
    admin_id = db.session.scalars(sa.select(models.User.id).where(models.User.login == 'admin')).one()
    yield app


def test_main_page(app):
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 302
    assert response.location.startswith('/users/login')


def test_all_app_rules(app):
    client = app.test_client()
    for rule in app.url_map.iter_rules():
        if rule.websocket:
            continue
        if rule.endpoint.startswith('static'):
            continue
        if rule.endpoint == 'users.user_login':
            continue
        if 'GET' not in rule.methods:
            continue
        if rule.endpoint.startswith('api.'):
            continue
        if rule.endpoint == 'generic.get_current_user_theme_style' or rule.endpoint == 'generic.get_ckeditor_styles':
            continue
        url_string = rule.build({i: '1' for i in rule.arguments})[1]
        response = client.get(url_string, follow_redirects=True)
        assert response.status_code == 200, f"URL {url_string} in rule {rule.endpoint} have no status code 200"
        assert len(response.history) == 1, f"URL {url_string} in rule {rule.endpoint} have no redirects"
        assert urlparse(response.request.url).path == url_for('users.user_login', _external=False), f"URL {url_string} in rule {rule.endpoint} not redirect to login"
        assert 'next' in parse_qs(urlparse(response.request.url).query), f"URL {url_string} in rule {rule.endpoint} don't have next parameter"
        assert parse_qs(urlparse(response.request.url).query)['next'][0] == url_string, f"URL {url_string} in rule {rule.endpoint} not have next={url_string} parameter"
        assert response.text.find('To perform this action, you need to log in') != -1, f"URL {url_string} in rule {rule.endpoint} not show message about login"


def test_admin_login(app):
    with app.app_context():
        client = app.test_client()
        response = client.get(url_for('users.user_login', _external=False))
        assert response.status_code == 200
        # test login
        wrong_password = client.post(url_for('users.user_login', _external=False), data={'login': 'admin', 'password': 'notvalid'}, follow_redirects=True)
        assert len(wrong_password.history) == 1, f"User login with wrong password have no redirects"
        assert urlparse(wrong_password.request.url).path == url_for('users.user_login', _external=False), f"User login with wrong password does not lead to the login page"
        assert 'Invalid user login or password' in wrong_password.text, f"There is no message about an incorrect password"
        correct_password = client.post(url_for('users.user_login', _external=False), data={'login': 'admin', 'password': 'admin'}, follow_redirects=True)
        assert len(correct_password.history) == 1 or len(correct_password.history) == 2, f"User login with correct password are redirected to another page: {urlparse(correct_password.request.url).path}"
        admin_id = db.session.scalars(sa.select(models.User.id).where(models.User.login == 'admin')).first()
        assert admin_id != None, f"Cannot locate admin_id in database"
        assert urlparse(correct_password.request.url).path in [url_for('users.user_show', user_id=admin_id, _external=False), url_for('users.user_change_password_callback', user_id=admin_id, _external=False)], f"Redirect with correct password doesn't lead to user page or change_password_page"