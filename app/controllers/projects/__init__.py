from flask import Blueprint, url_for
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo, SidebarElement, SidebarElementSublink
from app.helpers.projects_helpers import EnvironmentObjectAttrs, register_environment, check_if_same_type
from app.models import Project, ProjectAdditionalField
from markupsafe import Markup
from app.extensions.moment import moment
from flask_babel import lazy_gettext as _l, pgettext
from flask_login import current_user, login_required
from app.helpers.roles import project_role_can_make_action


bp = Blueprint('projects', __name__, url_prefix='/projects')


@bp.before_request
@login_required
def check_login_required():
    pass


import app.controllers.projects.routes
import app.controllers.projects.additional_parameters_routes


# Боковая панель, окружение шаблона:
def sidebar(current_object, act: str, **kwargs):
    con = current_object.__class__.__name__
    if con == 'Project':
        proj = current_object
    elif "proj" in kwargs:
        proj = kwargs["proj"]
    else:
        proj = current_object.project
    sels = []
    sel1 = SidebarElementSublink(_l("Main information"), url_for('projects.project_show', project_id=proj.id), con=='Project' and act=='show')
    sels.append(sel1)
    if project_role_can_make_action(current_user, proj, 'show_charts'):
        sel2 = SidebarElementSublink(_l("Status charts"), url_for('projects.project_diagrams', project_id=proj.id), con=='Project' and act == 'project_diagrams')
        sels.append(sel2)
    if project_role_can_make_action(current_user, proj, 'show_additional_parameters'):
        sel3 = SidebarElementSublink(_l("Additional parameters"), url_for('projects.project_additional_parameter_index', project_id=proj.id), con=='Project' and act=='project_additional_parameters_index')
        sels.append(sel3)
    return [SidebarElement("Страница проекта", url_for('projects.project_show', project_id=proj.id), "fa fa-home", con=='Project', sels)]


@check_if_same_type(Project)
def environment(obj, action, **kwargs):
    if action == 'show':
        title = _l("Project #%(project_id)s", project_id=obj.id)
        acts = []
        if project_role_can_make_action(current_user, obj, 'update') and not obj.archived:
            act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('projects.project_edit', project_id=obj.id))
            acts.append(act1)
        if project_role_can_make_action(current_user, obj, "archive") and not obj.archived:
            act3 = CurrentObjectAction(pgettext("todo", "Archive"), "fa-solid fa-box-archive", url_for('projects.project_archive', project_id=obj.id), confirm=_l("Are you sure you want to archive this project?"), btn_class="btn-light", method="DELETE")
            acts.append(act3)
        if project_role_can_make_action(current_user, obj, 'delete'):
            act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('projects.project_delete', project_id=obj.id), confirm=_l("Are you sure you want to delete this project?"), btn_class='btn-danger', method='DELETE')
            acts.append(act2)
        current_object = CurrentObjectInfo(obj.fulltitle, obj.Meta.icon, subtitle=Markup(_l('Created by <a href="%(link)s">%(created_by)s</a> %(date)s', link=url_for('users.user_show', user_id=obj.created_by.id), created_by=obj.created_by.title, date=str(moment(obj.created_at).fromNow()))), actions=acts)
    elif action == 'new':
        title = _l("Add new project")
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus")
    elif action == 'edit':
        title = _l("Edit project #%(project_id)s", project_id=obj.id)
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen")
    elif action == 'project_diagrams':
        title = _l("Status charts")
        current_object = CurrentObjectInfo(title, "fa-solid fa-chart-pie", subtitle=_l("Summary statistics for the project #%(project_id)s", project_id=obj.id))
    elif action == 'project_additional_parameters_index':
        title = _l("Additional parameters for Project #%(project_id)s", project_id=obj.id)
        act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('projects.project_additional_parameter_edit', project_id=obj.id))
        current_object = CurrentObjectInfo(_l("Additional parameters for Project %(project_fulltitle)s", project_fulltitle=obj.fulltitle), ProjectAdditionalField.Meta.icon, actions=[act1])
    elif action == 'project_additional_parameter_edit':
        title = _l("Edit addtional parameters for Project #%(project_id)s", project_id=obj.id)
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen", subtitle=obj.fulltitle) 
    return {'title': title, 'current_object': current_object, 'archived': bool(obj.archived)}

register_environment(EnvironmentObjectAttrs('Project', sidebar, environment), None)