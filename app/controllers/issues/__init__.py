from app import db
from flask import Blueprint, url_for
from app.models import Issue, IssueStatus
from app.helpers.projects_helpers import EnvironmentObjectAttrs, register_environment, check_if_same_type
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo, SidebarElement, SidebarElementSublink
from markupsafe import Markup
from app.extensions.moment import moment
from flask_babel import lazy_gettext as _l
from flask_login import current_user
from app.helpers.roles import project_role_can_make_action


bp = Blueprint('issues', __name__, url_prefix='/issues')


import app.controllers.issues.routes
import app.controllers.issues.websockets


def sidebar(current_object, act: str, **kwargs) -> SidebarElement:
    con = current_object.__class__.__name__
    if con == 'Project':
        proj = current_object
    elif "proj" in kwargs:
        proj = kwargs["proj"]
    else:
        proj = current_object.project
    sels = []
    if project_role_can_make_action(current_user, Issue(), 'index', project=proj):
        sel_exist = SidebarElementSublink(_l("Existing issues"), url_for('issues.exist_issue_index', project_id=proj.id), con=="Issue" and act=="exist-index")
        sels.append(sel_exist)
        sel_positive = SidebarElementSublink(_l("Fixed issues"), url_for('issues.positive_issue_index', project_id=proj.id), con=="Issue" and act=="positive-index")
        sel1 = SidebarElementSublink(_l("All issues"), url_for('issues.issue_index', project_id=proj.id), con=='Issue' and act=='index')
        sels.append(sel_positive)
        sels.append(sel1)
    if project_role_can_make_action(current_user, Issue(), 'create', project=proj):
        sel2 = SidebarElementSublink(_l("Add new issue"), url_for('issues.issue_new', project_id=proj.id), con=='Issue' and act=='new')
        sels.append(sel2)
    if con == 'Issue' and act not in ['index', 'positive-index', 'exist-index', 'new']:
        if project_role_can_make_action(current_user, current_object, 'show'):
            sel3 = SidebarElementSublink(current_object.fulltitle, url_for('issues.issue_show', issue_id=current_object.id), act=='show')
            sels.append(sel3)
        if project_role_can_make_action(current_user, current_object, 'update'):
            sel4 = SidebarElementSublink(_l("Edit issue #%(issue_id)s", issue_id=current_object.id), url_for('issues.issue_edit', issue_id=current_object.id), act=='edit')
            sels.append(sel4)
    if len(sels) == 0:
        return None
    return SidebarElement(_l("Issues"), url_for('issues.issue_index', project_id=proj.id), Issue.Meta.icon_index, con=='Issue', sels)


@check_if_same_type(Issue)
def environment(obj, action, **kwargs):
    # id state of fixed problem
    fixed_id = db.session.execute(db.select(IssueStatus.id).where(IssueStatus.string_slug == 'fixed')).one()[0]
    acts = []
    if action == 'index':
        title = _l("All issues")
        if project_role_can_make_action(current_user, obj, 'create', project=obj.project):
            act1 = CurrentObjectAction(_l("Add new issue"), "fa-solid fa-square-plus", url_for('issues.issue_new', project_id=obj.project.id))
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("All issues"), obj.Meta.icon_index, subtitle=obj.project.fulltitle, actions=acts)
    elif action == 'positive-index':
        title = _l("Fixed issues")
        if project_role_can_make_action(current_user, obj, 'create', project=obj.project):
            act1 = CurrentObjectAction(_l("Add fixed issues"), "fa-solid fa-square-plus", url_for('issues.issue_new', project_id=obj.project.id, status_id=fixed_id))
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("Fixed issues"), obj.Meta.icon_index, subtitle=obj.project.fulltitle, actions=acts)
    elif action == 'exist-index':
        title = _l("Existing issues")
        if project_role_can_make_action(current_user, obj, 'create', project=obj.project):
            act1 = CurrentObjectAction(_l("Add new issue"), "fa-solid fa-square-plus", url_for('issues.issue_new', project_id=obj.project.id))
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("Existing issues"), obj.Meta.icon_index, subtitle=obj.project.fulltitle, actions=acts)
    elif action == 'show':
        title = _l("Issue #%(issue_id)s", issue_id=obj.id)
        if project_role_can_make_action(current_user, obj, 'update'):
            act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('issues.issue_edit', issue_id=obj.id))
            acts.append(act1)
        if project_role_can_make_action(current_user, obj, 'delete'):
            act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('issues.issue_delete', issue_id=obj.id), confirm=_l("Are you sure you want to delete this issue?"), btn_class='btn-danger', method='DELETE')
            acts.append(act2)
        current_object = CurrentObjectInfo(obj.fulltitle, obj.Meta.icon, subtitle=Markup(_l('Created by <a href="%(link)s">%(created_by)s</a> %(date)s', link=url_for('users.user_show', user_id=obj.created_by.id), created_by=obj.created_by.title, date=str(moment(obj.created_at).fromNow()))), actions=acts)
    elif action == 'new':
        title = _l("Add new issue")
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus", subtitle=obj.project.fulltitle)
    elif action == 'edit':
        title = _l("Edit issue #%(issue_id)s", issue_id=obj.id)
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen", subtitle=obj.project.fulltitle)
    return {'title': title, 'current_object': current_object}

register_environment(EnvironmentObjectAttrs('Issue', sidebar, environment), 'Service')