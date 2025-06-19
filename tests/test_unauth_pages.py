import pytest
from app import create_app
from app.cli import register as register_cli
from config import TestConfig
from flask_migrate import init, upgrade
from urllib.parse import urlparse
from urllib.parse import parse_qs
import os
import click


@pytest.fixture(scope="module")
def app():
    app = create_app(TestConfig)
    app.app_context().push()
    register_cli(app)
    app.testing = True
    if not os.path.exists(TestConfig.SQLALCHEMY_DATABASE_URI.split('://', 1)[1].split('?', 1)[0]):
        init()
    upgrade()
    with click.Context(app.cli.commands['greenmine-command'].commands['update-database-value']):
        app.cli.commands['greenmine-command'].commands['update-database-value'].callback()
    app.setting_custom_attributes_for_application()
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
        url_string = rule.build({i: '1' for i in rule.arguments})[1]
        response = client.get(url_string, follow_redirects=True)
        assert response.status_code == 200, f"URL {url_string} in rule {rule.endpoint} have no status code 200"
        assert len(response.history) == 1, f"URL {url_string} in rule {rule.endpoint} have no redirects"
        assert urlparse(response.request.url).path == '/users/login', f"URL {url_string} in rule {rule.endpoint} not redirect to login"
        assert 'next' in parse_qs(urlparse(response.request.url).query), f"URL {url_string} in rule {rule.endpoint} don't have next parameter"
        assert parse_qs(urlparse(response.request.url).query)['next'][0] == url_string, f"URL {url_string} in rule {rule.endpoint} not have next={url_string} parameter"
        assert response.text.find('To perform this action, you need to log in') != -1, f"URL {url_string} in rule {rule.endpoint} not show message about login"


def test_login_page(app):
    client = app.test_client()
    response = client.get('/users/login')
    assert response.status_code == 200