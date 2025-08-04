from app import db
import app.models as models
from flask import url_for, current_app
from flask_login import current_user
from .general_helpers import SidebarElement, SidebarElementSublink
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo
from flask_babel import lazy_gettext as _l


class DefaultSidebar:
    def __init__(self, obj: str, act: str):
        from app.helpers.roles import user_position_can_make_action
        ses = []
        sel11 = SidebarElementSublink(_l("Home page"), url_for('main_page.main_page'), obj=='main_page' and act=='show')
        se1 = SidebarElement(_l("Home page"), url_for('main_page.main_page'), "fa fa-home", obj=='main_page', [sel11])
        ses.append(se1)
        sels = []
        if user_position_can_make_action(current_user, models.Project, 'index'):
            sel21 = SidebarElementSublink(_l("All projects"), url_for('projects.project_index'), obj=='Project' and act=='index')
            sels.append(sel21)
        if user_position_can_make_action(current_user, models.Project, 'create'):
            sel22 = SidebarElementSublink(_l("Add new project"), url_for('projects.project_new'), obj=='Project' and act=='new')
            sels.append(sel22)
        if len(sels) > 0:
            se2 = SidebarElement(_l("List of projects"), url_for('projects.project_index'), "fa-solid fa-list-check", obj=='Project', sels)
            ses.append(se2)
        sels_wiki = []
        if user_position_can_make_action(current_user, models.WikiDirectory, 'index'):
            sel31 = SidebarElementSublink(_l("Root directory"), url_for('wiki_pages.pagedirectory_index', directory_id=0), obj=='WikiPage' and act=='index')
            sels_wiki.append(sel31)
        if user_position_can_make_action(current_user, models.WikiDirectory, 'create'):
            sel32 = SidebarElementSublink(_l("Add new directory"), url_for('wiki_pages.pagedirectory_new'), obj=='WikiDirectory' and act=='new_dir')
            sels_wiki.append(sel32)
        if user_position_can_make_action(current_user, models.WikiPage, 'create'):
            sel33 = SidebarElementSublink(_l("Add new page"), url_for('wiki_pages.wikipage_new'), obj=='WikiPage' and act=='new_page')
            sels_wiki.append(sel33)
        if len(sels_wiki) > 0:
            se3 = SidebarElement(_l("Knowledge base"), url_for('wiki_pages.pagedirectory_index', directory_id=0), "fa-brands fa-wikipedia-w", obj=='WikiPage', sels_wiki)
            ses.append(se3)
        sels_cve = []
        if user_position_can_make_action(current_user, models.CriticalVulnerability, 'index'):
            sel41 = SidebarElementSublink(_l("CVE pages"), url_for('cves.cve_index'), obj=='CriticalVulnerability' and act=='index')
            sels_cve.append(sel41)
        if len(sels_cve) > 0:
            se4 = SidebarElement(_l("CVE"), url_for('cves.cve_index'), 'fa-solid fa-droplet', obj=='CriticalVulnerability', sels_cve)
            ses.append(se4)
        sels_users = []
        sel51 = SidebarElementSublink(_l("List of users"), url_for('users.user_index'), obj=='User' and act=='index')
        sels_users.append(sel51)
        sel52 = SidebarElementSublink(_l("My page"), url_for('users.user_show', user_id=current_user.id), obj=='User' and act=='show')
        sels_users.append(sel52)
        if user_position_can_make_action(current_user, models.User, 'create'):
            sel53 = SidebarElementSublink(_l("Add new user"), url_for('users.user_new'), obj=='User' and act == 'new')
            sels_users.append(sel53)
        sel54 = SidebarElementSublink(models.Team.Meta.verbose_name_plural, url_for('users.team_index'), act=='team_index')
        sels_users.append(sel54)
        if user_position_can_make_action(current_user, models.Team, 'create'):
            sel55 = SidebarElementSublink(_l("Add new team"), url_for('users.team_new'), act=='team_new')
            sels_users.append(sel55)
        se5 = SidebarElement(_l("Users"), url_for('users.user_index'), 'fa-solid fa-users', obj in ['User', 'Team'], sels_users)
        ses.append(se5)
        self.se = ses
        if not current_user.is_anonymous and current_user.position.is_administrator:
            sel61 = SidebarElementSublink(_l("The Admin Panel"), url_for('admin.index'), obj=='admin')
            sel62 = SidebarElementSublink(_l("Enumeration objects"), url_for('admin.object_index'), obj=='admin')
            sel63 = SidebarElementSublink(_l("State objects"), url_for('admin.status_index'), obj=='admin')
            sel64 = SidebarElementSublink(models.IssueTemplate.Meta.verbose_name_plural, url_for('admin.issue_template_index'), obj=='admin')
            sel65 = SidebarElementSublink(models.ProjectTaskTemplate.Meta.verbose_name_plural, url_for('admin.task_template_index'), obj=='admin')
            sel66 = SidebarElementSublink(models.CredentialImportTemplate.Meta.verbose_name_plural, url_for('admin.credential_template_index'), obj=='admin')
            sel67 = SidebarElementSublink(models.ProjectReportTemplate.Meta.verbose_name_plural, url_for('admin.report_template_index'), obj=='admin')
            sel68 = SidebarElementSublink(_l("Background task states"), url_for('admin.background_tasks_index'), obj=='admin')
            sel69 = SidebarElementSublink(_l("Project roles"), url_for('admin.project_role_index'), obj=='admin')
            sel610 = SidebarElementSublink(models.FileData.Meta.verbose_name_plural, url_for('admin.admin_file_index'), obj=='admin')
            se6 = SidebarElement(_l("Admin"), url_for('admin.index'), "fa-solid fa-gears", obj=='admin', [sel61, sel62, sel63, sel64, sel65, sel66, sel67, sel68, sel69,sel610])
            self.se.append(se6)

    def __call__(self):
        return self.se


class DefaultEnvironment:
    def __init__(self, obj: str, op: str, **kwargs):
        from app.helpers.roles import user_position_can_make_action
        acts = []
        # Title page
        if obj == 'main_page' and op == 'show':
            current_object = CurrentObjectInfo(current_app.config["GlobalSettings"].main_page_name, "fa-solid fa-user-secret")
            title = _l("Title page")
        # Projects
        elif obj == 'Project' and op == 'index':
            if user_position_can_make_action(current_user, models.Project, 'create'):
                act1 = CurrentObjectAction(_l("Add new project"), "fa-solid fa-square-plus", url_for('projects.project_new'))
                acts.append(act1)
            current_object = CurrentObjectInfo(_l("List of all projects"), "fa-solid fa-list-check", subtitle=_l('Projects, created in PCF'), actions=acts)
            title = _l("All projects")
        elif obj == "Project" and op == 'new':
            current_object = CurrentObjectInfo(_l("Add new project"), "fa-solid fa-square-plus")
            title = _l("Add new project")
        # Wiki pages
        elif obj == 'WikiPage' and op == 'index':
            if user_position_can_make_action(current_user, models.WikiPage, 'create'):
                act1 = CurrentObjectAction(_l("Add new page"), "fa-solid fa-file-circle-plus", url_for('wiki_pages.wikipage_new'))
                acts.append(act1)
            if user_position_can_make_action(current_user, models.WikiDirectory, 'create'):
                act2 = CurrentObjectAction(_l("Add new directory"), 'fa-solid fa-folder-plus', url_for('wiki_pages.pagedirectory_new'))
                acts.append(act2)
            current_object = CurrentObjectInfo(_l('Wiki pages'), "fa-brands fa-wikipedia-w", actions=acts)
            title = _l("Knowledge base")
        elif obj == 'WikiPage' and op == 'new':
            current_object = CurrentObjectInfo(_l("Add new Wiki page"), 'fa-brands fa-wikipedia-w')
            title = _l("Add a page to the knowledge base")
        elif obj == 'WikiPage' and op == 'show':
            if user_position_can_make_action(current_user, models.WikiPage, 'update'):
                act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('wiki_pages.wikipage_edit', wikipage_id=kwargs['obj_val'].id))
                acts.append(act1)
            if user_position_can_make_action(current_user, models.WikiPage, 'delete'):
                act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('wiki_pages.wikipage_delete', wikipage_id=kwargs['obj_val'].id), confirm=_l("Are you sure you want to delete this page?"), btn_class='btn-danger', method='DELETE')
                acts.append(act2)
            current_object = CurrentObjectInfo(_l("Knowledge Base Page"), 'fa-brands fa-wikipedia-w', actions=acts)
            title = kwargs['obj_val'].title
        elif obj == 'WikiPage' and op == 'edit':
            current_object = CurrentObjectInfo(_l("Editing the knowledge base page"), 'fa-brands fa-wikipedia-w')
            title = _l("Editing the knowledge base page")
        elif obj == 'WikiDirectory' and op == 'new_dir':
            current_object = CurrentObjectInfo(_l("Add new directory"), 'fa-solid fa-folder-plus')
            title = _l("Add new directory to knowledge base")
        # Critical vulnerabilities
        elif obj == 'CriticalVulnerability' and op == 'index':
            if user_position_can_make_action(current_user, models.CriticalVulnerability, 'create'):
                act1 = CurrentObjectAction(_l("Add new critical vulnerability"), 'fa-solid fa-square-plus', url_for('cves.cve_new'))
                acts.append(act1)
            current_object = CurrentObjectInfo(_l("CVE list"), 'fa-solid fa-droplet', actions=acts)
            title = _l("Critical vulnerabilities")
        elif obj == "CriticalVulnerability" and op == "new":
            current_object = CurrentObjectInfo(_l("Add a new entry about a critical vulnerability"), "fa-solid fa-square-plus")
            title = _l("Add new critical vulnerability")
        elif obj == "CriticalVulnerability" and op == "show":
            if user_position_can_make_action(current_user, models.CriticalVulnerability, 'update'):
                act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('cves.cve_edit', cve_id=kwargs['obj_val'].id))
                acts.append(act1)
            if user_position_can_make_action(current_user, models.CriticalVulnerability, 'delete'):
                act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for("cves.cve_delete", cve_id=kwargs['obj_val'].id, confirm=_l("Are you sure you want to delete this Critical Vulnerability?")), btn_class='btn-danger', method='DELETE')
                acts.append(act2)
            current_object = CurrentObjectInfo(_l("Critical vulnerability «%(title)s»", title=kwargs['obj_val'].title), "fa-solid fa-droplet", actions=acts)
            title = _l("Critical vulnerability «CVE-%(year)s-%(identifier)s»", year=kwargs['obj_val'].year, identifier=kwargs['obj_val'].identifier)
        elif obj == 'CriticalVulnerability' and op == 'edit':
            current_object = CurrentObjectInfo(_l("Edit critical vulnerability"), "fa-solid fa-square-pen")
            title = _l("Edit critical vulnerability «CVE-%(year)s-%(identifier)s»", year=kwargs['obj_val'].year, identifier=kwargs['obj_val'].identifier)
        # Users
        elif obj == 'User' and op == 'index':
            if not current_user.is_anonymous and current_user.position.is_administrator:
                act1 = CurrentObjectAction(_l("Add new user"), 'fa-solid fa-user-plus', url_for('users.user_new'))
                acts = [act1]
            else:
                acts = []
            current_object = CurrentObjectInfo(_l("User list"), "fa-solid fa-users", actions=acts)
            title = _l("All users")
        elif obj == 'User' and op == 'new':
            current_object = CurrentObjectInfo(_l("Add new user"), 'fa-solid fa-user-plus')
            title = _l("Add new user")
        # Teams
        elif obj == 'Team' and op == 'team_index':
            title = _l("All teams")
            acts = []
            if user_position_can_make_action(current_user, models.Team, 'create'):
                act1 = CurrentObjectAction(_l("Add new team"), "fa-solid fa-square-plus", url_for('users.team_new'))
                acts.append(act1)
            current_object = CurrentObjectInfo(_l("Team list"), models.Team.Meta.icon, subtitle=models.Team.Meta.description, actions=acts)
        elif obj == 'Team' and op == 'team_new':
            title = _l("Add new team")
            current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus", subtitle=models.Team.Meta.description)
        elif obj == 'Team' and op == 'team_show':
            title = _l("Team #%(team_id)s", team_id=kwargs['obj_val'].id)
            if user_position_can_make_action(current_user, models.Team, 'update'):
                act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('users.team_edit', team_id=kwargs['obj_val'].id))
                acts.append(act1)
            if user_position_can_make_action(current_user, models.Team, 'delete'):
                act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('users.team_delete', team_id=kwargs['obj_val'].id), confirm=_l("Are you sure you want to delete this team?"), btn_class='btn-danger', method='DELETE')
                acts.append(act2)
            current_object = CurrentObjectInfo(_l("Team #%(team_id)s: «%(team_title)s»", team_id=kwargs['obj_val'].id, team_title=kwargs['obj_val'].title), models.Team.Meta.icon, subtitle=models.Team.Meta.description, actions=acts)
        elif obj == 'Team' and op == 'team_edit':
            title = _l("Edit team #%(team_id)s", team_id=kwargs['obj_val'].id)
            current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen")
        sidebar_data = DefaultSidebar(obj, op)()
        self.context = {'title': title, 'current_object': current_object,
                        'sidebar_data': sidebar_data}

    def __call__(self):
        return self.context
