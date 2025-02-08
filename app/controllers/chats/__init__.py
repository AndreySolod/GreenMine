from flask import Blueprint, url_for
from app.helpers.general_helpers import SidebarElement, CurrentObjectInfo
from app.helpers.projects_helpers import check_if_same_type, register_environment, EnvironmentObjectAttrs
import app.models as models
from flask_babel import lazy_gettext as _l
from flask_login import current_user
from app.helpers.roles import project_role_can_make_action

bp = Blueprint('chats', __name__, url_prefix="/chats")


import app.controllers.chats.routes
import app.controllers.chats.websockets


def sidebar(current_object, act: str, **kwargs):
    con = current_object.__class__.__name__
    if con == 'Project':
        proj = current_object
    elif "proj" in kwargs:
        proj = kwargs["proj"]
    else:
        proj = current_object.project
    if not project_role_can_make_action(current_user, models.ChatMessage(), 'index', project=proj):
        return None
    return SidebarElement(models.ChatMessage.Meta.verbose_name_plural, url_for('chats.index', project_id=proj.id), models.ChatMessage.Meta.icon, con=='ChatMessage', [])


@check_if_same_type(models.ChatMessage)
def environment(obj, action, **kwargs):
    if action == 'index':
        title = _l("Project chat")
        current_object = CurrentObjectInfo(models.ChatMessage.Meta.verbose_name_plural, models.ChatMessage.Meta.icon, subtitle=obj.project.fulltitle)
    return {'title': title, 'current_object': current_object}


register_environment(EnvironmentObjectAttrs('ChatMessage', sidebar, environment), 'Note')