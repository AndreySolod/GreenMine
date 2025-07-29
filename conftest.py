import pytest
from app import create_app
from app.cli import register as register_cli
from flask.testing import FlaskClient
import shutil
from flask import url_for
from flask_migrate import upgrade
from config import TestConfig
import tempfile
import os
import click
from typing import Generator


@pytest.fixture(scope="module")
def auth_client() -> Generator[FlaskClient]:
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
    yield client
    os.remove(tmpfile)