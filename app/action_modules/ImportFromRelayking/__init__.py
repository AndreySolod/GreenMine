from app import db, sanitizer
from app.controllers.forms import FlaskForm
from app.action_modules.classes import ActionModule
import app.models as models
import sqlalchemy as sa
import sqlalchemy.orm as so
import ipaddress
import json
from typing import Optional
import wtforms
import wtforms.validators as validators
import flask_wtf.file as wtfile
from flask_babel import lazy_gettext as _l
import logging
logger = logging.getLogger("Import from RelayKing")


def action_run(relayking_file_data: str, project_id: int, current_user_id: int, session: so.Session, locale: str='en'):
    project = session.get(models.Project, project_id)
    if project is None:
        return None
    try:
        relayking_data = json.loads(relayking_file_data)
    except json.JSONDecodeError as e:
        logging.error(f"Error when decode relayking file data: {e}")
        return None
    # Для начала - сопоставления имени хоста и ip-адреса с занесением в базу данных.
    template_webclient = session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == "webclient")).first()
    if template_webclient is not None:
        issue_webclient = session.scalars(sa.select(models.Issue).where(sa.and_(models.Issue.by_template_slug == template_webclient.string_slug,
                                                                                models.Issue.project_id == project_id))).first()
    template_reflection = session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == "ntlm_reflection")).first()
    if template_reflection is not None:
        issue_reflection = session.scalars(sa.select(models.Issue).where(sa.and_(models.Issue.by_template_slug == template_reflection.string_slug,
                                                                                    models.Issue.project_id == project_id))).first()
    for rp in relayking_data['relay_paths']:
        host = session.scalars(sa.select(models.Host).join(models.Host.from_network).where(sa.and_(models.Host.ip_address == rp['source_ip'].split(',')[0],
                                                                    models.Network.project_id == project_id))).first()
        if host is None:
            logger.info(f"Host {rp['source_ip']} is not exist, skipping")
            continue
        if host.title in [None, ""]:
            host.title = rp["source_host"].split(".")[0]
        if rp["source_host"] not in list(map(lambda x: x.title, host.dnsnames)):
            dns = models.HostDnsName(title = rp["source_host"], dns_type="A", to_host=host)
            session.add(dns)
        if rp["description"].startswith("WebClient service enabled on"):
            if template_webclient is not None and issue_webclient is None:
                issue_webclient = template_webclient.create_issue_by_template()
                issue_webclient.project_id = project_id
                issue_webclient.created_by_id = current_user_id
                session.add(issue_webclient)
            elif template_webclient is not None and issue_webclient is not None:
                issue_webclient.hosts.add(host)
                issue_webclient.updated_by_id = current_user_id

        if rp["description"].startswith("CVE-2025-33073"):
            template_reflection = session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == "ntlm_reflection")).first()
            if template_reflection is not None and issue_reflection is None:
                issue_reflection = template_reflection.create_issue_by_template()
                issue_reflection.project_id = project_id
                issue_reflection.created_by_id = current_user_id
                session.add(issue_reflection)
                issue_reflection.hosts.add(host)
            elif template_reflection is not None and issue_reflection is not None:
                issue_reflection.hosts.add(host)
                issue_reflection.updated_by_id = current_user_id
    session.commit()


def exploit(filled_form: dict, running_user: int, default_options: dict, locale: str, project_id: int) -> None:
    with so.sessionmaker(db.engine, autoflush=False)() as session:
        action_run(filled_form['relayking_file_data'], int(filled_form['project_id']),
                                                 running_user, session, locale)


class AdminOptionsForm(FlaskForm):
    pass


class ModuleInitForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_id.data = project_id
    relayking_file_data = wtforms.FileField(_l("RelayKing scan result file:"), validators=[wtfile.FileAllowed(['json'], _l("Only an json file!")), wtfile.FileRequired(_l("This field is mandatory!"))])
    project_id = wtforms.HiddenField(_l("Project ID:"), validators=[validators.InputRequired(_l("This field is mandatory!"))])
    submit = wtforms.SubmitField(_l("Import"))


class ImportFromRelayKing(ActionModule):
    title = _l("Import from RelayKing")
    description = _l("Imports the data of the scan results with RelayKing-Depth scanner")
    admin_form = AdminOptionsForm
    run_form = ModuleInitForm
    exploit_single_target = staticmethod(action_run)
    exploit = staticmethod(exploit)
    default_options = {}
