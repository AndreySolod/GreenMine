from app import sanitizer
import app.models as models
import sqlalchemy as sa
from typing import Optional
from sqlalchemy.orm import Session
from xml.etree.ElementTree import Element as etreeElement
from flask_babel import force_locale, lazy_gettext as _l
import ipaddress

class NmapScriptProcessor:
    script_processors = {}
        
    def __init_subclass__(cls):
        NmapScriptProcessor.script_processors[cls.script_id] = cls
    
    @staticmethod
    def process(script_element: etreeElement, session: Session, project: models.Project, obj_with_script, current_user_id: int, locale: str='en') -> Optional[str]:
        ''' Process the script with name and data. Returned True if processed and False otherwise '''
        script_id = script_element.get('id')
        if script_id in NmapScriptProcessor.script_processors:
            r = NmapScriptProcessor.script_processors[script_id.strip()]()(script_element, session, project, obj_with_script, current_user_id, locale)
            if r is not None:
                return r
        return f'\n<h5>Script data:</h5>\n<h6>{script_id}</h6><p>{sanitizer.escape(script_element.get('output')).replace('\n', '<br />')}</p>'


class NmapScriptNbnsInterfaces(NmapScriptProcessor):
    script_id = 'nbns-interfaces'
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, obj_with_script: models.Service, current_user_id: int, locale: str='en'):
        def create_host_if_not_exist(host_ip: ipaddress.IPv4Address) -> Optional[models.Host]:
            ''' Trying to create host if them is not exist. Returned Host if they exist and create Host and saved it otherwise '''
            host = session.scalars(sa.select(models.Host).join(models.Host.from_network).where(sa.and_(models.Network.project_id == project.id, models.Host.ip_address == host_ip))).first()
            if host is not None:
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
                else:
                    obj_with_script.host.technical += "<h5>hostname: " + elem.text.strip() + "</h5>"
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
                        session.commit()
                if len(ifaces_data) > 0:
                    obj_with_script.host.technical += "<p>Interfaces:<br>" + "; ".join(ifaces_data) + "</p>"

class NmapScriptMessageSigning(NmapScriptProcessor):
    script_id = 'smb2-security-mode'
    def __call__(self, script_element: etreeElement, session: Session, project: models.Project, host: models.Host, current_user_id: int, locale: str='en'):
        elem = script_element.find('table')
        if elem is None:
            return ''
        elem = elem.find('elem')
        if elem is None:
            return ''
        elem = elem.text
        message = 'Message signing enabled but not required'
        if elem.strip() == message:
            issue = session.scalars(sa.select(models.Issue).where(models.Issue.by_template_slug == 'nmap_script_smb2_security_mode')).first()
            if issue is None:
                issue_status = session.scalars(sa.select(models.IssueStatus).where(models.IssueStatus.string_slug == 'confirmed')).first()
                if issue_status is None:
                    return None
                issue_template = session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == 'nmap_script_smb2_security_mode')).first()
                if issue_template is None:
                    return None
                issue = issue_template.create_issue_by_template()
                issue.status = issue_status
                issue.project = project
                issue.created_by_id = current_user_id
                session.add(issue)
            for serv in host.services:
                if serv.port == 445:
                    issue.services.add(serv)
                    break
            try:
                session.commit()
            except:
                return None
        else:
            return None
        return ''