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


def test_cves(client: FlaskClient):
    index = client.get(url_for('cves.cve_index', _external=False))
    assert index.status_code == 200, f"Index page status code is {index.status_code}"
    # New CVE
    new_get = client.get(url_for('cves.cve_new', _external=False))
    assert new_get.status_code == 200, f"New page status code is {new_get.status_code}"
    post_data = {"year": 2025, 'identifier': "12345678", "title": "Test CVE", "description": "Test description", "cvss": 10.0,
                 "vulnerable_environment_type_id": 1, "vulnerable_environment": "Test environment", "proof_of_concept_language_id": 1, "proof_of_concept_code": "Some code", "wikipage_id": 0}
    new_post = client.post(url_for('cves.cve_new', _external=False), data=post_data, follow_redirects=True)
    assert new_post.status_code == 200, f"New cve page status code is {new_post.status_code}"
    assert len(new_post.history) == 1, f"Incorrect count of redirect history after new cve page: {len(new_post.history)}"
    new_cve = db.session.scalars(sa.select(models.CriticalVulnerability).where(models.CriticalVulnerability.identifier == "12345678")).first()
    assert new_cve is not None, f"Cannot create new cve in database"
    for key, value in post_data.items():
        if key == "wikipage_id":
            continue
        elif key == 'cvss':
            assert round(value) == round(new_cve.cvss), f"Incorrect value of {key} attribute in new cve"
        else:
            assert getattr(new_cve, key) == value, f"Incorrect value of {key} attribute in new cve"
    # Show cve
    assert urlparse(new_post.request.url).path == url_for('cves.cve_show', _external=False, cve_id=new_cve.id), f"Incorrect redirect after new cve page."
    # Edit cve
    edit_get = client.get(url_for('cves.cve_edit', cve_id=new_cve.id, _external=False))
    assert edit_get.status_code == 200, f"CVE edit page status code is {edit_get.status_code}"
    post_data = {"year": 2024, 'identifier': "87654321", "title": "Edit CVE", "description": "Edit description", "cvss": 5.0,
                 "vulnerable_environment_type_id": 1, "vulnerable_environment": "Edit environment", "proof_of_concept_language_id": 2, "proof_of_concept_code": "Edit code", "wikipage_id": 0}
    edit_post = client.post(url_for('cves.cve_edit', _external=False, cve_id=new_cve.id), data=post_data, follow_redirects=True)
    assert edit_post.status_code == 200, f"Edit cve request status code is {edit_post.status_code}"
    assert len(edit_post.history) == 1, f"Incorrect count of redirect history after edit cve page: {len(edit_post.history)}"
    assert urlparse(edit_post.request.url).path == url_for('cves.cve_show', _external=False, cve_id=new_cve.id), f"Incorrect redirect after edit cve page."
    db.session.refresh(new_cve)
    for key, value in post_data.items():
        if key == "wikipage_id":
            continue
        elif key == 'cvss':
            assert round(value) == round(new_cve.cvss), f"Incorrect value of {key} attribute in edited cve"
        else:
            assert getattr(new_cve, key) == value, f"Incorrect value of {key} attribute in edited cve"
    # Delete cve
    edit_post = client.post(url_for('cves.cve_delete', _external=False, cve_id=new_cve.id), follow_redirects=True)
    assert edit_post.status_code == 200, f"Delete cve request status code is {edit_post.status_code}"
    assert len(edit_post.history) == 1, f"Incorrect count of redirect history after delete cve page: {len(edit_post.history)}"
    assert urlparse(edit_post.request.url).path == url_for('cves.cve_index', _external=False), f"Incorrect redirect after delete cve page."
    dcve = db.session.scalars(sa.select(models.CriticalVulnerability).where(models.CriticalVulnerability.id == new_cve.id)).first()
    assert dcve is None, f"Cannot delete cve from database"
