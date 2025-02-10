from app import sanitizer
import app.models as models
import sqlalchemy as sa
from typing import Optional
from sqlalchemy.orm import Session
from xml.etree.ElementTree import Element as etreeElement
from flask_babel import force_locale, lazy_gettext as _l

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


#class NmapScriptNbnsInterfaces(NmapScriptProcessor):
#    script_id = 'nbns-interfaces'
#    def __call__(self, script_element: etreeElement, session: Session):
#        pass


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
        message = _l('Message signing enabled but not required')
        if elem.strip() == "Message signing enabled but not required":
            with force_locale(locale):
                issue = session.scalars(sa.select(models.Issue).where(models.Issue.title == str(message))).first()
                if issue is None:
                    issue_status = session.scalars(sa.select(models.IssueStatus).where(models.IssueStatus.string_slug == 'confirmed')).first()
                    if issue_status is None:
                        return None
                    description = _l("There is no SMB signature requirement for some hosts.")
                    fix = _l("Enable SMB signature requirement for all hosts")
                    riscs = _l("The absence of an SMB signature allows an attacker to perform MitM attacks")
                    issue = models.Issue(project=project, title=sanitizer.escape(str(message), models.Issue.title.type.length), cvss=6.0, description=str(description),
                                         fix=str(fix), riscs=str(riscs), status=issue_status, created_by_id=current_user_id)
                    session.add(issue)
                for serv in host.services:
                    if serv.port == 445:
                        issue.services.add(serv)
                        break
                session.commit()
        else:
            return None
        return ''