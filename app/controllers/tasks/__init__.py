from flask import Blueprint, url_for
from flask_login import current_user
from app.models import ProjectTask
from app.helpers.projects_helpers import EnvironmentObjectAttrs, register_environment, check_if_same_type
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo, SidebarElement, SidebarElementSublink
from markupsafe import Markup
from app.extensions.moment import moment
from flask_babel import lazy_gettext as _l
from app.helpers.roles import project_role_can_make_action
from typing import Optional


bp = Blueprint('tasks', __name__, url_prefix='/tasks')


import app.controllers.tasks.routes
import app.controllers.tasks.websockets


def sidebar(current_object, act: str, **kwargs) -> Optional[SidebarElement]:
    con = current_object.__class__.__name__
    if con == 'Project':
        proj = current_object
    elif "proj" in kwargs:
        proj = kwargs["proj"]
    else:
        proj = current_object.project
    sels = []
    if project_role_can_make_action(current_user, ProjectTask(), 'index', project=proj):
        sel21 = SidebarElementSublink(_l("All tasks"), url_for('tasks.projecttask_index', project_id=proj.id), con=='ProjectTask' and act=='index')
        sels.append(sel21)
    if project_role_can_make_action(current_user, ProjectTask(), 'kanban', project=proj):
        sel_kanban = SidebarElementSublink(_l("Tasks Kanban board"), url_for('tasks.projecttask_kanban_board', project_id=proj.id), con=='ProjectTask' and act=='kanban-board')
        sels.append(sel_kanban)
    if project_role_can_make_action(current_user, ProjectTask(), 'index', project=proj):
        sel22 = SidebarElementSublink(_l("The tasks are on me"), url_for('tasks.projecttask_index_on_me', project_id=proj.id), con=='ProjectTask' and act=='index_on_me')
        sels.append(sel22)
    if project_role_can_make_action(current_user, ProjectTask(), 'create', project=proj):
        sel23 = SidebarElementSublink(_l("Add new task"), url_for('tasks.projecttask_new', project_id=proj.id), con=='ProjectTask' and act=='new')
        sels.append(sel23)
    if len(sels) == 0:
        return None
    return SidebarElement(_l("Tasks"), url_for('tasks.projecttask_index', project_id=proj.id), ProjectTask.Meta.icon_index, con=='ProjectTask', sels)


@check_if_same_type(ProjectTask)
def environment(obj, action, **kwargs) -> dict:
    if action == 'index':
        title = _l("All tasks")
        acts = []
        if project_role_can_make_action(current_user, ProjectTask(), 'create', project=obj.project):
            act1 = CurrentObjectAction(_l("Add new task"), "fa-solid fa-square-plus", url_for('tasks.projecttask_new', project_id=obj.project.id))
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("All tasks"), obj.Meta.icon_index, subtitle=obj.project.fulltitle, actions=acts)
    elif action == 'index_on_me':
        title = _l("The tasks are on me")
        act1 = CurrentObjectAction(_l("Add new task"), "fa-solid fa-square-plus", url_for('tasks.projecttask_new', project_id=obj.project.id, assigned_to_id=current_user.id))
        current_object = CurrentObjectInfo(_l("The tasks are on me"), obj.Meta.icon_index, subtitle=obj.project.fulltitle, actions=[act1])
    elif action == 'kanban-board':
        title = _l("Tasks Kanban board")
        acts = []
        if project_role_can_make_action(current_user, ProjectTask(), 'create', project=obj.project):
            act1 = CurrentObjectAction(_l("Add new task"), "fa-solid fa-square-plus", url_for("tasks.projecttask_new", project_id=obj.project.id))
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("Kanban board for task on project #%(project_id)s", project_id=obj.project.id), "fa-solid fa-clipboard", subtitle=obj.project.fulltitle, actions=acts)
    elif action == 'show':
        title = _l("Task #%(task_id)s", task_id=obj.id)
        acts = []
        if project_role_can_make_action(current_user, obj, 'update'):
            act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('tasks.projecttask_edit', projecttask_id=obj.id))
            acts.append(act1)
        if project_role_can_make_action(current_user, obj, 'delete'):
            act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('tasks.projecttask_delete', projecttask_id=obj.id), confirm="Вы уверены, что хотите удалить эту задачу?", btn_class='btn-danger', method='DELETE')
            acts.append(act2)
        current_object = CurrentObjectInfo(obj.fulltitle, obj.Meta.icon, subtitle=Markup(_l('Created by <a href="%(link)s">%(created_by)s</a> %(date)s', link=url_for('users.user_show', user_id=obj.created_by.id), created_by=obj.created_by.title, date=str(moment(obj.created_at).fromNow()))), actions=acts)
    elif action == 'new':
        title = _l("Add new task")
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus", subtitle=obj.project.fulltitle)
    elif action == 'edit':
        title = _l("Edit task #%(task_id)s", task_id=obj.id)
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen", subtitle=obj.project.fulltitle)
    return {'title': title, 'current_object': current_object}

register_environment(EnvironmentObjectAttrs('ProjectTask', sidebar, environment), 'Project')