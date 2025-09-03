from sqlalchemy.orm.session import Session
from app import sanitizer
from xml.etree import ElementTree
from .nmap_script_processing import NmapScriptProcessor
import ipaddress
import shlex
import subprocess
import sys
import re
import os
from typing import List, Optional
import sqlalchemy as sa
import app.models as models
import logging
logger = logging.getLogger("Nmap wrapper")


class PortScannerError(Exception):
    pass

class PortScannerTimeout(PortScannerError):
    pass


class NmapScanner:
    def __init__(self, init_scanner: bool=True):
        self._nmap_path = ""
        self._nmap_last_output = ""
        self._nmap_last_error = ""
        if init_scanner:
            self.init_scanner()
    
    def init_scanner(self, nmap_search_path=("nmap", "/usr/bin/nmap", "/usr/local/bin/nmap", "/sw/bin/nmap", "/opt/local/bin/nmap")):
        for nmap_path in nmap_search_path:
            try:
                if (
                    sys.platform.startswith("freebsd")
                    or sys.platform.startswith("linux")
                    or sys.platform.startswith("darwin")
                ):
                    p = subprocess.Popen(
                        [nmap_path, "-V"],
                        bufsize=10000,
                        stdout=subprocess.PIPE,
                        close_fds=True,
                    )
                else:
                    p = subprocess.Popen(
                        [nmap_path, "-V"], bufsize=10000, stdout=subprocess.PIPE
                    )

            except OSError:
                pass
            else:
                self._nmap_path = nmap_path  # save path
                break
        if self._nmap_path == "":
            logger.error("Nmap scanner not found")
            raise PortScannerError("Nmap scanner not found")
        # regex used to detect nmap (http or https)
        regex = re.compile(r"Nmap version [0-9]*\.[0-9]*[^ ]* \( http(|s)://.* \)")
        self._nmap_last_output = bytes.decode(p.communicate()[0])  # sav stdout
        for line in self._nmap_last_output.split(os.linesep):
            if regex.match(line) is not None:
                is_nmap_found = True
                # Search for version number
                regex_version = re.compile("[0-9]+")
                regex_subversion = re.compile(r"\.[0-9]+")

                rv = regex_version.search(line)
                rsv = regex_subversion.search(line)

                if rv is not None and rsv is not None:
                    # extract version/subversion
                    self._nmap_version_number = int(line[rv.start() : rv.end()])
                    self._nmap_subversion_number = int(
                        line[rsv.start() + 1 : rsv.end()]
                    )
                break

        if not is_nmap_found:
            raise PortScannerError("nmap program was not found in path")

    def scan(self, hosts: List[ipaddress.IPv4Address | ipaddress.IPv4Network], ports: str | None,
             arguments: str | List[str]="-sV -sT -sU -O", sudo: bool=False, timeout: int=0):
        h_args = list(map(str, hosts))
        if isinstance(arguments, str):
            f_args = shlex.split(arguments)
        else:
            f_args = arguments

        # Launch scan
        args = (
            [self._nmap_path, "-oX", "-"]
            + h_args
            + ["-p", ports] * (ports is not None)
            + f_args
        )
        if sudo:
            args = ["sudo"] + args

        p = subprocess.Popen(
            args,
            bufsize=100000,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # wait until finished
        # get output
        # Terminate after user timeout
        self._nmap_last_output, self._nmap_last_err = p.communicate()

        nmap_err = bytes.decode(self._nmap_last_err)

        # If there was something on stderr, there was a problem so abort...  in
        # fact not always. As stated by AlenLPeacock :
        # This actually makes python-nmap mostly unusable on most real-life
        # networks -- a particular subnet might have dozens of scannable hosts,
        # but if a single one is unreachable or unroutable during the scan,
        # nmap.scan() returns nothing. This behavior also diverges significantly
        # from commandline nmap, which simply stderrs individual problems but
        # keeps on trucking.

        nmap_err_keep_trace = []
        nmap_warn_keep_trace = []
        if len(nmap_err) > 0:
            regex_warning = re.compile("^Warning: .*", re.IGNORECASE)
            for line in nmap_err.split(os.linesep):
                if len(line) > 0:
                    rgw = regex_warning.search(line)
                    if rgw is not None:
                        nmap_warn_keep_trace.append(line + os.linesep)
                    else:
                        nmap_err_keep_trace.append(nmap_err)

        return self._nmap_last_output, self._nmap_last_err, nmap_err_keep_trace, nmap_warn_keep_trace
    
    def parse_and_update_database(self, nmap_file_data: str, project_id: int, current_user_id: int, session: Session,
               ignore_closed_ports: bool=True, ignore_host_without_open_ports_and_arp_response: bool=True,
               add_host_with_only_arp_response: bool=True, process_operation_system: bool=True,
               scanning_host_id: Optional[int]=None, add_network_mutial_visibility: bool=True, add_host_and_service_mutual_visibility: bool=True,
               new_host_labels: Optional[List[int]]=None, exist_host_labels: Optional[List[int]]=None,
               added_comment: str="",
               locale: str='en'):
        ''' Parse nmap file and create host/service object in project.
        Paramethers:
        :param nmap_file_data: data of nmap file, representated as string;
        :param project_id: project to which create host/service object;
        :param current_user_id: user's id that running a task;
        :param ignore_closed_ports: did not append a port that have state 'closed' or 'filtered';
        :param ignore_host_without_open_ports_and_arp_response: did not add a host that haven't an open ports and arp response;
        :param add_host_with_only_arp_response: host with arp-response and with MAC-address will be added to project;
        :param process_operation_system: processing the operation system data, containing in nmap file;
        :param scanning_host_id: scanning host's id which or through which the scan was performed. Added as a mutual visibility with this service;
        :param session: sqlalchemy database session object;
        :param locale: locale of user, that running a task;
        :param add_network_mutual_visibility: mark network in which scanned host are placed and scanning network as mutual visibility;
        :param add_host_and_service_mutual_visibility: mark scanning service as accessible from scanning host;
        :param new_host_labels: a list of id of HostLabel objects that was being added to labels of created host;
        :param exist_host_labels: a list of HostLabel ids that was being added to labes of existed host;
        :param added_comment: a comment to append to description for all modified hosts;
        Features:
        - If network to which host belongs does not exist, the host is skipped;
        - If port transport level protocol (tcp, udp, sctp, etc) does not exist in database like string slug field, the port is skipped '''
        project = session.scalars(sa.select(models.Project).where(models.Project.id == project_id)).one()
        host_status_up = session.scalars(sa.select(models.HostStatus).where(models.HostStatus.string_slug == 'up')).one()
        port_state_open = session.scalars(sa.select(models.ServicePortState).where(models.ServicePortState.string_slug == 'opened')).one()
        port_state_filtered = session.scalars(sa.select(models.ServicePortState).where(models.ServicePortState.string_slug == 'filtered')).one()
        port_state_closed = session.scalars(sa.select(models.ServicePortState).where(models.ServicePortState.string_slug == 'closed')).one()
        scanning_host = session.scalars(sa.select(models.Host).where(models.Host.id == scanning_host_id)).first()
        all_device_vendors = session.scalars(sa.select(models.DeviceVendor)).all()

        def get_network_by_host(host_ip: ipaddress.IPv4Address) -> Optional[models.Network]:
            ''' returns the network that the host belongs to '''
            nonlocal project
            for network in project.networks:
                if host_ip in network.ip_address:
                    return network
            return None
        
        hosts_with_only_arp: List[models.Host] = []

        def create_host_if_not_exist(host_ip: ipaddress.IPv4Address, current_user_id: int) -> models.Host:
            ''' Trying to create host if them is not exist. Returned Host if they exist and create Host and saved it otherwise '''
            host = session.scalars(sa.select(models.Host).join(models.Host.from_network).where(sa.and_(models.Network.project_id == project_id, models.Host.ip_address == host_ip))).first()
            if host is not None:
                return host
            nonlocal hosts_with_only_arp
            for host_only_arp in hosts_with_only_arp:
                if host_only_arp.ip_address == host_ip:
                    return host
            host = models.Host(ip_address=host_ip, created_by_id=current_user_id)
            return host
        
        def create_service_if_not_exist(host: models.Host, portid: int, transport_proto: str) -> Optional[models.Service]:
            nonlocal scanning_host
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
                logger.error("Error when parsing Nmap file data")
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
                        new_host = create_host_if_not_exist(ipaddress.IPv4Address(ip_addr), current_user_id)
                        new_host.mac = mac_addr
                        new_host.state = host_status_up
                        new_host.state_reason = status_reason
                        new_host.from_network = network
                        hosts_with_only_arp.append(new_host)
                        session.add(new_host)
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
            current_host = create_host_if_not_exist(ip_addr, current_user_id)
            current_host.mac = mac_addr
            current_host.from_network = current_network
            try:
                ipidsequence = next(host.iter("ipidsequence"))
                current_host.ipidsequence_class = ipidsequence.get("class")
                current_host.ipidsequence_value = ipidsequence.get("values")
            except StopIteration:
                pass
            # add network mutual visibility
            if add_network_mutial_visibility and scanning_host is not None:
                if current_host.from_network.id != scanning_host.from_network.id:
                    scanning_host.from_network.can_see_network.add(current_host.from_network)
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
                # Host and service mutual visibility
                if add_host_and_service_mutual_visibility and scanning_host is not None:
                    scanning_host.accessible_services.add(serv)
                # processing service
                service_attr = port.find('service')
                if service_attr is not None:
                    access_protocol = session.scalars(sa.select(models.AccessProtocol).where(models.AccessProtocol.string_slug == service_attr.get('name'))).first()
                    serv.access_protocol = access_protocol
                    serv.ssl = service_attr.get("tunnel") == "ssl"
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
                    if service_attr.get('servicefp') is not None:
                        serv.nmap_fingerprint = sanitizer.escape(service_attr.get('servicefp'))
                if port.find('script') is not None:
                    for script in port.iter('script'):
                        technical = NmapScriptProcessor.process(script, session, project, serv, current_user_id, locale)
                        if serv.technical is None and technical != '':
                            serv.technical = technical
                        elif serv.technical is not None and technical not in serv.technical:
                            serv.technical += technical
                serv.technical = sanitizer.sanitize(serv.technical)
                session.add(serv)
            # Check if we need to skip added this host to database
            if len(current_host.services) != 0 or len(current_host.services) == 0 and not ignore_host_without_open_ports_and_arp_response:
                session.add(current_host)
            else:
                continue
            # processing labels for host
            if current_host in session.new:
                if new_host_labels is not None:
                    current_host.labels = set(session.scalars(sa.select(models.HostLabel).where(models.HostLabel.id.in_(map(int, new_host_labels)))).all())
            else:
                if exist_host_labels is not None:
                    current_host.labels.update(set(session.scalars(sa.select(models.HostLabel).where(models.HostLabel.id.in_(map(int, exist_host_labels)))).all()))
            if added_comment not in [None, ""]:
                if current_host.description is None:
                    current_host.description = ""
                current_host.description += sanitizer.sanitize("\n" + added_comment)
            # processing hostnames
            for hostname in host.find('hostnames'):
                try_dns = session.scalars(sa.select(models.HostDnsName).where(sa.and_(models.HostDnsName.title==hostname.get('name'), models.HostDnsName.dns_type==hostname.get('type'), models.HostDnsName.to_host_id == current_host.id))).first()
                if try_dns is not None:
                    continue
                dns = models.HostDnsName(title=sanitizer.escape(hostname.get('name'), models.HostDnsName.title.type.length), dns_type=sanitizer.escape(hostname.get('type'), models.HostDnsName.dns_type.type.length))
                dns.to_host = current_host
                session.add(dns)
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
    
    def build_scan_command(self, args: dict[str, bool | str]) -> List[str]:
        build_command = []
        if args.get("scan_tcp"):
            build_command.append("-sS")
        if args.get('traceroute'):
            build_command.append("--traceroute")
        if args.get("scan_udp"):
            build_command.append("-sU")
        if args.get("scan_sctp"):
            build_command.append("-sY")
        if args.get("process_operation_system"):
            build_command.append("-O")
        if args.get("process_service_version"):
            build_command.append("-sV")
        if args.get("min_parallelism"):
            build_command.extend(["--min-parallelism", str(args.get("min_parallelism"))])
        if args.get("min_rate"):
            build_command.extend(["--min-rate", str(args.get("min_rate"))])
        if args.get("script_timeout"):
            build_command.extend(["--script-timeout", str(args.get("script_timeout"))])
        if args.get("host_timeout"):
            build_command.extend(["--host-timeout", str(args.get("host_timeout"))])
        if args.get("timing_pattern"):
            build_command.append("-T" + str(args.get("timing_pattern")))
        if args.get("script"):
            build_command.extend(["--script", args.get("script")])
        if args.get("resolve_dns") == False:
            build_command.append("-n")
        if args.get("no_ping_host"):
            build_command.append("-Pn")
        return build_command