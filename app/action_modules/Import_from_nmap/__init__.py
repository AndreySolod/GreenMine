from app import db, sanitizer
from app.action_modules.classes import ActionModule
import app.models as models
import sqlalchemy as sa
import sqlalchemy.orm as so
from xml.etree import ElementTree
import ipaddress
from typing import Optional
from app.controllers.forms import FlaskForm
import wtforms
import wtforms.validators as validators
import flask_wtf.file as wtfile
from flask_babel import lazy_gettext as _l
from .nmap_script_processing import NmapScriptProcessor


def action_run(nmap_file_data: str, project_id: int, current_user_id: int,
               ignore_closed_ports: bool=True, ignore_host_without_open_ports_and_arp_response: bool=True, add_host_with_only_arp_response: bool=True, process_operation_system: bool=True,
               session=db.session, locale: str='en'):
    ''' Parse nmap file and create host/service object in project.
        Paramethers:
        :param nmap_file_data: data of nmap file, representated as string;
        :param project_id: project to which create host/service object;
        :param current_user_id: user's id that running a task;
        :param ignore_closed_ports: did not append a port that have state 'closed' or 'filtered'
        :param ignore_host_without_open_ports_and_arp_response: did not add a host that haven't an open ports and arp response
        :param add_host_with_only_arp_response: host with arp-response and with MAC-address will be added to project
        :param process_operation_system: processing the operation system data, containing in nmap file
        Features:
        - If network to which host belongs does not exist, the host is skipped;
        - If port transport level protocol (tcp, udp, sctp etc) does not exist in database like string slug field, the port is skipped '''
    project = session.scalars(sa.select(models.Project).where(models.Project.id == project_id)).one()
    host_status_up = session.scalars(sa.select(models.HostStatus).where(models.HostStatus.string_slug == 'up')).one()
    port_state_open = session.scalars(sa.select(models.ServicePortState).where(models.ServicePortState.string_slug == 'opened')).one()
    port_state_filtered = session.scalars(sa.select(models.ServicePortState).where(models.ServicePortState.string_slug == 'filtered')).one()
    port_state_closed = session.scalars(sa.select(models.ServicePortState).where(models.ServicePortState.string_slug == 'closed')).one()
    all_device_vendors = session.scalars(sa.select(models.DeviceVendor)).all()

    def get_network_by_host(host_ip: ipaddress.IPv4Address) -> Optional[models.Network]:
        ''' returns the network that the host belongs to '''
        nonlocal project
        for network in project.networks:
            if host_ip in network.ip_address:
                return network
        return None
    def create_host_if_not_exist(host_ip: ipaddress.IPv4Address) -> models.Host:
        ''' Trying to create host if them is not exist. Returned Host if they exist and create Host and saved it otherwise '''
        host = session.scalars(sa.select(models.Host).join(models.Host.from_network).where(sa.and_(models.Network.project_id == project_id, models.Host.ip_address == host_ip))).first()
        if host is not None:
            return host
        host = models.Host(ip_address=host_ip)
        return host
    
    def create_service_if_not_exist(host: models.Host, portid: int, transport_proto: str) -> Optional[models.Service]:
        transport_proto_id = session.execute(sa.select(models.ServiceTransportLevelProtocol.id).where(models.ServiceTransportLevelProtocol.string_slug == transport_proto)).first()
        if transport_proto_id is None:
            return None
        service = session.scalars(sa.select(models.Service).where(sa.and_(models.Service.host_id == host.id, models.Service.port == portid, models.Service.transport_level_protocol_id == transport_proto_id[0]))).first()
        if service is None:
            service = models.Service(host=host, port=portid, transport_level_protocol_id=transport_proto_id[0])
        return service
    
    try:
        nmap_etree = ElementTree.fromstring(nmap_file_data)
    except ElementTree.ParseError:
        try:
            #looks like this is uncomplited scan. Try to close tag nmaprun and parse again:
            nmap_file_data = nmap_file_data.decode('utf8') + "</nmaprun>"
            nmap_etree = ElementTree.fromstring(nmap_file_data)
        except ElementTree.ParseError:
            print("Error when parsing Nmap file data")
            return None
    
    if add_host_with_only_arp_response:
        for host in nmap_etree.iter('hosthint'):
            status_state = host.find("status").attrib['state']
            status_reason = host.find('status').attrib['reason']
            mac_addr = ''
            ip_addr = None
            for addr in host.findall('address'):
                if addr.attrib['addrtype'] == 'mac':
                    mac_addr = addr.attrib['addr']
                elif addr.attrib['addrtype'] == 'ipv4':
                    ip_addr = addr.attrib['addr']
            if status_state == 'up':
                network = get_network_by_host(ipaddress.IPv4Address(ip_addr))
                if network is not None and mac_addr != '':
                    new_host = create_host_if_not_exist(ipaddress.IPv4Address(ip_addr))
                    new_host.mac = mac_addr
                    new_host.state = host_status_up
                    new_host.state_reason = status_reason
                    new_host.from_network = network
                    new_host.created_by_id = current_user_id
                    session.add(new_host)
                    session.commit()
    # Processing pure hosts and ports
    for host in nmap_etree.iter('host'):
        ip_addr = None
        mac_addr = ''
        for ads in host.iter('address'):
            if ads.get('addrtype') == 'ipv4':
                ip_addr = ads.get('addr')
            elif ads.get('addrtype') == 'mac':
                mac_addr = ads.get('addr')
        current_network = get_network_by_host(ipaddress.IPv4Address(ip_addr))
        if current_network is None:
            continue
        current_host = create_host_if_not_exist(ip_addr)
        current_host.mac = mac_addr
        current_host.created_by_id = current_user_id
        current_host.from_network = current_network
        session.add(current_host)
        session.commit()
        # processing hostnames
        for hostname in host.find('hostnames'):
            try_dns = session.scalars(sa.select(models.HostDnsName).where(sa.and_(models.HostDnsName.title==hostname.get('name'), models.HostDnsName.dns_type==hostname.get('type'), models.HostDnsName.to_host_id == current_host.id))).first()
            if try_dns is not None:
                continue
            dns = models.HostDnsName(title=sanitizer.escape(hostname.get('name'), models.HostDnsName.title.type.length), dns_type=sanitizer.escape(hostname.get('type'), models.HostDnsName.dns_type.type.length))
            dns.to_host = current_host
            session.add(dns)
            session.commit()
        # processing ports
        for port in host.iter('port'):
            state = port.find('state').get('state').strip()
            if ignore_closed_ports and state != 'open':
                continue
            serv = create_service_if_not_exist(current_host, int(port.get('portid')), port.get('protocol'))
            session.add(serv)
            if serv is None:
                continue
            serv.created_by_id = current_user_id
            if state == 'open':
                serv.port_state = port_state_open
            elif 'closed' in state:
                serv.port_state = port_state_closed
            else:
                serv.port_state = port_state_filtered
            serv.port_state_reason = port.find('state').get('reason').strip()
            # processing service
            service_attr = port.find('service')
            if service_attr is not None:
                access_protocol = session.scalars(sa.select(models.AccessProtocol).where(models.AccessProtocol.string_slug == service_attr.get('name'))).first()
                serv.access_protocol = access_protocol
                serv.title = sanitizer.escape(service_attr.get('product'), models.Service.title.type.length)
                device_type = service_attr.get('devicetype')
                if device_type is not None:
                    dt = session.scalars(sa.select(models.DeviceType).where(models.DeviceType.nmap_name == device_type)).first()
                    if dt is not None:
                        current_host.device_type = dt
                    if service_attr.get('product') is not None:
                        for vendor in all_device_vendors:
                            if vendor.title in service_attr.get('product'):
                                current_host.device_vendor = vendor
                                break
                if service_attr.get('extrainfo') is not None:
                    serv.technical = f'<p>Extrainfo: {service_attr.get('extrainfo')}</p>'
            if port.find('script') is not None:
                for script in port.iter('script'):
                    technical = NmapScriptProcessor.process(script, session, project, serv, current_user_id, locale)
                    if serv.technical is not None and technical not in serv.technical:
                        serv.technical += technical
                    elif serv.technical is None:
                        serv.technical = technical
            serv.technical = sanitizer.escape(serv.technical)
            session.add(serv)
            session.commit()
        if len(current_host.services) == 0 and ignore_host_without_open_ports_and_arp_response:
            session.delete(current_host)
            session.commit()
            continue
        elif len(current_host.services) == 0 and current_host.mac == '' and not ignore_host_without_open_ports_and_arp_response:
            session.delete(current_host)
            session.commit()
        else:
            session.commit()
        # processing host scripts
        for hostscript in host.iter('hostscript'):
            for script in hostscript.iter('script'):
                technical = NmapScriptProcessor.process(script, session, project, current_host, current_user_id, locale)
                if current_host.technical is None:
                    current_host.technical = technical
                elif technical not in current_host.technical:
                    current_host.technical += technical
        # processing operation systems
        if not process_operation_system:
            continue
        for os in host.findall('os'):
            osmatch = os.find('osmatch')
            if osmatch is None:
                continue
            osclass = osmatch.find('osclass')
            if osclass is None:
                continue
            if osclass.get('type') is not None:
                device_type = session.scalars(sa.select(models.DeviceType).where(models.DeviceType.nmap_name == osclass.get("type"))).first()
                if device_type is not None:
                    current_host.device_type = device_type
            if osclass.get('vendor') is not None:
                device_vendor = session.scalars(sa.select(models.DeviceVendor).where(models.DeviceVendor.title == osclass.get('vendor'))).first()
                if device_vendor is not None:
                    current_host.device_vendor = device_vendor
            if osclass.get('osfamily') is not None:
                osfamily = session.scalars(sa.select(models.OperationSystemFamily).where(models.OperationSystemFamily.title == osclass.get('osfamily'))).first()
                if osfamily is not None:
                    current_host.operation_system_family = osfamily
            current_host.operation_system_gen = osclass.get('osgen')
            session.commit()
    return None


def exploit(filled_form: dict, running_user: int, default_options: dict, locale: str='en') -> None:
    with so.sessionmaker(bind=db.engine)() as session:
        action_run(filled_form['nmap_file'], int(filled_form["project_id"]), running_user, filled_form["ignore_closed_ports"],
                filled_form["ignore_host_without_open_ports_and_arp_response"],
                filled_form["add_host_with_only_arp_response"], filled_form["process_operation_system"], session=session, locale=locale)


class AdminOptionsForm(FlaskForm):
    pass


class ModuleInitForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_id.data = project_id
    nmap_file = wtforms.FileField(_l("Nmap scan result file:"), validators=[wtfile.FileAllowed(['xml'], _l("Only an xml file!")), wtfile.FileRequired(message=_l("This field is mandatory!"))])
    ignore_closed_ports = wtforms.BooleanField(_l("Ignore ports that do not have the status <Open>:"), default=True)
    ignore_host_without_open_ports_and_arp_response = wtforms.BooleanField(_l("Ignore hosts without open ports and ARP response:"), default=True)
    add_host_with_only_arp_response = wtforms.BooleanField(_l("Add hosts for which an ARP response has been received and there are no open ports:"), default=True)
    process_operation_system = wtforms.BooleanField(_l("Process host operating system data:"), default=True)
    project_id = wtforms.HiddenField(_l("Project ID:"), validators=[validators.InputRequired()])
    submit = wtforms.SubmitField(_l("Import"))


class ImportFromNmap(ActionModule):
    title = _l("Import from Nmap")
    description = _l("Imports the data of the scan results with the Nmap scanner")
    admin_form = AdminOptionsForm
    run_form = ModuleInitForm
    exploit_single_target = staticmethod(action_run)
    exploit = staticmethod(exploit)
    default_options = {}
