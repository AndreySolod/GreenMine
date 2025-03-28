from flask import Blueprint, url_for
from app.helpers.projects_helpers import EnvironmentObjectAttrs, register_environment, check_if_same_type
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo, SidebarElement, SidebarElementSublink
from app.action_modules import AutomationModules
from flask_babel import lazy_gettext as _l
from flask_login import current_user, login_required
from app.helpers.roles import project_role_can_make_action
import app.models as models

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
        sel_all_modules = SidebarElementSublink(_l("Automation modules list"), url_for('action_modules.action_modules_index', project_id=proj.id), con=='AutomationModules' and act == 'index')
        sels.append(sel_all_modules)
    if project_role_can_make_action(current_user, AutomationModules(), 'default_credentials', project=proj):
        sel_default_creds = SidebarElementSublink(models.DefaultCredential.Meta.verbose_name_plural, url_for('action_modules.default_credentials_index', project_id=proj.id), con=='DefaultCredential')
        sels.append(sel_default_creds)
    if len(sels) == 0:
        return None
    return SidebarElement(AutomationModules.Meta.verbose_name_plural, url_for('action_modules.action_modules_index', project_id=proj.id), AutomationModules.Meta.icon, con in ['AutomationModules', 'DefaultCredential'], sels)


def environment(obj, action, **kwargs):
    if isinstance(obj, AutomationModules):
        if action == 'index':
            title = _l("All automation modules")
            current_object = CurrentObjectInfo(_l("Process automation modules"), AutomationModules.Meta.icon, subtitle=kwargs['proj'].fulltitle)
        elif action == 'run':
            title = kwargs["action_module"].title
            current_object = CurrentObjectInfo(kwargs["action_module"].title, AutomationModules.Meta.icon, subtitle=kwargs["action_module"].description)
        return {'title': title, 'current_object': current_object}
    elif isinstance(obj, models.DefaultCredential):
        if action == 'index':
            title = models.DefaultCredential.Meta.verbose_name_plural
            current_object = CurrentObjectInfo(_l("Factory credentials"), models.DefaultCredential.Meta.icon, subtitle=_l("A list of credentials installed at the factory by various manufacturers"))
        return {'title': title, 'current_object': current_object}
    else:
        return {}


register_environment(EnvironmentObjectAttrs("AutomationModules", sidebar, environment), 'Credential')