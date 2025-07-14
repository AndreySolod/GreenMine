import pytest
from app import create_app, db
from app.cli import register as register_cli
import app.models as models
from config import TestConfig
from flask_migrate import init, upgrade
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


@pytest.fixture(scope="module")
def app_parameters() -> Generator[Tuple[FlaskClient, int]]:
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
    admin_id = db.session.scalars(sa.select(models.User).where(models.User.login == 'admin')).one().id
    response_with_cookie = client.post(url_for('users.user_login', _external=False), data={'login': 'admin', 'password': 'admin'})
    yield (client, admin_id)


def test_correct_user_page(app_parameters: Tuple[FlaskClient, int]):
    client, admin_id = app_parameters
    response = client.get(url_for('users.user_show', user_id=admin_id, _external=False), follow_redirects=True)
    assert urlparse(response.request.url).path == url_for('users.user_show', user_id=admin_id, _external=False)
