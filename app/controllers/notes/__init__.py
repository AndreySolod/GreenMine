from flask import Blueprint, url_for
from app.models import Note
from app.helpers.projects_helpers import EnvironmentObjectAttrs, register_environment, check_if_same_type
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo, SidebarElement, SidebarElementSublink
from flask_babel import lazy_gettext as _l
from flask_login import current_user, login_required
from app.helpers.roles import project_role_can_make_action


bp = Blueprint('notes', __name__, url_prefix='/notes')

@bp.before_request
@login_required
def check_login_required():
    pass


import app.controllers.notes.routes
import app.controllers.notes.websockets


def sidebar(current_object, act: str, **kwargs) -> SidebarElement:
    con = current_object.__class__.__name__
    if con == 'Project':
        proj = current_object
    elif "proj" in kwargs:
        proj = kwargs["proj"]
    else:
        proj = current_object.project
    sels = []
    if project_role_can_make_action(current_user, Note(), 'index', project=proj):
        sel_notes = SidebarElementSublink(_l("All notes"), url_for('notes.note_index', project_id=proj.id), con=='Note')
        sels.append(sel_notes)
    if len(sels) == 0:
        return None
    return SidebarElement(_l("Notes"), url_for('notes.note_index', project_id=proj.id), Note.Meta.icon_index, con=='Note', [])


@check_if_same_type(Note)
def environment(obj, action, **kwargs):
    acts = []
    if action == 'index':
        title = _l("All notes")
        if project_role_can_make_action(current_user, obj, 'create'):
            act1 = CurrentObjectAction(_l("Add new note"), "fa-solid fa-square-plus", 'modalAddNewNote', action_type='button_modal')
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("All notes"), Note.Meta.icon_index, subtitle=obj.project.fulltitle, actions=acts)
    return {'title': title, 'current_object': current_object}


register_environment(EnvironmentObjectAttrs('Note', sidebar, environment), 'Credential')