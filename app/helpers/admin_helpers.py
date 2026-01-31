from flask import url_for
from .general_helpers import SidebarElement, SidebarElementSublink
from .general_helpers import CurrentObjectAction, CurrentObjectInfo
from app import db
import app.models as models
from flask_babel import lazy_gettext as _l
from typing import Any, List
import inspect as python_inspect


enumerated_object_list: List[Any] = []  # This is a list of all the enumerations that can be processed in the /admin panel
status_object_list: List[Any] = []  # This is a list of all objects of the "Status" type - that is, the attributes of the object for which the conditions for transition from one state to another are defined.


def register_enumerated_object(*obj):
    global enumerated_object_list
    enumerated_object_list.extend(obj)


def register_status_object(*obj):
    global status_object_list
    status_object_list.extend(obj)


def project_enumerated_object(obj: Any):
    global enumerated_object_list
    if not hasattr(obj, 'Meta'):
        raise AttributeError("Project enumerated object must have an 'Meta' attribute")
    if not hasattr(obj.Meta, 'verbose_name'):
        raise AttributeError("Project enumerated object Meta must have an attribute 'verbose_name'")
    if not hasattr(obj.Meta, "verbose_name_plural"):
        raise AttributeError("Project enumerated object Meta must have an 'verbose_name_plural' attribute")
    if not hasattr(obj.Meta, 'title_new'):
        raise AttributeError("Project enumerated object Meta must have an attribute 'title_new'")
    if not hasattr(obj.Meta, 'column_index') or not isinstance(obj.Meta.column_index, list):
        raise AttributeError("Project enumerated object Meta must have an attribute 'column_index' as instance of 'list' class")
    enumerated_object_list.append(obj)
    return obj


def project_status_object(obj: Any):
    """
    Appends an object to the global status object list and returns the object.
    
    This function is used as class decorator for project objects that have status:
    
    @project_status_object
    class SomeModel(db.model):
        ...

    Args:
        obj (Any): The object to be appended to the status object list.

    Returns:
        Any: The object that was appended to the list.
    """
    global status_object_list
    status_object_list.append(obj)
    return obj


def get_enumerated_objects():
    global enumerated_object_list
    return enumerated_object_list


def get_status_objects() -> None:
    global status_object_list
    return status_object_list


# Roles
PROJECT_OBJECTS = set()
def register_new_project_object(obj):
    ''' Added new project object to list '''
    global PROJECT_OBJECTS
    if not hasattr(obj, 'Meta'):
        raise AttributeError("Project object must have an 'Meta' attribute")
    if not hasattr(obj.Meta, 'project_permission_actions'):
        raise AttributeError("Project object Meta must have an 'project_permission_actions' attribute")
    PROJECT_OBJECTS.add(obj)


def project_object_with_permissions(obj):
    global PROJECT_OBJECTS
    if not hasattr(obj, 'Meta'):
        raise AttributeError("Project object must have an 'Meta' attribute")
    if not hasattr(obj.Meta, 'project_permission_actions'):
        raise AttributeError("Project object Meta must have an 'project_permission_actions' attribute")
    PROJECT_OBJECTS.add(obj)
    return obj


def get_all_project_objects():
    global PROJECT_OBJECTS
    for i in PROJECT_OBJECTS:
        yield i


class DefaultSidebar:
    def __init__(self, address: str, obj=None):
        # TODO: import inspect; inspect.stack()[1].function
        global enumerated_object_list, status_object_list
        sel11 = SidebarElementSublink(_l("List of tools"), url_for('admin.index'), address=='index')
        sel12 = SidebarElementSublink(_l("Title page"), url_for('admin.admin_main_info_edit'), address=='admin_main_info_edit')
        se1 = SidebarElement(_l("Administration Tools"), url_for('admin.index'), "fa-solid fa-screwdriver-wrench", address in ['index', 'admin_main_info_edit'], [sel11, sel12])
        sels2 = [SidebarElementSublink(_l("All enumeration objects"), url_for('admin.object_index'), address=='object_index')]
        for e in enumerated_object_list:
            nsel = SidebarElementSublink(e.Meta.verbose_name_plural, url_for('admin.object_type_index', object_type=e.__name__), address=='object_type_index' and obj.__name__==e.__name__)
            sels2.append(nsel)
        se2 = SidebarElement(_l("Enumeration objects"), url_for('admin.object_index'), 'fa-solid fa-list-ol', address in ['object_type_index', 'object_type_new', 'object_type_edit'], sels2)
        sels3 = [SidebarElementSublink(_l("All state objects"), url_for('admin.status_index'), address=='status_index')]
        for e in status_object_list:
            nsel = SidebarElementSublink(e.Meta.verbose_name_plural, url_for('admin.status_type_transits', object_type=e.__name__), address=='status_type_transits' and obj.__name__==e.__name__)
            sels3.append(nsel)
        se3 = SidebarElement(_l("State objects"), url_for('admin.status_index'), "fa-solid fa-satellite", address in ['status_type_transits', 'status_index'], sels3)
        sel41 = SidebarElementSublink(_l("Object with templates"), url_for('admin.object_template_list'), address=='object_template_list')
        sel42 = SidebarElementSublink(models.IssueTemplate.Meta.verbose_name_plural, url_for('admin.issue_template_index'), address=='issue_template_index')
        sel43 = SidebarElementSublink(models.ProjectTaskTemplate.Meta.verbose_name_plural, url_for('admin.task_template_index'), address=='task_template_index')
        sel44 = SidebarElementSublink(models.CredentialImportTemplate.Meta.verbose_name_plural, url_for('admin.credential_template_index'), address=='credential_template_index')
        sel45 = SidebarElementSublink(models.ProjectReportTemplate.Meta.verbose_name_plural, url_for('admin.report_template_index'), address=='report_template_index')
        se4 = SidebarElement(_l("Templates"), url_for('admin.issue_template_index'), "fa-solid fa-gopuram", '_template_' in address, [sel41, sel42, sel43, sel44, sel45])
        sel51 = SidebarElementSublink(_l("All files"), url_for('admin.admin_file_index'), address=="admin_file_index")
        se5 = SidebarElement(models.FileData.Meta.verbose_name_plural, url_for('admin.admin_file_index'), models.FileData.Meta.icon, address=='admin_file_index')
        sel61 = SidebarElementSublink(_l("Background task states"), url_for('admin.background_tasks_index'), address=='background_tasks_index')
        sel62 = SidebarElementSublink(_l("Background task options"), url_for('admin.background_tasks_options_index'), address=='background_tasks_options_index')
        sel63 = SidebarElementSublink(_l("Hooks"), url_for('admin.hook_index'), address in ['hook_index', 'hook_new', 'hook_edit'])
        se6 = SidebarElement(_l("Background tasks"), url_for('admin.background_tasks_index'), "fa-solid fa-bars-progress", address in ['background_tasks_index', 'background_tasks_options_index', 'hook_index', 'hook_new', 'hook_edit'], [sel61, sel62, sel63])
        sel71 = SidebarElementSublink(models.ProjectRole.Meta.verbose_name_plural, url_for('admin.project_role_index'), address=='project_role_index')
        sel72 = SidebarElementSublink(_l("Add new project role"), url_for('admin.project_role_new'), address=='project_role_new')
        sel73 = SidebarElementSublink(_l("Edit role permissions"), url_for('admin.project_role_permissions'), address=='project_role_permissions')
        sel74 = SidebarElementSublink(models.UserPosition.Meta.verbose_name_plural, url_for('admin.user_positions_index'), address=='user_positions_index')
        sel75 = SidebarElementSublink(_l("Add new user position"), url_for('admin.user_positions_new'), address=='user_positions_new')
        sel76 = SidebarElementSublink(_l("Edit user position permissions"), url_for('admin.user_positions_permissions'), address=='user_positions_permissions')
        se7 = SidebarElement(_l("Permissions"), url_for('admin.project_role_index'), models.ProjectRole.Meta.icon, address.startswith('project_role_') or address.startswith("user_positions_"), [sel71, sel72, sel73, sel74, sel75, sel76])
        sel81 = SidebarElementSublink(_l("Password Policy"), url_for('admin.authentication_password_policy_settings'), address=='authentication_password_policy_settings')
        se8 = SidebarElement(_l("Authentication"), url_for('admin.authentication_password_policy_settings'), "fa-solid fa-person-hiking", address.startswith('authentication_'), [sel81])
        sel91 = SidebarElementSublink(models.ProjectAdditionalField.Meta.verbose_name_plural, url_for('admin.project_additional_parameters_index'), address=='project_additional_parameters_index')
        sel92 = SidebarElementSublink(_l("Add new project additional field"), url_for('admin.project_additional_parameters_new'), address=='project_additional_parameters_new')
        se9 = SidebarElement(_l("Project parameters"), url_for('admin.project_additional_parameters_index'), "fa-solid fa-building-columns", address.startswith('project_additional_parameters'), [sel91, sel92])
        sel101 = SidebarElementSublink(_l("Console"), url_for('admin.console'), address=='console')
        se10 = SidebarElement(_l("Low-level operations"), url_for('admin.console'), "fa-solid fa-terminal", address in ['console'], [sel101])
        self.se = [se1, se2, se3, se4, se5, se6, se7, se8, se9, se10]

    def __call__(self):
        return self.se


class DefaultEnvironment:
    def __init__(self, obj=None):
        address = python_inspect.stack()[1].function
        match address:
            case 'index':
                title = _l("Administration")
                current_object = CurrentObjectInfo(_l("The administration panel. List of administrative tools"), 'fa-solid fa-screwdriver-wrench')
            case 'admin_main_info_edit':
                title = _l("Editing information about an organization")
                current_object = CurrentObjectInfo(_l("The administration panel. The title page"), 'fa-solid fa-house-chimney-crack')
            case 'object_index':
                title = _l("Administration of enumeration objects")
                current_object = CurrentObjectInfo(_l("The administration panel. Enumeration objects"), 'fa-solid fa-list-ol', subtitle=_l("Enumerations are simple objects (most often consisting of 1-2 attributes) that are referenced by other objects."))
            case 'object_type_index':
                title = obj.Meta.verbose_name_plural
                act1 = CurrentObjectAction(_l("Add"), "fa-solid fa-square-plus", url_for('admin.object_type_new', object_type=obj.__name__))
                current_object = CurrentObjectInfo(obj.Meta.verbose_name_plural, "fa-regular fa-rectangle-list", actions=[act1])
            case 'object_type_new':
                title = obj.Meta.title_new
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus")
            case 'object_type_edit':
                title = _l("Edit %(object_name)s", object_name=obj.Meta.verbose_name)
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen")
            case 'status_index':
                title = _l("The administration panel. State object")
                current_object = CurrentObjectInfo(title, 'fa-solid fa-satellite', subtitle=_l("State objects are objects that are attributes of other objects, for which conditions for changing to a different value in the attributes are defined."))
            case 'status_type_transits':
                title = _l("Edit transitions between states for an object «%(name)s»", name=obj.Meta.verbose_name)
                current_object = CurrentObjectInfo(title, 'fa-solid fa-square-pen', subtitle=_l("Simple conditions for changing to a different value can be defined for the status object on this page"))
            case 'issue_template_index':
                title = models.IssueTemplate.Meta.verbose_name_plural
                act1 = CurrentObjectAction(_l("Add new template"), "fa-solid fa-square-plus", url_for('admin.issue_template_new'))
                current_object = CurrentObjectInfo(models.IssueTemplate.Meta.verbose_name_plural, models.IssueTemplate.Meta.icon, subtitle=_l("Issue templates allow you to speed up the addition of new issue to the project"), actions=[act1])
            case 'issue_template_new':
                title = _l("Add new issue template")
                current_object = CurrentObjectInfo(_l("Add new issue template"), "fa-solid fa-square-plus")
            case 'issue_template_show':
                title = _l("Issue template #%(templ_id)s", templ_id=obj.id)
                act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('admin.issue_template_edit', template_id=obj.id))
                act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('admin.issue_template_delete', template_id=obj.id), confirm=_l("Are you sure you want to delete this template?"), btn_class='btn-danger', method='DELETE')
                current_object = CurrentObjectInfo(_l("Issue template «%(title)s»", title=obj.title), models.IssueTemplate.Meta.icon, actions=[act1, act2])
            case 'issue_template_edit':
                title = _l("Edit issue template #%(templ_id)s", templ_id=obj.id)
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen")
            case 'admin_file_index':
                title = _l("File Administration")
                current_object = CurrentObjectInfo(_l("Files"), models.FileData.Meta.icon, subtitle=_l("All files saved in the database"))
            case 'background_tasks_index':
                title = _l("Background tasks")
                current_object = CurrentObjectInfo(title, "fa-solid fa-bars-progress", subtitle=_l("Tasks performed in the background via Celery"))
            case 'background_tasks_options_index':
                title = _l("Background Task Options")
                current_object = CurrentObjectInfo(title, 'fa-solid fa-bars-progress', subtitle=_l("Options for tasks running in the background"))
            case 'project_role_index':
                title = _l("Project roles list")
                act1 = CurrentObjectAction(_l("Add new project role"), "fa-solid fa-square-plus", url_for('admin.project_role_new'))
                act2 = CurrentObjectAction(_l("Edit permissions for roles"), "fa-solid fa-person-walking-arrow-loop-left", url_for('admin.project_role_permissions'))
                current_object = CurrentObjectInfo(title, models.ProjectRole.Meta.icon, subtitle=_l("A list of all the roles that a user can have on a project"), actions=[act1, act2])
            case 'project_role_new':
                title = _l("Add new project role")
                current_object = CurrentObjectInfo(title, models.ProjectRole.Meta.icon)
            case 'project_role_edit':
                title = _l("Edit project role #%(role_id)s", role_id=obj.id)
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen")
            case 'project_role_permissions':
                title = _l("Edit permissions for roles")
                current_object = CurrentObjectInfo(title, "fa-solid fa-person-walking-arrow-loop-left", subtitle="List of actions available for this role on the project")
            case 'user_positions_index':
                title = _l("User positions")
                act1 = CurrentObjectAction(_l("Add new position"), "fa-solid fa-square-plus", url_for('admin.user_positions_new'))
                act2 = CurrentObjectAction(_l("Edit permissions for positions"), "fa-solid fa-person-walking-arrow-loop-left", url_for('admin.user_positions_permissions'))
                current_object = CurrentObjectInfo(title, models.UserPosition.Meta.icon, actions=[act1, act2])
            case 'user_positions_new':
                title = _l("Add new position")
                current_object = CurrentObjectInfo(title, models.UserPosition.Meta.icon)
            case 'user_positions_edit':
                title = _l("Edit position #%(position_id)s", position_id=obj.id)
                current_object = CurrentObjectInfo(title, models.UserPosition.Meta.icon)
            case 'user_positions_permissions':
                title = _l("Edit permissions for user positions")
                current_object = CurrentObjectInfo(title, "fa-solid fa-person-walking-arrow-loop-left", subtitle="List of actions available for this position on the project")
            case 'task_template_index':
                title = models.ProjectTaskTemplate.Meta.verbose_name_plural
                act1 = CurrentObjectAction(_l("Add new template"), "fa-solid fa-square-plus", url_for('admin.task_template_new'))
                current_object = CurrentObjectInfo(models.ProjectTaskTemplate.Meta.verbose_name_plural, models.ProjectTaskTemplate.Meta.icon, subtitle=_l("Task templates allow you to speed up the addition of new tasks to the project"), actions=[act1])
            case 'task_template_new':
                title = _l("Add new task template")
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus")
            case 'task_template_show':
                title = _l("Task template #%(templ_id)s", templ_id=obj.id)
                act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('admin.task_template_edit', template_id=obj.id))
                act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('admin.task_template_delete', template_id=obj.id), confirm=_l("Are you sure you want to delete this template?"), btn_class='btn-danger', method='DELETE')
                current_object = CurrentObjectInfo(_l("Task template «%(title)s»", title=obj.title), models.ProjectTaskTemplate.Meta.icon, actions=[act1, act2])
            case 'task_template_edit':
                title = _l("Edit task template #%(templ_id)s", templ_id=obj.id)
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen")
            case 'report_template_index':
                title = models.ProjectReportTemplate.Meta.verbose_name_plural
                act1 = CurrentObjectAction(_l("Add new report template"), "fa-solid fa-square-plus", url_for('admin.report_template_new'))
                current_object = CurrentObjectInfo(title, models.ProjectReportTemplate.Meta.icon, subtitle=_l("Report templates is a Jinja2 templater file, in which one paramether is passed - current project"), actions=[act1])
            case 'report_template_new':
                title = _l("Add new project report template")
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus", subtitle=_l("Report templates is a Jinja2 templater file, in which one paramether is passed - current project"))
            case 'object_template_list':
                title = _l("List of all template for objects")
                current_object = CurrentObjectInfo(title, "fa-solid fa-gopuram", subtitle=_l("Templates help you create different types of objects faster."))
            case 'report_template_show':
                title = _l("Report template #%(templ_id)s", templ_id=obj.id)
                act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('admin.report_template_edit', template_id=obj.id))
                act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('admin.report_template_delete', template_id=obj.id), confirm=_l("Are you sure you want to delete this template?"), btn_class='btn-danger', method='DELETE')
                current_object = CurrentObjectInfo(_l("Report template #%(templ_id)s: «%(title)s»", templ_id=obj.id, title=obj.title), models.ProjectReportTemplate.Meta.icon, actions=[act1, act2])
            case 'report_template_edit':
                title = _l("Edit report template #%(templ_id)s", templ_id=obj.id)
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen")
            case 'credential_template_index':
                title = _l("Template of credentials multiple import")
                act1 = CurrentObjectAction(_l("Add new template"), "fa-solid fa-square-plus", url_for('admin.credential_template_new'))
                current_object = CurrentObjectInfo(title, models.CredentialImportTemplate.Meta.icon, subtitle=_l("Templates that help and simplify the import of credential output from various collection systems"), actions=[act1])
            case 'credential_template_new':
                title = _l("Add new credential import template")
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus", subtitle="The parameters are inserted into the credentials import form")
            case 'credential_template_show':
                title = _l("Credential import template #%(templ_id)s", templ_id=obj.id)
                act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('admin.credential_template_edit', template_id=obj.id))
                act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for("admin.credential_template_delete", template_id=obj.id), confirm=_l("Are you sure you want to delete this template?"), btn_class='btn-danger', method='DELETE')
                current_object = CurrentObjectInfo(title, models.CredentialImportTemplate.Meta.icon, subtitle=_l("A template that allows you to quickly fill in the fields for importing credentials."), actions=[act1, act2])
            case 'credential_template_edit':
                title = _l("Edit credential import template #%(templ_id)s", templ_id=obj.id)
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen")
            case "authentication_password_policy_settings":
                title = _l("Edit password policy settings")
                current_object = CurrentObjectInfo(title, "fa-solid fa-user-astronaut", subtitle=_l("Password complexity parameters to be set for users"))
            case 'project_additional_parameters_index':
                title = _l("All project additional parameters")
                act1 = CurrentObjectAction(_l("Add new project field"), "fa-solid fa-square-plus", url_for('admin.project_additional_parameters_new'))
                act2 = CurrentObjectAction(_l("Add new group"), "fa-solid fa-campground", url_for('admin.object_type_new', object_type='ProjectAdditionalFieldGroup'))
                current_object = CurrentObjectInfo(title, models.ProjectAdditionalField.Meta.icon, subtitle=_l("Parameters, that was being assigned to every project"), actions=[act1, act2])
            case 'project_additional_parameters_new':
                title = _l("Add new project additional field")
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus")
            case 'project_additional_parameters_edit':
                title = _l("Edit project additional field #%(field_id)s", field_id=obj.id)
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen")
            case 'console':
                title = _l("Console")
                current_object = CurrentObjectInfo(title, "fa-solid fa-terminal")
            case 'hook_index':
                title = _l("All hooks")
                act1 = CurrentObjectAction(_l("Add new hook"), "fa-solid fa-square-plus", url_for('admin.hook_new'))
                current_object = CurrentObjectInfo(title, models.Hook.Meta.icon, subtitle=_l("Hooks are used to execute custom code when certain events occur."), actions=[act1])
            case 'hook_new':
                title = _l("Add new hook")
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus")
            case 'hook_edit':
                title = _l("Edit hook #%(hook_id)s", hook_id=obj.id)
                current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen")

        sidebar_data = DefaultSidebar(address, obj)()
        self.context = {'title': title, 'current_object': current_object,
                        'sidebar_data': sidebar_data}

    def __call__(self):
        return self.context
