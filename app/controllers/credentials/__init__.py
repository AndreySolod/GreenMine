from flask import Blueprint, url_for
from app import sanitizer
from app.models import Credential
from app.helpers.projects_helpers import EnvironmentObjectAttrs, register_environment, check_if_same_type
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo, SidebarElement, SidebarElementSublink
from jinja2.filters import Markup
from app.extensions.moment import moment
from flask_babel import lazy_gettext as _l
from flask_login import current_user
from app.helpers.roles import project_role_can_make_action


bp = Blueprint('credentials', __name__, url_prefix='/credentials')


import app.controllers.credentials.routes
import app.controllers.credentials.websockets


def sidebar(current_object, act: str, **kwargs) -> SidebarElement:
    con = current_object.__class__.__name__
    if con == 'Project':
        proj = current_object
    elif "proj" in kwargs:
        proj = kwargs["proj"]
    else:
        proj = current_object.project
    sels = []
    if project_role_can_make_action(current_user, Credential(), 'index', project=proj):
        sel_all_creds = SidebarElementSublink(_l("User credentials"), url_for('credentials.credential_index', project_id=proj.id), con=='Credential' and act=='index')
        sels.append(sel_all_creds)
    if project_role_can_make_action(current_user, Credential(), 'pentest_index', project=proj):
        sel_pentest_creds = SidebarElementSublink(_l("Credentials of the researchers"), url_for('credentials.pentest_credential_index', project_id=proj.id), con=='Credential' and act=='index_pentest')
        sels.append(sel_pentest_creds)
    if project_role_can_make_action(current_user, Credential(), 'create', project=proj):
        sel_add_creds = SidebarElementSublink(_l("Add new credentials"), url_for('credentials.credential_new', project_id=proj.id), con=='Credential' and act=='new')
        sel_add_multiple = SidebarElementSublink(_l("Add multiple credentials"), url_for('credentials.multiple_import_credentials', project_id=proj.id), con=='Credential' and act=='multiple_import')
        sels.append(sel_add_creds)
        sels.append(sel_add_multiple)
    if len(sels) == 0:
        return None
    return SidebarElement(_l("Credentials"), url_for('credentials.credential_index', project_id=proj.id), Credential.Meta.icon_index, con=='Credential',
                              sels)


@check_if_same_type(Credential)
def environment(obj, action, **kwargs):
    acts = []
    if action == 'index':
        title = _l("All credentials")
        if project_role_can_make_action(current_user, obj, 'create'):
            act1 = CurrentObjectAction(_l("Add new credentials"), "fa-solid fa-square-plus", url_for('credentials.credential_new', project_id=obj.project.id))
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("Credentials"), obj.Meta.icon_index, subtitle=_l("Credentials that were found within the framework of this project"), actions=acts)
    elif action == 'pentest-index':
        title = _l("Researcher credentials")
        if project_role_can_make_action(current_user, obj, 'create'):
            act1 = CurrentObjectAction(_l("Add new credentials"), "fa-solid fa-square-plus", url_for('credentials.credential_new', project_id=obj.project.id, is_pentest_credentials=True))
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("Researcher credentials"), obj.Meta.icon_index, subtitle=_l("The credentials that were added by the researchers within the framework of this project"), actions=acts)
    elif action == 'show':
        title = _l("«%(login)s» login credentials", login=obj.login)
        if project_role_can_make_action(current_user, obj, 'update'):
            act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('credentials.credential_edit', credential_id=obj.id))
            acts.append(act1)
        if project_role_can_make_action(current_user, obj, 'delete'):
            act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('credentials.credential_delete', credential_id=obj.id), confirm=_l("Are you sure you want to delete these credentials?"), btn_class='btn-danger', method='DELETE')
            acts.append(act2)
        current_object = CurrentObjectInfo(obj.fulltitle, obj.Meta.icon, subtitle=Markup(_l('Created by <a href="%(link)s">%(created_by)s</a> %(date)s', link=url_for('users.user_show', user_id=obj.created_by.id), created_by=sanitizer.pure_text(obj.created_by.title), date=str(moment(obj.created_at).fromNow()))), actions=acts)
    elif action == 'new':
        title = _l("Add new credentials")
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus", subtitle=obj.project.fulltitle)
    elif action == 'multiple_import':
        title = _l("Multiple import credentials")
        current_object = CurrentObjectInfo(title, "fa-solid fa-upload", subtitle=_l("Multiple add new credentials or update if they exist in database"))
    elif action == 'edit':
        title = _l("Edit credentials")
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen", subtitle=obj.project.fulltitle)
    return {'title': title, 'current_object': current_object}

register_environment(EnvironmentObjectAttrs('Credential', sidebar, environment), 'Issue')