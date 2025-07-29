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


def test_cves(auth_client: FlaskClient):
    index = auth_client.get(url_for('cves.cve_index', _external=False))
    assert index.status_code == 200, f"Index page status code is {index.status_code}"
    # New CVE
    new_get = auth_client.get(url_for('cves.cve_new', _external=False))
    assert new_get.status_code == 200, f"New page status code is {new_get.status_code}"
    post_data = {"year": 2025, 'identifier': "12345678", "title": "Test CVE", "description": "Test description", "cvss": 10.0,
                 "vulnerable_environment_type_id": 1, "vulnerable_environment": "Test environment", "proof_of_concept_language_id": 1, "proof_of_concept_code": "Some code", "wikipage_id": 0}
    new_post = auth_client.post(url_for('cves.cve_new', _external=False), data=post_data, follow_redirects=True)
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
    edit_get = auth_client.get(url_for('cves.cve_edit', cve_id=new_cve.id, _external=False))
    assert edit_get.status_code == 200, f"CVE edit page status code is {edit_get.status_code}"
    post_data = {"year": 2024, 'identifier': "87654321", "title": "Edit CVE", "description": "Edit description", "cvss": 5.0,
                 "vulnerable_environment_type_id": 1, "vulnerable_environment": "Edit environment", "proof_of_concept_language_id": 2, "proof_of_concept_code": "Edit code", "wikipage_id": 0}
    edit_post = auth_client.post(url_for('cves.cve_edit', _external=False, cve_id=new_cve.id), data=post_data, follow_redirects=True)
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
    edit_post = auth_client.post(url_for('cves.cve_delete', _external=False, cve_id=new_cve.id), follow_redirects=True)
    assert edit_post.status_code == 200, f"Delete cve request status code is {edit_post.status_code}"
    assert len(edit_post.history) == 1, f"Incorrect count of redirect history after delete cve page: {len(edit_post.history)}"
    assert urlparse(edit_post.request.url).path == url_for('cves.cve_index', _external=False), f"Incorrect redirect after delete cve page."
    dcve = db.session.scalars(sa.select(models.CriticalVulnerability).where(models.CriticalVulnerability.id == new_cve.id)).first()
    assert dcve is None, f"Cannot delete cve from database"
