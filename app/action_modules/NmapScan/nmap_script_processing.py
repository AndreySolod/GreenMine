from app import sanitizer
import app.models as models
import sqlalchemy as sa
from typing import Optional
from sqlalchemy.orm import Session
from xml.etree.ElementTree import Element as etreeElement
from flask_babel import force_locale, lazy_gettext as _l
from app.helpers.general_helpers import validates_mac
import ipaddress
import re

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


def get_dns_record(dnsname: str, project: models.Project, session: Session) -> models.HostDnsName | None:
    for i in session.new:
        if isinstance(i, models.HostDnsName) and i.title == dnsname.strip() and i.project_id ==project.id:
            return i
    for i in session.dirty:
        if isinstance(i, models.HostDnsName) and i.title == dnsname.strip() and i.project_id == project.id:
            return i
    dns = session.scalars(sa.select(models.HostDnsName).join(models.HostDnsName.to_host).join(models.Host.from_network).where(sa.and_(models.Network.project_id == project.id,
                                                                                                                                      models.HostDnsName.title.ilike(dnsname)))).first()
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
        elif "http" not in service.additional_attributes:
            service["additional_attributes"]["http"] = {}
        for elem in script_element.findall("elem"):
            if elem.get("key") == "title":
                try:
                    service.additional_attributes["http"]["title"] = elem.text.encode('latin-1').decode('cp1251')
                except Exception as e:
                    service.additional_attributes["http"]["title"] = elem.text
                return ""


class NmapScriptHttpServerHeader(NmapScriptProcessor):
    script_id = "http-server-header"
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, service: models.Service, current_user_id: int, locale: str="en"):
        if service.additional_attributes is None:
            service.additional_attributes = {"http": {}}
        elif "http" not in service.additional_attributes:
            service["additional_attributes"]["http"] = {}
        service.additional_attributes["http"]["server_header"] = script_element.get("output")


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
                service.title = elem.text.strip().replace('\\x00', '')
            elif elem.get('key') == 'fqdn':
                dns = get_dns_record(elem.text, project=project, session=session)
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
                dns = get_dns_record(elem.text, project=project, session=session)
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
