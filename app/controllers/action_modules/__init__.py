from flask import Blueprint, url_for
from app.helpers.projects_helpers import EnvironmentObjectAttrs, register_environment, check_if_same_type
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo, SidebarElement, SidebarElementSublink
from app.action_modules import AutomationModules
from flask_babel import lazy_gettext as _l
from flask_login import current_user, login_required
from app.helpers.roles import project_role_can_make_action

bp = Blueprint('action_modules', __name__, url_prefix='/action_modules')


@bp.before_request
@login_required
def check_login_required():
    pass


import app.controllers.action_modules.routes


def sidebar(current_object, act: str, **kwargs) -> SidebarElement:
    con = current_object.__class__.__name__
    if con == 'Project':
        proj = current_object
    elif "proj" in kwargs:
        proj = kwargs["proj"]
    else:
        proj = current_object.project
    sels = []
    if project_role_can_make_action(current_user, AutomationModules(), 'index', project=proj):
        sel_all_modules = SidebarElementSublink(_l("Automation modules"), url_for('action_modules.action_modules_index', project_id=proj.id), con=='AutomationModules')
        sels.append(sel_all_modules)
    if len(sels) == 0:
        return None
    return SidebarElement(_l("Automation modules"), url_for('action_modules.action_modules_index', project_id=proj.id), AutomationModules.Meta.icon, con=='AutomationModules' and act=='index', sels)


@check_if_same_type(AutomationModules)
def environment(obj, action, **kwargs):
    if action == 'index':
        title = _l("All automation modules")
        current_object = CurrentObjectInfo(_l("Process automation modules"), AutomationModules.Meta.icon, subtitle=kwargs['proj'].fulltitle)
    elif action == 'run':
        title = kwargs["action_module"].title
        current_object = CurrentObjectInfo(kwargs["action_module"].title, AutomationModules.Meta.icon, subtitle=kwargs["action_module"].description)
    return {'title': title, 'current_object': current_object}


register_environment(EnvironmentObjectAttrs("AutomationModules", sidebar, environment), 'Credential')