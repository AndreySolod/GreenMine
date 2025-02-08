from flask import Blueprint, url_for
from app.models import FileDirectory
from app.helpers.projects_helpers import EnvironmentObjectAttrs, register_environment, check_if_same_type
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo, SidebarElement, SidebarElementSublink
from flask_babel import lazy_gettext as _l
from flask_login import current_user
from app.helpers.roles import project_role_can_make_action


bp = Blueprint('webfiles', __name__, url_prefix='/webfiles')


import app.controllers.webfiles.routes
import app.controllers.webfiles.websockets


def sidebar(current_object, act: str, **kwargs) -> SidebarElement:
    con = current_object.__class__.__name__
    if con == 'Project':
        proj = current_object
    elif "proj" in kwargs:
        proj = kwargs["proj"]
    else:
        proj = current_object.project
    sels = []
    if project_role_can_make_action(current_user, FileDirectory(), 'index', project=proj):
        sel_webfiles = SidebarElementSublink(_l("Files"), url_for('webfiles.filedirectory_index', project_id=proj.id), con=='FileDirectory')
        sels.append(sel_webfiles)
    if len(sels) == 0:
        return None
    return SidebarElement(_l("Files"), url_for('webfiles.filedirectory_index', project_id=proj.id), "fa-solid fa-folder-tree", con=='FileDirectory', [])


@check_if_same_type(FileDirectory)
def environment(obj, action, **kwargs):
    if action == 'index':
        title = _l("All files")
        current_object = CurrentObjectInfo(_l("Files, related with project"), obj.Meta.icon_index, subtitle=obj.project.fulltitle)
    return {'title': title, 'current_object': current_object}

register_environment(EnvironmentObjectAttrs('FileDirectory', sidebar, environment), 'Note')