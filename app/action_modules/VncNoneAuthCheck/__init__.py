from pymetasploit import MsfRpcClient, MsfRpcConsole
from app.action_modules.classes import ActionModule
import sqlalchemy as sa
from sqlalchemy.orm.session import Session
import sqlalchemy.orm as so
from app import db
from app.controllers.forms import FlaskForm, TreeSelectMultipleField
import wtforms
import wtforms.validators as validators
import app.models as models
from typing import Dict
import re
import logging
logger = logging.getLogger("VncNoneAuthCheck")
from flask import current_app
from flask_babel import lazy_gettext as _l


def action_run(target: models.Service, console: MsfRpcConsole, running_user_id: int, session: Session) -> bool:
    project_id = target.host.from_network.project_id
    console.write("set RHOSTS {}".format(str(target.host.ip_address)))
    console.write("set RPORT {}".format(str(target.port)))
    _garbage = console.read()
    console.write("run")
    vnc_data = console.read_all()
    # OUTPUT:
    # [*] 10.68.20.10:5900      - 10.68.20.10:5900 - VNC server protocol version: 3.3
    # [*] 10.68.20.10:5900      - 10.68.20.10:5900 - VNC server security types supported: None
    # [+] 10.68.20.10:5900      - 10.68.20.10:5900 - VNC server security types includes None, free access!
    # [*] 10.68.20.10:5900      - Scanned 1 of 1 hosts (100% complete)
    # [*] Auxiliary module execution completed
    vnc_version = None
    security_types_supported = None
    support_none_auth = False
    for line in vnc_data.decode("utf8").strip().split("\n"):
        line = line.strip()
        vnc_version_pattern = r"\[\*\].*? - VNC server protocol version: (.*?)"
        version_prop = re.match(vnc_version_pattern, line)
        if version_prop:
            vnc_version = version_prop.group(1)
            continue
        server_security_types_supported_patttern = r"\[\*\].* - VNC server security types supported: (.*)"
        security_types_prop = re.match(server_security_types_supported_patttern, line)
        if security_types_prop:
            security_types_supported = security_types_prop.group(1)
            continue
        support_none_auth_pattern = r"\[\+\].* - VNC server security types includes None, free access!"
        none_auth_props = re.match(support_none_auth_pattern, line)
        if none_auth_props:
            support_none_auth = True
            continue
    if target.additional_attributes is None:
        target.additional_attributes = {}
    if vnc_version or security_types_supported:
        target.additional_attributes["vnc_version"] = vnc_version
        target.additional_attributes["vnc_security_types_supported"] = security_types_supported
    if support_none_auth:
        issue = session.scalars(sa.select(models.Issue).where(sa.and_(models.Issue.project_id == project_id, models.Issue.by_template_slug == "vnc_none_auth"))).first()
        if not issue:
            issue_template = session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == "vnc_none_auth")).first()
            issue_status = session.scalars(sa.select(models.IssueStatus).where(models.IssueStatus.string_slug == 'confirmed')).first()
            if issue_template and issue_status:
                issue = issue_template.create_issue_by_template()
                issue.project_id = project_id
                issue.created_by_id = running_user_id
                issue.status = issue_status
                issue.services.add(target)
                session.add(issue)
        else:
            issue.updated_by_id = running_user_id
            issue.services.add(target)
    return support_none_auth


def exploit(filled_form: dict, running_user_id: int, default_options: dict, locale: str, project_id: int) -> None:
    logger.info("Running module VNC None Auth Check")
    client = MsfRpcClient(password=current_app.config['METASPLOIT_PASSWORD'], port=current_app.config['METASPLOIT_PORT'],
                          host=current_app.config['METASPLOIT_HOST'], ssl=True, verify_ssl=current_app.config["METASPLOIT_VERIFY_SSL"])
    with so.sessionmaker(db.engine, autoflush=False)() as session, client.create_console() as console:
        console.write('use auxiliary/scanner/vnc/vnc_none_auth')
        for target in filled_form['targets']:
            target = session.scalars(sa.select(models.Service).where(models.Service.id == int(target))).one()
            logger.info("Trying to exploit " + str(target))
            action_run(target, console, running_user_id, session)
        session.commit()

class ModuleInitForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        vnc_mark_nmap = db.session.scalars(sa.select(models.AccessProtocol).where(models.AccessProtocol.string_slug == 'vnc')).first()
        self.targets.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Service).join(models.Service.host)
                                                                                                    .join(models.Host.from_network)
                                                                                                    .where(sa.and_(models.Network.project_id == project_id,
                                                                                                                   models.Service.access_protocol_id == vnc_mark_nmap.id)))]
    targets =TreeSelectMultipleField(_l("Services:"), coerce=int, description=_l("Choose targets to exploit"), validators=[validators.Optional()])
    submit = wtforms.SubmitField(_l("Run"))


class VNCNoneAuthCheck(ActionModule):
    title = _l("VNC None Authentication check")
    description = _l("VNC checks for None Authentication for the specified addresses.")
    admin_form = None
    run_form = ModuleInitForm
    exploit_single_target = staticmethod(action_run)
    exploit = staticmethod(exploit)
    default_options = {}

