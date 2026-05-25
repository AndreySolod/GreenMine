from flask import Blueprint, url_for
from app.models import Domain
from app.helpers.projects_helpers import EnvironmentObjectAttrs, register_environment, check_if_same_type
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo, SidebarElement, SidebarElementSublink
from markupsafe import Markup
from app.extensions.moment import moment
from flask_babel import lazy_gettext as _l, pgettext
from flask_login import current_user, login_required
from app.helpers.roles import project_role_can_make_action
from typing import Optional
from app import sanitizer


bp = Blueprint('domains', __name__, url_prefix='/')


@bp.before_request
@login_required
def check_login_required():
    pass


import app.controllers.domains.routes
import app.controllers.domains.ajax_routes


def sidebar(current_object, act: str, **kwargs) -> Optional[SidebarElement]:
    con = current_object.__class__.__name__
    if con == 'Project':
        proj = current_object
    elif "proj" in kwargs:
        proj = kwargs["proj"]
    else:
        proj = current_object.project
    sels = []
    if project_role_can_make_action(current_user, Domain(), 'index', project=proj):
        sel31 = SidebarElementSublink(_l("All domains"), url_for('domains.domain_index', project_id=proj.id), con=='Domain' and act=='index')
        sels.append(sel31)
    if project_role_can_make_action(current_user, Domain(), 'create', project=proj):
        sel32 = SidebarElementSublink(_l("Add new domain"), url_for('domains.domain_new', project_id=proj.id), con=='Domain' and act=='create')
        sels.append(sel32)
    if len(sels) == 0:
        return None
    return SidebarElement(_l("Domains"), url_for('domains.domain_index', project_id=proj.id), Domain.Meta.icon, con=='Domain', sels)


@check_if_same_type(Domain)
def environment(obj, action, **kwargs) -> dict:
    if action == 'index':
        title = _l("All domains")
        acts = []
        if project_role_can_make_action(current_user, Domain(), 'create', project=obj.project):
            act1 = CurrentObjectAction(_l("Add new domain"), "fa-solid fa-square-plus", url_for('domains.domain_new', project_id=obj.project.id))
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("All domains"), obj.Meta.icon, subtitle=obj.project.fulltitle, actions=acts)
    elif action == 'show':
        title = _l("Domain #%(domain_id)s", domain_id=obj.id)
        acts = []
        if project_role_can_make_action(current_user, obj, 'update'):
            act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('domains.domain_edit', domain_id=obj.id))
            acts.append(act1)
        if project_role_can_make_action(current_user, obj, 'delete'):
            act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('domains.domain_delete', domain_id=obj.id), confirm=_l("Are you sure you want to delete this domain?"), btn_class='btn-danger', method='DELETE')
            acts.append(act2)
        if obj.created_by is not None:
            co_subtitle = sanitizer.markup(_l('Created by <a href="%(link)s">%(created_by)s</a> %(date)s', link=url_for('users.user_show', user_id=obj.created_by.id), created_by=sanitizer.pure_text(obj.created_by.title), date=str(moment(obj.created_at).fromNow())))
        else:
            co_subtitle = sanitizer.markup(_l('Created by <a href="%(link)s">%(created_by)s</a> %(date)s', link="", created_by=_l("Removed user"), date=str(moment(obj.created_at).fromNow())))
        current_object = CurrentObjectInfo(obj.title, obj.Meta.icon, subtitle=co_subtitle, actions=acts)
    elif action == 'new':
        title = _l("Add new domain")
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus", subtitle=obj.project.fulltitle)
    elif action == 'edit':
        title = _l("Edit domain #%(domain_id)s", domain_id=obj.id)
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen", subtitle=obj.project.fulltitle)
    return {'title': title, 'current_object': current_object, 'archived': obj.project.archived}

register_environment(EnvironmentObjectAttrs('Domain', sidebar, environment), 'ProjectTask')