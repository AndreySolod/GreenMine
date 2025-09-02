from pymetasploit import MsfRpcClient, MsfRpcConsole
from app.action_modules.classes import ActionModule
from app.controllers.forms import FlaskForm, TreeSelectMultipleField
import re
import wtforms
import wtforms.validators as validators
from flask_babel import lazy_gettext as _l
import app.models as models
from app import db, sanitizer
import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.orm.session import Session
from typing import Optional
import logging
from flask import current_app
logger = logging.getLogger("EthernalBlue ActionModule")


def action_run(target: models.Service, running_user_id: int, session: Session, console: Optional[MsfRpcConsole], locale: str="en") -> Optional[bool]:
    project_id = target.host.from_network.project_id
    console.write("use auxiliary/scanner/smb/smb_ms17_010")
    console.write(f"set RHOSTS {target.host.ip_address}")
    _garbage = console.read()
    console.write("run")
    module_data = console.read_all()
    issue = None
    for line in module_data.decode('utf-8', errors="ignore").strip().split("\n"):
        if "Host is likely VULNERABLE to MS17-010!" in line:
            logger.info(f"Service {target} are vulnerable to ms17-010")
            line = line.strip()
            pattern = r'\[\+\].*?- Host is likely VULNERABLE to MS17-010! - (.*)'
            host_info = re.search(pattern, line)
            if len(host_info.groups()) > 0:
                if target.host.description is None:
                    target.host.description = ''
                target.host.description += sanitizer.sanitize(f"<p>Host info (from MS17-010): {host_info.groups()[0]}</p>")
            issue = session.scalars(sa.select(models.Issue).where(sa.and_(models.Issue.project_id == project_id, models.Issue.by_template_slug == 'cve_2017_0144'))).first()
            if issue is None:
                issue_template = session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == 'cve_2017_0144')).first()
                issue_status = session.scalars(sa.select(models.IssueStatus).where(models.IssueStatus.string_slug == 'confirmed')).first()
                if issue_template and issue_status:
                    issue = issue_template.create_issue_by_template()
                    issue.project_id = project_id
                    issue.created_by_id = running_user_id
                    issue.status = issue_status
                else:
                    logger.error("Error when getting issue template or issue status")
            else:
                issue.updated_by_id = running_user_id
            if issue:
                session.add(issue)
                issue.services.add(target)
    session.commit()
    return issue is not None


def exploit(filled_form: dict, running_user_id: int, default_options: dict, locale: str, project_id: int) -> None:
    logger.info("Running module EthernalBlueCheck")
    client = MsfRpcClient(password=current_app.config['METASPLOIT_PASSWORD'], port=current_app.config['METASPLOIT_PORT'],
                          host=current_app.config['METASPLOIT_HOST'], ssl=True, verify_ssl=current_app.config["METASPLOIT_VERIFY_SSL"])
    with so.sessionmaker(db.engine, autoflush=False)() as session, client.create_console() as console:
        for target in filled_form['targets']:
            target = session.scalars(sa.select(models.Service).where(models.Service.id == int(target))).one()
            logger.info("Trying to exploit " + str(target))
            action_run(target, running_user_id, session, console, locale)
        session.commit()


class ModuleInitForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        smb_mark_nmap = db.session.scalars(sa.select(models.AccessProtocol).where(models.AccessProtocol.string_slug == 'microsoft-ds')).first()
        self.targets.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Service).join(models.Service.host)
                                                                                                    .join(models.Host.from_network)
                                                                                                    .where(sa.and_(models.Network.project_id == project_id,
                                                                                                                   models.Service.access_protocol_id == smb_mark_nmap.id)))]
    targets =TreeSelectMultipleField(_l("Services:"), coerce=int, description=_l("Choose targets to exploit"), validators=[validators.Optional()])
    submit = wtforms.SubmitField(_l('Run'))


class EthernalBlueCheck(ActionModule):
    title = _l("EthernalBlue check")
    description = _l("Check given address on MS17-010 vulnerability, and, if true, save data to database")
    admin_form = None
    run_form = ModuleInitForm
    exploit_single_target = staticmethod(action_run)
    exploit = staticmethod(exploit)
    default_options = {}