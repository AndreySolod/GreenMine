from app import sanitizer
import app.models as models
import sqlalchemy as sa
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from xml.etree.ElementTree import Element as etreeElement
from flask_babel import force_locale, lazy_gettext as _l
from app.helpers.general_helpers import validates_mac
import ipaddress
import re
import logging
logger = logging.getLogger("Nmap script processing")

class NmapScriptProcessor:
    """
    Base class for Nmap script processors.
    
    Implements a registration mechanism for subclasses via the script_id attribute.
    All subclasses are automatically added to the script_processors dictionary.
    """
    script_processors = {}
        
    def __init_subclass__(cls):
        NmapScriptProcessor.script_processors[cls.script_id] = cls
    
    @staticmethod
    def process(script_element: etreeElement, session: Session, project: models.Project, obj_with_script, current_user_id: int, locale: str='en') -> Optional[str]:
        """
        Process an Nmap script element.
        
        Looks up a registered processor by script_id and executes it.
        If a processor is found and returns non‑None, that result is returned.
        Otherwise returns an HTML representation of the raw script data.
        
        Args:
            script_element: Nmap script XML element.
            session: Database session.
            project: Project the script belongs to.
            obj_with_script: Object (Host or Service) associated with the script.
            current_user_id: Current user ID.
            locale: Language locale (default 'en').
        
        Returns:
            Optional[str]: HTML string for display or None.
        """
        script_id = script_element.get('id')
        if script_id in NmapScriptProcessor.script_processors:
            r = NmapScriptProcessor.script_processors[script_id.strip()]()(script_element, session, project, obj_with_script, current_user_id, locale)
            if r is not None:
                return r
        return f'\n<h5>Script data:</h5>\n<h6>{script_id}</h6><p>{sanitizer.escape(script_element.get('output')).replace('\n', '<br />')}</p>'


def get_issue_by_template(template_slug: str, project: models.Project, created_by_id: int, session: Session) -> Optional[models.Issue]:
    """
    Retrieve or create an issue based on a template slug.
    
    Searches for an existing issue in the session (new/dirty) or database
    that matches the given template slug and project.
    If not found, creates a new issue using the template with the same slug.
    
    Args:
        template_slug: Slug of the issue template.
        project: Project the issue belongs to.
        created_by_id: User ID who created the issue.
        session: Database session.
    
    Returns:
        Optional[models.Issue]: Existing or newly created issue, or None if the template does not exist.
    """
    for i in session.new:
        if isinstance(i, models.Issue) and i.by_template_slug == template_slug and i.project_id == project.id:
            return i
    for i in session.dirty:
        if isinstance(i, models.Issue) and i.by_template_slug == template_slug and i.project_id == project.id:
            return i
    issue = session.scalars(sa.select(models.Issue).where(sa.and_(models.Issue.project_id == project.id, models.Issue.by_template_slug == template_slug))).first()
    if issue is None:
        issue_template = session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == template_slug)).first()
        if issue_template is None:
            return None
        issue = issue_template.create_issue_by_template()
        issue.project_id = project.id
        issue.created_by_id = created_by_id
        session.add(issue)
    return issue


def get_dns_record(dnsname: str, dnstype: str, project: models.Project, session: Session) -> models.HostDnsName | None:
    if dnsname is None:
        return None
    for i in session.new:
        if isinstance(i, models.HostDnsName) and i.title == dnsname.strip() and i.to_host.from_network.project_id ==project.id and i.dns_type == dnstype:
            return i
    for i in session.dirty:
        if isinstance(i, models.HostDnsName) and i.title == dnsname.strip() and i.to_host.from_network.project_id == project.id and i.dns_type == dnstype:
            return i
    dns = session.scalars(sa.select(models.HostDnsName).join(models.HostDnsName.to_host).join(models.Host.from_network).where(sa.and_(models.Network.project_id == project.id,
                                                                                                                                    models.HostDnsName.title.ilike(dnsname),
                                                                                                                                    models.HostDnsName.dns_type.ilike(dnstype)))).first()
    return dns


class NmapScriptNbnsInterfaces(NmapScriptProcessor):
    """
    Processor for Nmap script 'nbns-interfaces'.
    
    Extracts hostname and network interface information from the script output.
    Creates host records for discovered interfaces and links them as interfaces
    of the current host.
    """
    script_id = 'nbns-interfaces'
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, obj_with_script: models.Service, current_user_id: int, locale: str='en'):
        """
        Process the nbns-interfaces script element.
        
        Parses hostname from script elements and interface IP addresses from tables.
        For each interface IP, either finds an existing host or creates a new one.
        Updates the technical field of the current host with interface list.
        
        Args:
            script_element: Nmap script XML element.
            session: Database session.
            project: Project the script belongs to.
            obj_with_script: Service object associated with the script.
            current_user_id: Current user ID.
            locale: Language locale (default 'en').
        
        Returns:
            None (implicitly returns None).
        """
        def create_host_if_not_exist(host_ip: ipaddress.IPv4Address) -> Optional[models.Host]:
            """
            Find or create a host with the given IP address within the project.
            
            Searches for an existing host in the database or session.
            If not found, attempts to locate a network that contains the IP
            and creates a new host attached to that network.
            
            Args:
                host_ip: IPv4 address of the host.
            
            Returns:
                Optional[models.Host]: Existing or newly created host, or None if no suitable network exists.
            """
            host = session.scalars(sa.select(models.Host).join(models.Host.from_network).where(sa.and_(models.Network.project_id == project.id, models.Host.ip_address == host_ip))).first()
            if host is not None:
                return host
            for host in [i for i in session.new if isinstance(i, models.Host)]:
                if host.ip_address == ip_address:
                    return host
            for i in session.dirty:
                if isinstance(i, models.Host) and i.ip_address == host_ip:
                    return i
            # check if network with this host is exist:
            for n in session.scalars(sa.select(models.Network).where(models.Network.project_id == project.id)).all():
                if host_ip in n.ip_address:
                    host = models.Host(ip_address=host_ip)
                    session.add(host)
                    host.from_network = n
                    return host
        
        for elem in script_element.findall('elem'):
            if elem.get('key') == 'hostname':
                if obj_with_script.host.title is None or obj_with_script.host.title == '':
                    obj_with_script.host.title = elem.text.strip()
        for table in script_element.iter('table'):
            if table.get('key') == 'interfaces':
                ifaces_data = []
                for iface in table.iter('elem'):
                    ip_address = ipaddress.IPv4Address(iface.text)
                    if ip_address == obj_with_script.host.ip_address:
                        continue
                    new_host = create_host_if_not_exist(ip_address)
                    if new_host is None:
                        ifaces_data.append(str(ip_address))
                    else:
                        new_host.created_by_id = current_user_id
                        obj_with_script.host.assign_interface(new_host)
                        session.add(new_host)
                if obj_with_script.host.technical is None:
                    obj_with_script.host.technical = ''
                if len(ifaces_data) > 0:
                    obj_with_script.host.technical += "<p>Interfaces:<br>" + "; ".join(ifaces_data) + "</p>"

class NmapScriptMessageSigning(NmapScriptProcessor):
    """
    Processor for Nmap script 'smb2-security-mode'.
    
    Detects SMB message signing configuration and creates/issues security findings
    when message signing is disabled or not required.
    """
    script_id = 'smb2-security-mode'
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, host: models.Host, current_user_id: int, locale: str='en') -> str | None:
        """
        Process the smb2-security-mode script element.
        
        Parses the script output to determine message signing status.
        If signing is disabled or enabled but not required, creates or links
        an issue of template 'nmap_script_smb2_security_mode' and associates it
        with the SMB service (port 445) on the host.
        
        Args:
            script_element: Nmap script XML element.
            session: Database session.
            project: Project the script belongs to.
            host: Host object associated with the script.
            current_user_id: Current user ID.
            locale: Language locale (default 'en').
        
        Returns:
            str: Empty string on success, None if an error occurs.
        """
        elem = script_element.find('table')
        if elem is None:
            # another style of filling
            elems = script_element.findall('elem')
            for e in elems:
                if e.get('key') == 'message_signing':
                    if e.text.strip() == 'disabled':
                        issue = get_issue_by_template('nmap_script_smb2_security_mode', project, current_user_id, session)
                        if issue is None:
                            return None
                        for serv in host.services:
                            if serv.port == 445:
                                issue.services.add(serv)
                                break
            return ''
        elem = elem.find('elem')
        if elem is None:
            return ''
        elem = elem.text
        message = 'Message signing enabled but not required'
        if elem.strip() == message:
            issue = get_issue_by_template('nmap_script_smb2_security_mode', project, current_user_id, session)
            if issue is None:
                return None
            for serv in host.services:
                if serv.port == 445:
                    issue.services.add(serv)
                    break
        elif elem.strip() == 'Message signing enabled and required':
            return ''
        else:
            return None
        return ''


class NmapScriptNBSTAT(NmapScriptProcessor):
    """
    Processor for Nmap script 'nbstat'.
    
    Extracts NetBIOS name and MAC address from the script output and updates
    the host record accordingly.
    """
    script_id = 'nbstat'
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, host: models.Host, current_user_id: int, locale: str='en'):
        """
        Process the nbstat script element.
        
        Parses the raw script output for NetBIOS name and MAC address.
        Updates the host's title and MAC fields if they are empty.
        
        Args:
            script_element: Nmap script XML element.
            session: Database session.
            project: Project the script belongs to.
            host: Host object associated with the script.
            current_user_id: Current user ID.
            locale: Language locale (default 'en').
        
        Returns:
            str: Empty string.
        """
        if host.title == None or host.title == '':
            out = script_element.get('output')
            m = re.search(pattern="NetBIOS name: (.*?),", string=out)
            if m:
                host.title = m.groups()[0]
        if host.mac == '' or host.mac == None:
            out = script_element.get('output')
            m = re.search(pattern="NetBIOS MAC: (.*?),", string=out)
            if m:
                curr_mac = m.groups()[0]
                try:
                    host.mac = validates_mac(curr_mac)
                except ValueError:
                    pass
        return ''


class NmapScriptCVE20093103(NmapScriptProcessor):
    """
    Processor for Nmap script 'smb-vuln-cve2009-3103'.
    
    Detects vulnerability CVE-2009-3103 (SMB buffer overflow) and creates/links
    an issue of template 'cve_2009_3103' for vulnerable hosts.
    """
    script_id = 'smb-vuln-cve2009-3103'
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, host: models.Host, current_user_id: int, locale: str='en'):
        """
        Process the smb-vuln-cve2009-3103 script element.
        
        Searches for a table with key 'CVE-2009-3103' and checks the state.
        If the state is 'VULNERABLE', retrieves or creates an issue for the CVE
        and associates it with the host's SMB service (port 445) and the host itself.
        
        Args:
            script_element: Nmap script XML element.
            session: Database session.
            project: Project the script belongs to.
            host: Host object associated with the script.
            current_user_id: Current user ID.
            locale: Language locale (default 'en').
        
        Returns:
            str: Empty string on success, None if not vulnerable or error.
        """
        tables = script_element.findall('table')
        for table in tables:
            if table.attrib['key'] == 'CVE-2009-3103':
                for elem in table:
                    if elem.attrib['key'] == 'state':
                        if elem.text.strip() == 'VULNERABLE':
                            issue = get_issue_by_template('cve_2009_3103', project, current_user_id, session)
                            if issue is None:
                                return None
                            for serv in host.services:
                                if serv.port == 445:
                                    issue.services.add(serv)
                                    break
                            issue.hosts.add(host)
                            return ''
        return None


class NmapScriptCVE20170144(NmapScriptProcessor):
    """
    Processor for Nmap script 'smb-vuln-ms17-010'.
    
    Detects vulnerability CVE-2017-0144 (EternalBlue) and creates/links
    an issue of template 'cve_2017_0144' for vulnerable hosts.
    """
    script_id = 'smb-vuln-ms17-010'
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, host: models.Host, current_user_id: int, locale: str='en'):
        """
        Process the smb-vuln-ms17-010 script element.
        
        Searches for a table with key 'CVE-2017-0143' and checks the state.
        If the state is 'VULNERABLE', retrieves or creates an issue for the CVE
        and associates it with the host's SMB service (port 445) and the host itself.
        
        Args:
            script_element: Nmap script XML element.
            session: Database session.
            project: Project the script belongs to.
            host: Host object associated with the script.
            current_user_id: Current user ID.
            locale: Language locale (default 'en').
        
        Returns:
            str: Empty string on success, None if not vulnerable or error.
        """
        tables = script_element.findall('table')
        for table in tables:
            if table.attrib['key'] == 'CVE-2017-0143':
                for elem in table:
                    if elem.attrib['key'] == 'state':
                        if elem.text.strip() == 'VULNERABLE':
                            issue = get_issue_by_template('cve_2017_0144', project, current_user_id, session)
                            if issue is None:
                                return None
                            for serv in host.services:
                                if serv.port == 445:
                                    issue.services.add(serv)
                                    break
                            issue.hosts.add(host)
                            return ''
        return None


class NmapScriptSnmpInfo(NmapScriptProcessor):
    """
    Processor for Nmap script 'snmp-info'.
    
    Extracts SNMP information from the script output and stores it in the
    service's additional_attributes dictionary under the 'snmp' key.
    """
    script_id = "snmp-info"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str='en'):
        """
        Process the snmp-info script element.
        
        Parses each 'elem' child of the script and stores its key‑value pairs
        in service.additional_attributes['snmp'].
        
        Args:
            script_element: Nmap script XML element.
            session: Database session.
            project: Project the script belongs to.
            service: Service object associated with the script.
            current_user_id: Current user ID.
            locale: Language locale (default 'en').
        
        Returns:
            str: Empty string.
        """
        if service.additional_attributes is None:
            service.additional_attributes = {"snmp": {}}
        elif "snmp" not in service.additional_attributes:
            service.additional_attributes["snmp"] = {}
        for elem in script_element.findall("elem"):
            service.additional_attributes["snmp"][elem.attrib.get("key")] = elem.text
        flag_modified(service, "additional_attributes")
        return ''


class NmapScriptSMBShares(NmapScriptProcessor):
    script_id = "smb-enum-shares"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str='en'):
        issue = get_issue_by_template('anonymous_access_to_smb_share', project, current_user_id, session)
        for table in script_element.findall("table"):
            current_share = {"name": table.get('key')}
            for elem in table.findall("elem"):
                current_share[elem.get('key')] = elem.text
            if 'READ' in current_share['Anonymous access']:
                issue.services.add(service)
                if issue.technical is None:
                    issue.technical = '<p>' + str(_l("Affected resources:")) + '</p>'
                issue.technical += f"<p>{current_share["name"]}</p>"
        return ''
    

class NmapScriptHTTPOpenProxy(NmapScriptProcessor):
    script_id = "http-open-proxy"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Host, current_user_id: int, locale: str='en'):
        issue = get_issue_by_template('http_open_proxy', project, current_user_id, session)
        if "Potentially OPEN proxy" in script_element.get("output"):
            issue.services.add(service)


class NmapScriptHttpTitle(NmapScriptProcessor):
    script_id = "http-title"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if service.additional_attributes is None:
            service.additional_attributes = {"http": {}}
        if "http" not in service.additional_attributes:
            service.additional_attributes["http"] = {}
        if "Site doesn't have a title" in script_element.get("output"):
            service.additional_attributes["http"]["title"] = ""
            return ""
        for elem in script_element.findall("elem"):
            if elem.get("key") == "title":
                try:
                    service.additional_attributes["http"]["title"] = elem.text.encode('latin-1').decode('unicode_escape').encode('latin-1').decode()
                except UnicodeDecodeError as e:
                    service.additional_attributes["http"]["title"] = elem.text
                except Exception as e:
                    logging.error(f"Unknown exception when decode http-title: {e}")
                flag_modified(service, "additional_attributes")
                return ""


class NmapSciptHTTPWebDav(NmapScriptProcessor):
    script_id = "http-webdav-scan"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if service.additional_attributes is None:
            service.additional_attributes = {"http": {}}
        if "http" not in service.additional_attributes:
            service.additional_attributes["http"] = {}
        for elem in script_element.findall("elem"):
            if elem.get("key") == "Server Type":
                service.additional_attributes["http"]["Server Type"] = elem.text
            if elem.get("key") == "Server Date":
                service.additional_attributes["http"]["Server Date"] = elem.text
            elif elem.get("key") == "WebDAV type":
                service.additional_attributes["http"]["WebDAV type"] = elem.text
        return ""


class NmapScriptHttpServerHeader(NmapScriptProcessor):
    script_id = "http-server-header"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if service.additional_attributes is None:
            service.additional_attributes = {"http": {}}
        if "http" not in service.additional_attributes:
            service.additional_attributes["http"] = {}
        service.additional_attributes["http"]["server_header"] = script_element.get("output")
        flag_modified(service, "additional_attributes")
        return ""


class NmapScriptSmbOsDiscovery(NmapScriptProcessor):
    script_id = "smb-os-discovery"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Host, current_user_id: int, locale: str="en"):
        for elem in script_element.findall("elem"):
            if elem.get('key') == 'os':
                try:
                    os, version = elem.text.split(' ', 2)
                except ValueError:
                    continue
                operation_system = session.scalars(sa.select(models.OperationSystemFamily).where(models.OperationSystemFamily.title.ilike(os))).first()
                if operation_system:
                    service.operation_system_family = operation_system
                    service.operation_system_gen = version
            elif elem.get('key') == 'server':
                text_data = elem.text
                if text_data is not None:
                    service.title = text_data.strip().replace('\\x00', '')
            elif elem.get('key') == 'fqdn':
                if elem.text is not None:
                    dns = get_dns_record(elem.text, "A", project=project, session=session)
                    if dns is None:
                        dns = models.HostDnsName(title=elem.text.strip(), dns_type='A', to_host=service)
                        session.add(dns)
            elif elem.get('key') == 'workgroup' or elem.get('key') == 'domain_dns':
                text = elem.text or ""
                domain = session.scalars(sa.select(models.Domain).where(sa.and_(models.Domain.project_id == project.id,
                                                                                models.Domain.title.ilike(text.replace("\\x00", "").upper())))).first()
                if domain and service.domain is None:
                    service.domain = domain
        return ""
    

class NmapScriptRdpNtlmInfo(NmapScriptProcessor):
    script_id = 'rdp-ntlm-info'
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        for elem in script_element.findall('elem'):
            if elem.get('key') == 'NetBIOS_Computer_Name':
                service.host.title = elem.text.strip()
            elif elem.get('key') == 'DNS_Computer_Name':
                if elem.text is not None:
                    dns = get_dns_record(elem.text, "A", project=project, session=session)
                    if dns is None:
                        dns = models.HostDnsName(title=elem.text.strip(), dns_type='A', to_host=service.host)
                        session.add(dns)
            elif elem.get('key') == 'NetBIOS_Domain_Name' or elem.get('key') == 'DNS_Domain_Name':
                text = elem.text or ""
                domain = session.scalars(sa.select(models.Domain).where(sa.and_(models.Domain.project_id == project.id,
                                                                                models.Domain.title.ilike(text.strip().replace('\\x00', '').upper())))).first()
                if domain and service.host.domain is None:
                    service.host.domain = domain
        return ""

class NmapScriptSSHhostkey(NmapScriptProcessor):
    script_id = "ssh-hostkey"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if service.additional_attributes == None:
            service.additional_attributes = {"ssh": {"hostkeys": []}}
        if 'ssh' in service.additional_attributes:
            service.additional_attributes["ssh"]["hostkeys"] = []
        else:
            service.additional_attributes["ssh"] = {"hostkeys": []}
        for table in script_element.findall("table"):
            hostkey = {}
            for elem in table:
                hostkey[elem.get('key')] = elem.text
            service.additional_attributes["ssh"]["hostkeys"].append(hostkey)
        flag_modified(service, "additional_attributes")
        return ""


class NmapScriptSMTPCommands(NmapScriptProcessor):
    script_id = "smtp-commands"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if service.additional_attributes is None:
            service.additional_attributes = {}
        if "smtp" not in service.additional_attributes:
            service.additional_attributes["smtp"] = {}
        service.additional_attributes["smtp"]["commands"] = script_element.get("output")
        flag_modified(service, "additional_attributes")
        return ""


class NmapScriptIMAPCapabilities(NmapScriptProcessor):
    script_id = "imap-capabilities"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if service.additional_attributes is None:
            service.additional_attributes = {}
        if "imap" not in service.additional_attributes:
            service.additional_attributes["imap"] = {}
        service.additional_attributes["imap"]["capabilities"] = script_element.get("output")
        flag_modified(service, "additional_attributes")
        return ""


class NmapScriptPOP3Capabilities(NmapScriptProcessor):
    script_id = "pop3-capabilities"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if service.additional_attributes is None:
            service.additional_attributes = {}
        if "pop3" not in service.additional_attributes:
            service.additional_attributes["pop3"] = {}
        service.additional_attributes["pop3"]["capabilities"] = script_element.get("output")
        flag_modified(service, "additional_attributes")
        return ""


class NmapScriptSSLCert(NmapScriptProcessor):
    script_id = "ssl-cert"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if service.additional_attributes is None:
            service.additional_attributes = {}
        if "tls" not in service.additional_attributes:
            service.additional_attributes["tls"] = {"subject": {}, "issuer": {}, "pubkey": {}, "validity": {}, "pem": None, "date": None, "alpn_protos": []}
        for table in script_element.findall("table"):
            if table.get("key") == "subject":
                for elem in table.findall("elem"):
                    match elem.get("key"):
                        case "commonName":
                            service.additional_attributes["tls"]["subject"]["commonName"] = elem.text
                        case "countryName":
                            service.additional_attributes["tls"]["subject"]["countryName"] = elem.text
                        case "localityName":
                            service.additional_attributes["tls"]["subject"]["localityName"] = elem.text
                        case "organizationName":
                            service.additional_attributes["tls"]["subject"]["organizationName"] = elem.text
                        case "organizationalUnitName":
                            service.additional_attributes["tls"]["subject"]["organizationalUnitName"] = elem.text
                        case "stateOrProvinceName":
                            service.additional_attributes["tls"]["subject"]["stateOrProvinceName"] = elem.text
                        case "emailAddress":
                            service.additional_attributes["tls"]["subject"]["emailAddress"] = elem.text
            elif table.get("key") == "issuer":
                for elem in table.findall("elem"):
                    match elem.get("key"):
                        case "commonName":
                            service.additional_attributes["tls"]["issuer"]["commonName"] = elem.text
                        case "countryName":
                            service.additional_attributes["tls"]["issuer"]["countryName"] = elem.text
                        case "localityName":
                            service.additional_attributes["tls"]["issuer"]["localityName"] = elem.text
                        case "organizationName":
                            service.additional_attributes["tls"]["issuer"]["organizationName"] = elem.text
                        case "organizationalUnitName":
                            service.additional_attributes["tls"]["issuer"]["organizationalUnitName"] = elem.text
                        case "stateOrProvinceName":
                            service.additional_attributes["tls"]["issuer"]["stateOrProvinceName"] = elem.text
                        case "emailAddress":
                            service.additional_attributes["tls"]["subject"]["emailAddress"] = elem.text
            elif table.get('key') == 'pubkey':
                for elem in table.findall("elem"):
                    match elem.get("key"):
                        case "type":
                            service.additional_attributes["tls"]["pubkey"]["type"] = elem.text
                        case "bits":
                            service.additional_attributes["tls"]["pubkey"]["bits"] = elem.text
                        case "modulus":
                            service.additional_attributes["tls"]["pubkey"]["modulus"] = elem.text
            elif table.get("key") == "validity":
                for elem in table.findall("elem"):
                    match elem.get("key"):
                        case "notBefore":
                            service.additional_attributes["tls"]["validity"]["notBefore"] = elem.text
                        case "notAfter":
                            service.additional_attributes["tls"]["validity"]["notAfter"] = elem.text
            else:
                is_san_subject = False
                dns_name = ""
                for elem in table.findall("elem"):
                    if elem.get("key") == "name" and "Subject Alternative Name" in elem.text:
                        is_san_subject = True
                    elif elem.get("key") == "value" and elem.text.strip().startswith("DNS:"):
                        dns_name = elem.text[4::].strip()
                if is_san_subject and "*" not in dns_name:
                    dns = get_dns_record(dns_name, "A", project=project, session=session)
                    if dns is None:
                        dns = models.HostDnsName(title=dns_name, dns_type='A', to_host=service)
                        session.add(dns)
        for elem in script_element.findall("elem"):
            match elem.get("key"):
                case "pem":
                    service.additional_attributes["tls"]["pem"] = elem.text
        flag_modified(service, "additional_attributes")
        return ""


class NmapScriptSSLDate(NmapScriptProcessor):
    script_id = "ssl-date"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if service.additional_attributes is None:
            service.additional_attributes = {}
        if "tls" not in service.additional_attributes:
            service.additional_attributes["tls"] = {"subject": {}, "issuer": {}, "pubkey": {}, "validity": {}, "pem": None, "date": None, "alpn_protos": []}
        service.additional_attributes["tls"]["date"] = script_element.get("output")
        flag_modified(service, "additional_attributes")
        return ""

class NmapScriptTLSALPN(NmapScriptProcessor):
    script_id = "tls-alpn"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if service.additional_attributes is None:
            service.additional_attributes = {}
        if "tls" not in service.additional_attributes:
            service.additional_attributes["tls"] = {"subject": {}, "issuer": {}, "pubkey": {}, "validity": {}, "pem": None, "date": None, "alpn_protos": []}
        if "alpn_protos" not in service.additional_attributes["tls"]:
            service.additional_attributes["tls"]["alpn_protos"] = []
        for elem in script_element.findall("elem"):
            service.additional_attributes["tls"]["alpn_protos"].append(elem.text.strip())
        flag_modified(service, "additional_attributes")
        return ""


class NmapScriptMSSQLntlmInfo(NmapScriptProcessor):
    script_id = "ms-sql-ntlm-info"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if service.additional_attributes is None:
            service.additional_attributes = {}
        if "ms-sql" not in service.additional_attributes:
            service.additional_attributes["ms-sql"] = {}
        table = script_element.findall("table")
        if len(table) == 0:
            return ""
        table = table[0]
        for elem in table.findall("elem"):
            if elem.get('key') == 'NetBIOS_Computer_Name':
                service.host.title = elem.text.strip()
            elif elem.get('key') == 'DNS_Computer_Name':
                if elem.text is not None:
                    dns = get_dns_record(elem.text, "A", project=project, session=session)
                    if dns is None:
                        dns = models.HostDnsName(title=elem.text.strip(), dns_type='A', to_host=service.host)
                        session.add(dns)
            elif elem.get('key') == 'NetBIOS_Domain_Name' or elem.get('key') == 'DNS_Domain_Name':
                text = elem.text or ""
                domain = session.scalars(sa.select(models.Domain).where(sa.and_(models.Domain.project_id == project.id,
                                                                                models.Domain.title.ilike(text.strip().replace('\\x00', '').upper())))).first()
                if domain and service.host.domain is None:
                    service.host.domain = domain
        return ""


class NmapScriptMSSQLInfo(NmapScriptProcessor):
    script_id = "ms-sql-info"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if isinstance(service, models.Host):
            return ""
        if service.additional_attributes is None:
            service.additional_attributes = {}
        if "ms-sql" not in service.additional_attributes:
            service.additional_attributes["ms-sql"] = {}
        if script_element.get("table") is None:
            return ""
        for table in script_element.get("table"):
            service.additional_attributes["ms-sql"][table.get("key")] = {}
            for elem in table.findall("elem"):
                if elem.key == "Instance name":
                    service.additional_attributes["ms-sql"][table.get("key")]["Instance name"] = elem.text
                elif elem.key == "TCP Port":
                    try:
                        service.additional_attributes["ms-sql"][table.get("key")]["TCP Port"] = int(elem.text)
                    except ValueError, TypeError:
                        pass
                elif elem.key == "Named pipe":
                    service.additional_attributes["ms-sql"][table.get("key")]["Named pipe"] = elem.text
                elif elem.key == "Clustered":
                    service.additional_attributes["ms-sql"][table.get("key")]["Clustered"] = elem.text == "true"
            for version_table in table.findall("table"):
                if version_table.get("key") == "Version":
                    for elem in version_table.findall("elem"):
                        if elem.get('key') == 'name':
                            service.additional_attributes["ms-sql"][table.get("key")]["Version name"] = elem.text
                        elif elem.get('key') == 'number':
                            service.additional_attributes["ms-sql"][table.get("key")]["Version number"] = elem.text
                        elif elem.get('key') == 'Product':
                            service.additional_attributes["ms-sql"][table.get("key")]["Product"] = elem.text
                        elif elem.get('key') == "Service pack level":
                            service.additional_attributes["ms-sql"][table.get("key")]["Service pack level"] = elem.text
                        elif elem.get('key') == "Post-SP patches applied":
                            service.additional_attributes["ms-sql"][table.get("key")]["Post-SP patches applied"] = elem.text == "true"
        flag_modified(service, 'additional_attributes')
        return ""


class NmapScriptFingerprintStrings(NmapScriptProcessor):
    script_id = "fingerprint-strings"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if service.description is None:
            service.description = ""
        service.description += "<h5>Fingerprint Strings</h5><p>" + script_element.get("output", "") + "</p>"
        return ""


class NmapScriptHttpNtlmInfo(NmapScriptProcessor):
    script_id = 'http-ntlm-info'
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        for elem in script_element.findall('elem'):
            if elem.get('key') == 'NetBIOS_Computer_Name':
                service.host.title = elem.text.strip()
            elif elem.get('key') == 'DNS_Computer_Name':
                if elem.text is not None:
                    dns = get_dns_record(elem.text, "A", project=project, session=session)
                    if dns is None:
                        dns = models.HostDnsName(title=elem.text.strip(), dns_type='A', to_host=service.host)
                        session.add(dns)
            elif elem.get('key') == 'NetBIOS_Domain_Name' or elem.get('key') == 'DNS_Domain_Name':
                text = elem.text or ""
                domain = session.scalars(sa.select(models.Domain).where(sa.and_(models.Domain.project_id == project.id,
                                                                                models.Domain.title.ilike(text.strip().replace('\\x00', '').upper())))).first()
                if domain and service.host.domain is None:
                    service.host.domain = domain
        return ""