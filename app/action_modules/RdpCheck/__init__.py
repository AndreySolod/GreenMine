from pymetasploit import MsfRpcClient, MsfRpcConsole
from typing import Dict, Optional
from app.controllers.forms import FlaskForm, TreeSelectMultipleField
import wtforms
from wtforms import validators
from app.action_modules.classes import ActionModule
import app.models as models
from app import db
import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.orm.session import Session
from flask import current_app
import re
from flask_babel import lazy_gettext as _l
import logging
logger = logging.getLogger("Module RDP Check")


RDP_PROPS = None
def console_read(console_data):
    for line in console_data['data'].split('\n'):
        if "Detected RDP on" in line: #Detected RDP on 10.0.0.1:3389     (name:SOME-NAME) (domain:SOME-DOMAIN) (domain_fqdn:SOME-FQDN) (server_fqdn:SOME-FQDN) (os_version:10.0.19041) (Requires NLA: Yes)
            rdp_props = re.findall(r".*?- Detected RDP on .*?\(name:(.*?)\) \(domain:(.*?)\) \(domain_fqdn:(.*?)\) \(server_fqdn:(.*?)\) \(os_version:(.*?)\) \(Requires NLA: (.*?)\)", line)
            if len(rdp_props) == 0:
                logger.warning(f"Error when parse rdp props. String: {line}")
                continue
            RDP_PROPS = rdp_props[0]
    CONSOLE_BUSY = console_data['busy']


def action_run(target: models.Service, running_user_id: int, session: Session, console: Optional[MsfRpcConsole]=None) -> Dict[str, str]:
    console.write('set RHOSTS {}'.format(target.host.ip_address))
    console.write('set THREADS 1')
    console.write('set RPORT '+ str(target.port))
    _garbage = console.read()
    console.write("run")
    rdp_data = console.read_all()
    RDP_PROPS = None
    for line in rdp_data.decode("utf8").strip().split('\n'):
        line = line.strip()
        pattern = r".*?- Detected RDP on .*?(\(name:(.*?)\) )?(\(domain:(.*?)\) )?(\(domain_fqdn:(.*?)\) )?(\(server_fqdn:(.*?)\) )?(\(os_version:(.*?)\) )?\(Requires NLA: (.*?)\)"
        if "Detected RDP on" in line: #Detected RDP on 10.0.0.1:3389     (name:SOME-NAME) (domain:SOME-DOMAIN) (domain_fqdn:SOME-FQDN) (server_fqdn:SOME-FQDN) (os_version:10.0.19041) (Requires NLA: Yes)
            rdp_props = re.findall(pattern, line)
            if len(rdp_props) == 0:
                logger.warning(f"Error when parse rdp props. String: {line}")
                continue
            RDP_PROPS = rdp_props[0]
    if RDP_PROPS is None:
        logger.warning(f"All RDP Properties is None. Target id is: {target.id}")
        return {"Name": None, "Domain":None, "Domain FQDN":None, "Server FQDN":None, "OS Version":None, "Requires NLA": None}
    if not target.host.title:
        target.host.title = RDP_PROPS[1]
    if target.description is None:
        target.description = ""
    if target.host.description is None:
        target.host.description = ""
    target.description += f"<p>Name: {RDP_PROPS[1]};<br>Domain:{RDP_PROPS[3]};" \
        f"<br>Domain FQDN:{RDP_PROPS[5]};<br>Server FQDN:{RDP_PROPS[7]};<br>" \
            f"OS Version:{RDP_PROPS[9]};<br>Requires NLA:{RDP_PROPS[10]};</p>"
    target.host.description += f"<p>RDP Data:</p><p>Name: {RDP_PROPS[1]};<br>Domain:{RDP_PROPS[3]};<br>" \
        f"Domain FQDN:{RDP_PROPS[5]};<br>Server FQDN:{RDP_PROPS[7]};"
    target.host.operation_system_gen = RDP_PROPS[9].strip()
    if RDP_PROPS[10] == "No":
        issue = session.scalars(sa.select(models.Issue).where(sa.and_(models.Issue.project_id == target.host.from_network.project_id, models.Issue.by_template_slug == 'rdp_without_nla'))).first()
        if not issue:
            issue_template = session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == 'rdp_without_nla')).first()
            issue_status = session.scalars(sa.select(models.IssueStatus).where(models.IssueStatus.string_slug == 'confirmed')).first()
            if issue_template and issue_status:
                issue = issue_template.create_issue_by_template()
                issue.status = issue_status
                issue.created_by_id = running_user_id
                issue.project_id = target.host.from_network.project_id
                session.add(issue)
                session.commit()
        if issue:
            issue.services.add(target)
    session.add(target)
    session.commit()
    return {"Name": RDP_PROPS[1], "Domain":RDP_PROPS[3], "Domain FQDN":RDP_PROPS[5], "Server FQDN":RDP_PROPS[7], "OS Version":RDP_PROPS[9], "Requires NLA":RDP_PROPS[10] == 'Yes'}


def exploit(filled_form: dict, running_user_id: int, default_options: dict, locale: str, project_id: int) -> None:
    logger.info("Running module RDP Check")
    client = MsfRpcClient(password=current_app.config['METASPLOIT_PASSWORD'], port=current_app.config['METASPLOIT_PORT'],
                          host=current_app.config['METASPLOIT_HOST'], ssl=True, verify_ssl=current_app.config["METASPLOIT_VERIFY_SSL"])
    with so.sessionmaker(db.engine, autoflush=False)() as session, client.create_console() as console:
        console.write('use auxiliary/scanner/rdp/rdp_scanner')
        for target in filled_form['targets']:
            target = session.scalars(sa.select(models.Service).where(models.Service.id == int(target))).one()
            logger.info("Trying to exploit " + str(target))
            action_run(target, running_user_id, session, console)
        session.commit()


class ModuleInitForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        rdp_mark_nmap = db.session.scalars(sa.select(models.AccessProtocol).where(models.AccessProtocol.string_slug == 'ms-wbt-server')).first()
        self.targets.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Service).join(models.Service.host)
                                                                                                    .join(models.Host.from_network)
                                                                                                    .where(sa.and_(models.Network.project_id == project_id,
                                                                                                                   models.Service.access_protocol_id == rdp_mark_nmap.id)))]
    targets =TreeSelectMultipleField(_l("Services:"), coerce=int, description=_l("Choose targets to exploit"), validators=[validators.Optional()])
    submit = wtforms.SubmitField(_l("Run"))


class RDPcheck(ActionModule):
    title = _l("RDP check")
    description = _l("For a given address, check classic RDP misconfigures (such as RDP without NLA)")
    admin_form = None
    run_form = ModuleInitForm
    exploit_single_target = staticmethod(action_run)
    exploit = staticmethod(exploit)
    default_options = {}
