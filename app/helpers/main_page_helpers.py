from app import db
from flask import url_for, current_app
from flask_login import current_user
from .general_helpers import SidebarElement, SidebarElementSublink
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo
from flask_babel import lazy_gettext as _l


class DefaultSidebar:
    def __init__(self, obj: str, act: str):
        sel11 = SidebarElementSublink(_l("Home page"), url_for('main_page.main_page'), obj=='main_page' and act=='show')
        se1 = SidebarElement(_l("Home page"), url_for('main_page.main_page'), "fa fa-home", obj=='main_page', [sel11])
        sel21 = SidebarElementSublink(_l("All projects"), url_for('projects.project_index'), obj=='Project' and act=='index')
        sel22 = SidebarElementSublink(_l("Add new project"), url_for('projects.project_new'), obj=='Project' and act=='new')
        se2 = SidebarElement(_l("List of projects"), url_for('projects.project_index'), "fa-solid fa-list-check", obj=='Project', [sel21, sel22])
        sel31 = SidebarElementSublink(_l("Root directory"), url_for('wiki_pages.pagedirectory_index', directory_id=0), obj=='WikiPage' and act=='index')
        sel32 = SidebarElementSublink(_l("Add new directory"), url_for('wiki_pages.pagedirectory_new'), obj=='WikiDirectory' and act=='new_dir')
        sel33 = SidebarElementSublink(_l("Add new page"), url_for('wiki_pages.wikipage_new'), obj=='WikiPage' and act=='new_page')
        se3 = SidebarElement(_l("Knowledge base"), url_for('wiki_pages.pagedirectory_index', directory_id=0), "fa-brands fa-wikipedia-w", obj=='WikiPage', [sel31, sel32, sel33])
        sel41 = SidebarElementSublink(_l("CVE pages"), url_for('cves.cve_index'), obj=='CriticalVulnerability' and act=='index')
        se4 = SidebarElement(_l("CVE"), url_for('cves.cve_index'), 'fa-solid fa-droplet', obj=='CriticalVulnerability', [sel41])
        sel51 = SidebarElementSublink(_l("List of users"), url_for('users.user_index'), obj=='User' and act=='index')
        sel52 = SidebarElementSublink(_l("My page"), url_for('users.user_show', user_id=current_user.id), obj=='User' and act=='show')
        sel53 = SidebarElementSublink(_l("Add new user"), url_for('users.user_new'), obj=='User' and act == 'new')
        se5 = SidebarElement(_l("Users"), url_for('users.user_index'), 'fa-solid fa-users', obj=='User', [sel51, sel52, sel53])
        self.se = [se1, se2, se3, se4, se5]
        if not current_user.is_anonymous and current_user.is_administrator:
            sel61 = SidebarElementSublink(_l("The Admin Panel"), url_for('admin.index'), obj=='admin')
            sel62 = SidebarElementSublink(_l("Enumeration objects"), url_for('admin.object_index'), obj=='admin')
            sel63 = SidebarElementSublink(_l("State objects"), url_for('admin.status_index'), obj=='admin')
            sel64 = SidebarElementSublink(_l("Templates"), url_for('admin.issue_template_index'), obj=='admin')
            sel65 = SidebarElementSublink(_l("Project roles"), url_for('admin.project_role_index'), obj=='admin')
            se6 = SidebarElement(_l("Admin"), url_for('admin.index'), "fa-solid fa-gears", obj=='admin', [sel61, sel62, sel63, sel64, sel65])
            self.se.append(se6)

    def __call__(self):
        return self.se


class DefaultEnvironment:
    def __init__(self, obj: str, op: str, **kwargs):
        # Title page
        if obj == 'main_page' and op == 'show':
            current_object = CurrentObjectInfo(current_app.config["GlobalSettings"].main_page_name, "fa-solid fa-user-secret")
            title = _l("Title page")
        # Projects
        elif obj == 'Project' and op == 'index':
            act1 = CurrentObjectAction(_l("Add new project"), "fa-solid fa-square-plus", url_for('projects.project_new'))
            current_object = CurrentObjectInfo(_l("List of all projects"), "fa-solid fa-list-check", subtitle=_l('Projects, created in PCF'), actions=[act1])
            title = _l("All projects")
        elif obj == "Project" and op == 'new':
            current_object = CurrentObjectInfo(_l("Add new project"), "fa-solid fa-square-plus")
            title = _l("Add new project")
        # Wiki pages
        elif obj == 'WikiPage' and op == 'index':
            act1 = CurrentObjectAction(_l("Add new page"), "fa-solid fa-file-circle-plus", url_for('wiki_pages.wikipage_new'))
            act2 = CurrentObjectAction(_l("Add new directory"), 'fa-solid fa-folder-plus', url_for('wiki_pages.pagedirectory_new'))
            current_object = CurrentObjectInfo(_l('Wiki pages'), "fa-brands fa-wikipedia-w", actions=[act1, act2])
            title = _l("Knowledge base")
        elif obj == 'WikiPage' and op == 'new':
            current_object = CurrentObjectInfo(_l("Add new Wiki page"), 'fa-brands fa-wikipedia-w')
            title = _l("Add a page to the knowledge base")
        elif obj == 'WikiPage' and op == 'show':
            act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('wiki_pages.wikipage_edit', wikipage_id=kwargs['obj_val'].id))
            act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('wiki_pages.wikipage_delete', wikipage_id=kwargs['obj_val'].id), confirm='Вы уверены, что хотите удалить эту страницу?', btn_class='btn-danger', method='DELETE')
            current_object = CurrentObjectInfo(_l("Knowledge Base Page"), 'fa-brands fa-wikipedia-w', actions=[act1, act2])
            title = kwargs['obj_val'].title
        elif obj == 'WikiPage' and op == 'edit':
            current_object = CurrentObjectInfo(_l("Editing the knowledge base page"), 'fa-brands fa-wikipedia-w')
            title = _l("Editing the knowledge base page")
        elif obj == 'WikiDirectory' and op == 'new_dir':
            current_object = CurrentObjectInfo(_l("Add new directory"), 'fa-solid fa-folder-plus')
            title = _l("Add new directory to knowledge base")
        # Critical vulnerabilities
        elif obj == 'CriticalVulnerability' and op == 'index':
            act1 = CurrentObjectAction(_l("Add new critical vulnerability"), 'fa-solid fa-square-plus', url_for('cves.cve_new'))
            current_object = CurrentObjectInfo(_l("CVE list"), 'fa-solid fa-droplet', actions=[act1])
            title = _l("Critical vulnerabilities")
        elif obj == "CriticalVulnerability" and op == "new":
            current_object = CurrentObjectInfo(_l("Add a new entry about a critical vulnerability"), "fa-solid fa-square-plus")
            title = _l("Add new critical vulnerability")
        elif obj == "CriticalVulnerability" and op == "show":
            act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('cves.cve_edit', cve_id=kwargs['obj_val'].id))
            act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for("cves.cve_delete", cve_id=kwargs['obj_val'].id, confirm='Вы уверены, что хотите удалить эту запись о критической уязвимости?'), btn_class='btn-danger', method='DELETE')
            current_object = CurrentObjectInfo(_l("Critical vulnerability «%(title)s»", title=kwargs['obj_val'].title), "fa-solid fa-droplet", actions=[act1, act2])
            title = _l("Critical vulnerability «CVE-%(year)s-%(identifier)s»", year=kwargs['obj_val'].year, identifier=kwargs['obj_val'].identifier)
        elif obj == 'CriticalVulnerability' and op == 'edit':
            current_object = CurrentObjectInfo(_l("Edit critical vulnerability"), "fa-solid fa-square-pen")
            title = _l("Edit critical vulnerability «CVE-%(year)s-%(identifier)s»", year=kwargs['obj_val'].year, identifier=kwargs['obj_val'].identifier)
        # Users
        elif obj == 'User' and op == 'index':
            if not current_user.is_anonymous and current_user.is_administrator:
                act1 = CurrentObjectAction(_l("Add new user"), 'fa-solid fa-user-plus', url_for('users.user_new'))
                acts = [act1]
            else:
                acts = []
            current_object = CurrentObjectInfo(_l("User list"), "fa-solid fa-users", actions=acts)
            title = _l("All users")
        elif obj == 'User' and op == 'new':
            current_object = CurrentObjectInfo(_l("Add new user"), 'fa-solid fa-user-plus')
            title = _l("Add new user")
        sidebar_data = DefaultSidebar(obj, op)()
        self.context = {'title': title, 'current_object': current_object,
                        'sidebar_data': sidebar_data}

    def __call__(self):
        return self.context
