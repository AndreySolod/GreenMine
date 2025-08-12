from app import db, sanitizer
from app.controllers.forms import FlaskForm
from app.action_modules.classes import ActionModule
import app.models as models
import sqlalchemy as sa
import sqlalchemy.orm as so
import ipaddress
import csv
from typing import Optional
import wtforms
import wtforms.validators as validators
import flask_wtf.file as wtfile
from flask_babel import lazy_gettext as _l
import logging
logger = logging.getLogger("Import from Zmap")


def action_run(zmap_file_data: str, project_id: int, current_user_id: int, session: so.Session, locale: str='en'):
    ''' Parse zmap file and create host/service object on project.
    Parameters:
    :param zmap_file_data: data of zmap file, representated as string;
    :param project_id: project to which create host/service object;
    :param current_user_id: user's id that running a task;
    :param session: session, in which we was execute a sql command;
    :param locale: locale, in which we create a text '''
    project = session.get(models.Project, project_id)
    if project is None:
        return None
    def get_network_by_host(host_ip: ipaddress.IPv4Address) -> Optional[models.Network]:
        ''' returns the network that the host belongs to '''
        nonlocal project
        for network in project.networks:
            if host_ip in network.ip_address:
                return network
        return None
    
    def create_host_if_not_exist(host_ip: ipaddress.IPv4Address) -> models.Host:
        ''' Trying to create host if them is not exist. Returned Host if they exist and create Host and saved it otherwise '''
        nonlocal current_user_id, project_id
        host = session.scalars(sa.select(models.Host).join(models.Host.from_network).where(sa.and_(models.Network.project_id == project_id, models.Host.ip_address == host_ip))).first()
        if host is not None:
            return host
        host = models.Host(ip_address=host_ip, created_by_id=current_user_id)
        return host
    
    def create_service_if_not_exist(host: models.Host, portid: int, created_by_id: int) -> Optional[models.Service]:
        transport_proto_id = session.execute(sa.select(models.ServiceTransportLevelProtocol.id).where(models.ServiceTransportLevelProtocol.string_slug == 'tcp')).first()
        if transport_proto_id is None:
            return None
        service = session.scalars(sa.select(models.Service).where(sa.and_(models.Service.host_id == host.id, models.Service.port == portid, models.Service.transport_level_protocol_id == transport_proto_id[0]))).first()
        if service is None:
            service = models.Service(host=host, port=portid, transport_level_protocol_id=transport_proto_id[0], created_by_id=created_by_id)
        return service
    
    try:
        reader = csv.DictReader(zmap_file_data.decode('utf8').split('\n'))
    except UnicodeDecodeError as e:
        logger.error(f'Error when decoding file: not utf8 character: {e}')
        return None
    for line in reader:
        try:
            addr = ipaddress.IPv4Address(line['saddr'])
            port = int(line['sport'])
        except (ipaddress.AddressValueError, KeyError, TypeError, ValueError):
            continue
        current_network = get_network_by_host(addr)
        if current_network is None:
            continue
        current_host = create_host_if_not_exist(addr)
        current_host.from_network = current_network
        session.add(current_host)
        session.commit()
        service = create_service_if_not_exist(current_host, port, current_user_id)
        session.add(service)
        session.add(current_host)
    session.commit()


def exploit(filled_form: dict, running_user: int, default_options: dict, locale: str, project_id: int) -> None:
    with so.sessionmaker(db.engine, autoflush=False)() as session:
        action_run(filled_form['zmap_file'], int(filled_form['project_id']),
                                                 running_user, session, locale)
        


class AdminOptionsForm(FlaskForm):
    pass


class ModuleInitForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_id.data = project_id
    zmap_file = wtforms.FileField(_l("Zmap scan result file:"), validators=[wtfile.FileAllowed(['csv'], _l("Only an csv file!")), wtfile.FileRequired(_l("This field is mandatory!"))])
    project_id = wtforms.HiddenField(_l("Project ID:"), validators=[validators.InputRequired(_l("This field is mandatory!"))])
    submit = wtforms.SubmitField(_l("Import"))


class ImportFromZmap(ActionModule):
    title = _l("Import from Zmap")
    description = _l("Imports the data of the scan results with Zmap scanner (Not to be confused with nmap/zenmap)")
    admin_form = AdminOptionsForm
    run_form = ModuleInitForm
    exploit_single_target = staticmethod(action_run)
    exploit = staticmethod(exploit)
    default_options = {}