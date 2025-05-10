from flask import Blueprint, url_for
from app.models import Network, Host, Service
from app.helpers.projects_helpers import EnvironmentObjectAttrs, register_environment, check_if_same_type
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo, SidebarElement, SidebarElementSublink
from markupsafe import Markup
from app.extensions.moment import moment
from flask_babel import lazy_gettext as _l, pgettext
from flask_login import current_user, login_required
from app.helpers.roles import project_role_can_make_action
from typing import Optional


bp = Blueprint('networks', __name__, url_prefix='/')


@bp.before_request
@login_required
def check_login_required():
    pass


import app.controllers.networks.routes
import app.controllers.networks.ajax_routes
import app.controllers.networks.websockets


def sidebar_network(current_object, act: str, **kwargs) -> Optional[SidebarElement]:
    con = current_object.__class__.__name__
    if con == 'Project':
        proj = current_object
    elif "proj" in kwargs:
        proj = kwargs["proj"]
    else:
        proj = current_object.project
    sels = []
    if project_role_can_make_action(current_user, Network(), 'index', project=proj):
        sel31 = SidebarElementSublink(_l("All networks"), url_for('networks.network_index', project_id=proj.id), con=="Network" and act=='index')
        sels.append(sel31)
    if project_role_can_make_action(current_user, Network(), 'create', project=proj):
        sel32 = SidebarElementSublink(_l("Add new network"), url_for('networks.network_new', project_id=proj.id), con=="Network" and act=='new')
        sels.append(sel32)
    if len(sels) == 0:
        return None
    return SidebarElement(_l("Networks"), url_for('networks.network_index', project_id=proj.id), Network.Meta.icon_index, con=='Network', sels)


def sidebar_host(current_object, act: str, **kwargs) -> Optional[SidebarElement]:
    con = current_object.__class__.__name__
    if con == 'Project':
        proj = current_object
    elif "proj" in kwargs:
        proj = kwargs["proj"]
    else:
        proj = current_object.project
    sels = []
    if project_role_can_make_action(current_user, Host(), 'index', project=proj):
        sel41 = SidebarElementSublink(_l("All hosts"), url_for('networks.host_index', project_id=proj.id), con=='Host' and act=='index')
        sel45 = SidebarElementSublink(_l("Excluded hosts"), url_for('networks.hosts_excluded_index', project_id=proj.id), con=='Host' and act=='excluded-index')
        sels.append(sel41)
        sels.append(sel45)
    if project_role_can_make_action(current_user, Host(), 'create', project=proj):
        sel42 = SidebarElementSublink(_l("Add new host"), url_for('networks.host_new', project_id=proj.id), con=='Host' and act=='new')
        sels.append(sel42)
        sel46 = SidebarElementSublink(_l("Multiple import"), url_for('networks.multiple_import_hosts', project_id=proj.id), con=='Host' and act=='multiple_import')
        sels.append(sel46)
    if len(sels) == 0:
        return None
    return SidebarElement(_l("Hosts"), url_for('networks.host_index', project_id=proj.id), Host.Meta.icon_index, con=='Host', sels)


def sidebar_service(current_object, act: str, **kwargs) -> Optional[SidebarElement]:
    con = current_object.__class__.__name__
    if con == 'Project':
        proj = current_object
    elif "proj" in kwargs:
        proj = kwargs["proj"]
    else:
        proj = current_object.project
    sels = []
    if project_role_can_make_action(current_user, Service(), 'index', project=proj):
        sel51 = SidebarElementSublink(_l("All servicves"), url_for('networks.service_index', project_id=proj.id), con=='Service' and act=='index')
        sels.append(sel51)
        sel55 = SidebarElementSublink(_l("Services by port"), url_for("networks.services_index_by_port", project_id=proj.id), con=='Service' and act=='index_by_port')
        sels.append(sel55)
    if project_role_can_make_action(current_user, Service(), 'create', project=proj):
        sel52 = SidebarElementSublink(_l("Add new service"), url_for('networks.service_new', project_id=proj.id), con=='Service' and act=='new')
        sels.append(sel52)
    if project_role_can_make_action(current_user, Service(), 'update', project=proj):
        sel53 = SidebarElementSublink(_l("Inventory of services"), url_for('networks.services_inventory', project_id=proj.id), con=='Service' and act=='inventory')
        sels.append(sel53)
    if len(sels) == 0:
        return None
    return SidebarElement(_l("Services"), url_for('networks.service_index', project_id=proj.id), Service.Meta.icon_index, con=='Service', sels)


@check_if_same_type(Network)
def environment_network(obj, action, **kwargs):
    if action == 'index':
        title = _l("All networks")
        acts = []
        if project_role_can_make_action(current_user, obj, 'create', project=obj.project):
            act1 = CurrentObjectAction(_l("Add new network"), "fa-solid fa-square-plus", url_for('networks.network_new', project_id=obj.project.id))
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("All networks"), obj.Meta.icon_index, subtitle=obj.project.fulltitle, actions=acts)
    elif action == 'show':
        title = _l("Network «%(ip_addr)s»", ip_addr=str(obj.ip_address))
        acts = []
        if project_role_can_make_action(current_user, obj, 'update'):
            act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('networks.network_edit', network_id=obj.id))
            acts.append(act1)
        if project_role_can_make_action(current_user, obj, 'delete'):
            act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('networks.network_delete', network_id=obj.id), confirm=_l("Are you sure you want to delete this network?"), btn_class='btn-danger', method='DELETE')
            acts.append(act2)
        current_object = CurrentObjectInfo(obj.fulltitle, obj.Meta.icon, subtitle=Markup(_l('Created by <a href="%(link)s">%(created_by)s</a> %(date)s', link=url_for('users.user_show', user_id=obj.created_by.id), created_by=obj.created_by.title, date=str(moment(obj.created_at).fromNow()))), actions=acts)
    elif action == 'new':
        title = _l("Add new network")
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus", subtitle=obj.project.fulltitle)
    elif action == 'edit':
        title = _l("Edit network «%(ip_addr)s»", ip_addr=str(obj.ip_address))
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen", subtitle=obj.project.fulltitle)
    return {'title': title, 'current_object': current_object, 'archived': obj.project.archived}


@check_if_same_type(Host)
def environment_host(obj, action, **kwargs):
    if 'proj' in kwargs:
        proj = kwargs["proj"]
    else:
        proj = obj.project
    if action == 'index':
        title = _l("All hosts")
        acts = []
        if project_role_can_make_action(current_user, obj, 'create', project=proj):
            act1 = CurrentObjectAction(_l("Add new host"), "fa-solid fa-square-plus", url_for('networks.host_new', project_id=proj.id))
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("All hosts"), obj.Meta.icon_index, subtitle=proj.fulltitle, actions=acts)
    elif action == 'excluded-index':
        title = _l("Excluded hosts")
        acts = []
        if project_role_can_make_action(current_user, obj, 'create', project=proj):
            act1 = CurrentObjectAction(_l("Add new excluded host"), "fa-solid fa-square-plus", url_for('networks.host_new', project_id=proj.id, excluded=True))
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("Excluded hosts"), "fa-solid fa-crosshairs", subtitle=proj.fulltitle, actions=acts)
    elif action == 'show':
        title = _l("Host «%(ip_addr)s»", ip_addr=str(obj.ip_address))
        acts = []
        if project_role_can_make_action(current_user, obj, 'update'):
            act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('networks.host_edit', host_id=obj.id))
            acts.append(act1)
            if obj.excluded:
                act3 = CurrentObjectAction(_l("Include to research"), "icon-target", url_for("networks.add_host_to_research", host_id=obj.id), btn_class="btn-warning", method='POST')
            else:
                act3 = CurrentObjectAction(_l("Exclude from research"), "icon-no-target", url_for('networks.exclude_host_from_research', host_id=obj.id), btn_class="btn-warning", method='POST')
            acts.append(act3)
        if project_role_can_make_action(current_user, obj, 'delete'):
            act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('networks.host_delete', host_id=obj.id), confirm=_l("Are you sure you want to delete this host?"), btn_class='btn-danger', method='DELETE')
            acts.append(act2)
        if obj.created_by_id is None:
            link = "#"
            created_by_title = pgettext('man', "Anonymous")
        else:
            link = url_for('users.user_show', user_id=obj.created_by.id)
            created_by_title = obj.created_by.title
        subtitle = Markup(_l('Created by <a href="%(link)s">%(created_by)s</a> %(date)s', link=link, created_by=created_by_title, date=str(moment(obj.created_at).fromNow())))
        current_object = CurrentObjectInfo(obj.fulltitle, obj.Meta.icon, subtitle=subtitle, actions=acts)
    elif action == 'new':
        title = _l("Add new host")
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus", subtitle=proj.fulltitle)
    elif action == 'edit':
        title = _l("Edit host «%(ip_addr)s»", ip_addr=str(obj.ip_address))
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen", subtitle=proj.fulltitle)
    elif action == 'multiple_import':
        title = _l("Multiple import hosts")
        current_object = CurrentObjectInfo(title, "fa-solid fa-cash-register", subtitle=proj.fulltitle)
    return {'title': title, 'current_object': current_object, 'archived': proj.archived}


@check_if_same_type(Service)
def environment_service(obj, action, **kwargs):
    if 'proj' in kwargs:
        proj = kwargs['proj']
    else:
        proj = obj.project
    if action == 'index':
        title = _l("All services")
        acts = []
        if project_role_can_make_action(current_user, obj, 'create', project=proj):
            act1 = CurrentObjectAction(_l("Add new service"), "fa-solid fa-square-plus", url_for('networks.service_new', project_id=proj.id))
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("All services"), obj.Meta.icon_index, subtitle=proj.fulltitle, actions=[act1])
    elif action == 'index_by_port':
        title = _l("Services, splitted by ports")
        acts = []
        if project_role_can_make_action(current_user, obj, 'create', project=proj):
            act1 = CurrentObjectAction(_l("Add new service"), "fa-solid fa-square-plus", url_for('networks.service_new', project_id=proj.id))
            acts.append(act1)
        current_object = CurrentObjectInfo(_l("Services, splitted by ports"), obj.Meta.icon_index, subtitle=proj.fulltitle, actions=[act1])

    elif action == 'show':
        title = _l("Service «%(ip_addr)s:%(port)s»", ip_addr=str(obj.host.ip_address), port=str(obj.port))
        acts = []
        if project_role_can_make_action(current_user, obj, 'update'):
            act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-square-pen", url_for('networks.service_edit', service_id=obj.id))
            acts.append(act1)
        if project_role_can_make_action(current_user, obj, 'delete'):
            act2 = CurrentObjectAction(_l("Delete"), "fa-solid fa-trash", url_for('networks.service_delete', service_id=obj.id), confirm=_l("Are you sure you want to delete this service?"), btn_class='btn-danger', method='DELETE')
            acts.append(act2)
        current_object = CurrentObjectInfo(obj.fulltitle, obj.Meta.icon, subtitle=Markup(_l('Created by <a href="%(link)s">%(created_by)s</a> %(date)s', link=url_for('users.user_show', user_id=obj.created_by.id), created_by=obj.created_by.title, date=str(moment(obj.created_at).fromNow()))), actions=acts)
    elif action == 'new':
        title = _l("Add new service")
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-plus", subtitle=proj.fulltitle)
    elif action == 'edit':
        title = _l("Edit service «%(ip_addr)s:%(port)s»", ip_addr=str(obj.host.ip_address), port=str(obj.port))
        current_object = CurrentObjectInfo(title, "fa-solid fa-square-pen", subtitle=proj.fulltitle)
    elif action == 'inventory':
        title = _l("Inventory of services")
        current_object = CurrentObjectInfo(_l("Inventory of services on project #%(project_id)s", project_id=proj.id), "fa-solid fa-boxes-stacked", subtitle=_l("A page that allows you to quickly fill in basic data for hosts/services"))
    return {'title': title, 'current_object': current_object, 'archived': proj.archived}


register_environment(EnvironmentObjectAttrs('Network', sidebar_network, environment_network), 'ProjectTask')
register_environment(EnvironmentObjectAttrs('Host', sidebar_host, environment_host), 'Network')
register_environment(EnvironmentObjectAttrs('Service', sidebar_service, environment_service), 'Host')