from app import socketio, db, sanitizer, logger, automation_modules
from app.helpers.general_helpers import authenticated_only
from app.helpers.projects_helpers import get_current_room
from flask_socketio import emit, join_room, send
from flask import url_for
from app.helpers.roles import project_role_can_make_action
from flask_login import current_user
import app.models as models
import sqlalchemy as sa
import sqlalchemy.exc as exc
from selenium.common.exceptions import WebDriverException


@socketio.on("join_room", namespace="/service")
@authenticated_only
def join_current_service_room(data):
    try:
        service = db.session.scalars(sa.select(models.Service).where(models.Service.id == int(data))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join incorrect service room {data}")
        return None
    if not project_role_can_make_action(current_user, service, 'show'):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join service room #{data}, in which he has no rights to")
        return None
    room = data
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' join service room #{data}")
    join_room(room, namespace="/service")


@socketio.on('edit related issues', namespace='/service')
@authenticated_only
def relate_issue_to_service(data):
    r = get_current_room()
    if r is None:
        return False
    service_id, current_room_name = r
    try:
        service = db.session.scalars(sa.select(models.Service).where(models.Service.id == int(service_id))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        return None
    if not project_role_can_make_action(current_user, service, 'update'):
        return None
    try:
        now_issues = db.session.scalars(sa.select(models.Issue).where(sa.and_(models.Issue.id.in_([int(i) for i in data['related_issues']]),
                                                                          models.Issue.project_id==service.host.from_network.project_id))).all()
        service.issues = now_issues
        db.session.commit()
    except(ValueError, TypeError, KeyError):
        return None
    new_issues = [{'id': i.id, 'title': i.title, 'description': sanitizer.pure_text(i.description), 'status': i.status.title} for i in service.issues]
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit related issues on service #{service.id}")
    emit('change related issues', {'rows': new_issues},
         namespace='/service', to=current_room_name)


@socketio.on('edit related credentials', namespace='/service')
@authenticated_only
def relate_issue_to_service(data):
    r = get_current_room()
    if r is None:
        return False
    service_id, current_room_name = r
    try:
        service = db.session.scalars(sa.select(models.Service).where(models.Service.id == int(service_id))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        return None
    if not project_role_can_make_action(current_user, service, 'update'):
        return None
    try:
        now_credentials = db.session.scalars(sa.select(models.Credential).where(sa.and_(models.Credential.id.in_([int(i) for i in data['related_credentials']]),
                                                                          models.Credential.project_id==service.host.from_network.project_id))).all()
        updated_credentials = set(service.credentials)
        updated_credentials = updated_credentials.union(set(now_credentials))
        service.credentials = now_credentials
        db.session.commit()
    except(ValueError, TypeError, KeyError):
        return None
    new_credentials = []
    for i in service.credentials:
        nr = {'id': i.id, 'login': i.login, 'password': i.password, 'password_hash': i.password_hash}
        nr['hash_type'] = '' if i.hash_type is None else i.hash_type.title
        new_credentials.append(nr)
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit related credentials on service #{service.id}")
    emit('change related credentials', {'rows': new_credentials},
         namespace='/service', to=current_room_name)
    for credential in updated_credentials:
        new_services = []
        for i in credential.services:
            ns = {'id': i.id, 'title': i.title, 'ip_address': str(i.host.ip_address), 'port': i.port, 'technical': i.technical}
            ns['transport_level_protocol'] = '' if i.transport_level_protocol is None else i.transport_level_protocol.title
            ns['access_protocol'] = '' if i.access_protocol is None else i.access_protocol.title
            new_services.append(ns)
        emit('change related services', {'rows': new_services},
            namespace='/credential', to=str(credential.id))


@socketio.on('edit related tasks', namespace='/service')
@authenticated_only
def relate_issue_to_service(data):
    r = get_current_room()
    if r is None:
        return False
    service_id, current_room_name = r
    try:
        service = db.session.scalars(sa.select(models.Service).where(models.Service.id == int(service_id))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        return None
    if not project_role_can_make_action(current_user, service, 'update'):
        return None
    try:
        now_tasks = db.session.scalars(sa.select(models.ProjectTask).where(sa.and_(models.ProjectTask.id.in_([int(i) for i in data['related_tasks']]),
                                                                          models.ProjectTask.project_id==service.host.from_network.project_id))).all()
        update_tasks = set(service.tasks)
        update_tasks = update_tasks.union(set(now_tasks))
        service.tasks = now_tasks
        db.session.commit()
    except(ValueError, TypeError, KeyError):
        return None
    new_tasks = []
    for i in service.tasks:
        nr = {'id': i.id, 'title': i.title, 'state': i.state.title, 'readiness': i.readiness}
        nr['tracker'] = '' if i.tracker is None else i.tracker.title
        nr['priority'] = '' if i.priority is None else i.priority.title
        nr['assigned_to'] = '' if i.assigned_to is None else i.assigned_to.title
        new_tasks.append(nr)
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit related tasks on service #{service.id}")
    emit('change related tasks', {'rows': new_tasks},
         namespace='/service', to=current_room_name)
    for task in update_tasks:
        new_services = []
        for i in task.services:
            ns = {'id': i.id, 'title': i.title, 'ip_address': str(i.host.ip_address), 'port': i.port, 'technical': i.technical}
            ns['transport_level_protocol'] = '' if i.transport_level_protocol is None else i.transport_level_protocol.title
            ns['access_protocol'] = '' if i.access_protocol is None else i.access_protocol.title
            new_services.append(ns)
        emit('change related services', {'rows': new_services},
            namespace='/task', to=str(task.id))


@socketio.on('take screenshot', namespace='/service')
@authenticated_only
def take_service_sreenshot(data):
    r = get_current_room()
    if r is None:
        return False
    service_id, current_room_name = r
    try:
        service = db.session.scalars(sa.select(models.Service).where(models.Service.id == int(service_id))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        return None
    if not project_role_can_make_action(current_user, service, 'update'):
        return None
    proto = data['proto']
    if proto is None:
        return None
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request take service screenshot on service #{service_id}")
    emit('take screenshot received', {'by_user': current_user.title, 'proto': proto}, namespace="/service", to=current_room_name)
    screenshoter = automation_modules.get("HardwareInventory")
    exploit_data = {"protocol": proto, "target": service}
    try:
        screenshoter.run_by_single_target(session=db.session, running_user=current_user, exploit_data=exploit_data)
        db.session.commit()
    except WebDriverException:
        pass
    db.session.refresh(service)
    attr = "screenshot_" + proto + "_id"
    file_id = getattr(service, attr)
    if file_id:
        screenshot_title = getattr(service, proto + 'title', '')
        emit("screenshot taked", {'address': url_for('files.download_file', file_id=file_id), 'proto': proto, 'screenshot_title': screenshot_title}, namespace="/service", to=current_room_name)
    else:
        emit("screenshot taked", {'address': None, 'proto': proto, 'screenshot_title': ''}, namespace="/service", to=current_room_name)


@socketio.on("join_room", namespace="/host")
@authenticated_only
def join_current_host_room(data):
    try:
        host = db.session.scalars(sa.select(models.Host).where(models.Host.id == int(data))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join incorrect host room {data}")
        return None
    if not project_role_can_make_action(current_user, host, 'show'):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join host room #{data}, in which he has no rights to")
        return None
    room = data
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' join host room #{data}")
    join_room(room, namespace="/host")


@socketio.on('add dns name', namespace='/host')
@authenticated_only
def add_dns_name_to_host(data):
    r = get_current_room()
    if r is None:
        return False
    host_id, current_room_name = r
    try:
        host = db.session.scalars(sa.select(models.Host).where(models.Host.id == int(host_id))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        return None
    if not project_role_can_make_action(current_user, host, 'update'):
        return None
    try:
        dns = models.HostDnsName(title = sanitizer.escape(data['title']), dns_type = sanitizer.escape(data['dns_type']), to_host=host)
        db.session.add(dns)
        db.session.commit()
    except(KeyError, exc.IntegrityError):
        return None
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' add new dns name to host #{host_id}")
    emit('edit dns names', {'dns': [{'title': i.title, 'dns_type': i.dns_type, 'id': i.id} for i in host.dnsnames]},
         namespace='/host', to=current_room_name)


@socketio.on('remove dns name', namespace='/host')
@authenticated_only
def remove_dns_name_from_host(data):
    r = get_current_room()
    if r is None:
        return False
    _, current_room_name = r
    try:
        dns = db.session.scalars(sa.select(models.HostDnsName).where(models.HostDnsName.id == int(data['dns_id']))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        return None
    if not project_role_can_make_action(current_user, dns.to_host, 'update'):
        return None
    host = dns.to_host
    db.session.delete(dns)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' remove dns name #{data['dns_id']} from host #{host.id}")
    emit('edit dns names', {'dns': [{'id': i.id, 'title': i.title, 'dns_type': i.dns_type} for i in host.dnsnames]},
         namespace='/host', to=current_room_name)


@socketio.on('edit interfaces', namespace='/host')
@authenticated_only
def add_new_host_interface(data):
    r = get_current_room()
    if r is None:
        return False
    current_room, _ = r
    try:
        host = db.session.scalars(sa.select(models.Host).where(models.Host.id == int(current_room))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        return None
    if not project_role_can_make_action(current_user, host, 'update'):
        return None
    new_interfaces = db.session.scalars(sa.select(models.Host).join(models.Host.from_network).where(models.Host.id.in_(list(map(int, data['interfaces']))), models.Network.project_id==host.from_network.project_id)).all()
    ifaces_ids = set(map(lambda x: x.id, host.interfaces))
    ifaces_ids.update(set(map(lambda x: x.id, new_interfaces)))
    ifaces_ids.add(host.id)
    host.flush_interfaces()
    for i in new_interfaces:
        host.assign_interface(i)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit related interfaces from host #{host.id}")
    for i in ifaces_ids:
        emit("interfaces changed", {"interfaces": [{"id": j.id, "title": j.title, "ip_address": str(j.ip_address), "description": sanitizer.pure_text(j.description),
                                                    "technical": sanitizer.pure_text(j.technical)} for j in host.interfaces]}, namespace="/host", to=str(i))



@socketio.on("join_room", namespace="/network")
@authenticated_only
def join_current_host_room(data):
    try:
        network = db.session.scalars(sa.select(models.Network).where(models.Network.id == int(data))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join incorrect network room {data}")
        return None
    if not project_role_can_make_action(current_user, network, 'show'):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join network room #{data}, in which he has no rights to")
        return None
    room = data
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' join network room #{data}")
    join_room(room, namespace="/network")


@socketio.on("reset network hosts", namespace="/network")
@authenticated_only
def reset_network_hosts(data):
    r = get_current_room()
    if r is None:
        return False
    current_room, current_room_name = r
    try:
        network = db.session.scalars(sa.select(models.Network).where(models.Network.id == int(current_room))).one()
        pagination_count = int(data['pagination_count'])
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        return None
    if not project_role_can_make_action(current_user, network, 'update'):
        return None
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request reset hosts to network")
    old_networks = []
    for h in db.session.scalars(sa.select(models.Host).join(models.Host.from_network).where(models.Network.project_id == network.project_id)):
        if h.ip_address in network.ip_address:
            old_networks.append(h.from_network.id)
            h.from_network = network
    db.session.commit()
    lst = []
    emit('hosts changed', {'update': True}, namespace='/network', to=current_room_name)
    for i in old_networks:
        emit('hosts changed', {'update': True}, namespace='/network', to=str(i))


@socketio.on('join_room', namespace="/hosts-excluded")
@authenticated_only
def join_hosts_room(data):
    try:
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == int(data))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join incorrect excluded hosts room {data}")
        return None
    if not project_role_can_make_action(current_user, models.Host(), 'index', project=project):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join excluded hosts room #{data}, in which he has no rights to")
        return None
    room = data
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' join excluded hosts room #{data}")
    join_room(room, namespace="/hosts-excluded")


@socketio.on('include to research', namespace='/hosts-excluded')
@authenticated_only
def include_host_to_research(data):
    r = get_current_room()
    if r is None:
        return False
    current_room, current_room_name = r
    try:
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == int(current_room))).one()
        host = db.session.scalars(sa.select(models.Host).where(models.Host.id == int(data['host_id']))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        return None
    if not project_role_can_make_action(current_user, host, 'update'):
        return None
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request add host to research")
    host.excluded = False
    db.session.add(host)
    db.session.commit()
    all_excluded_hosts = db.session.scalars(sa.select(models.Host).join(models.Host.from_network).where(sa.and_(models.Network.project_id == project.id, models.Host.excluded==True))).all()
    excluded_hosts = [{'id': i.id, 'title': i.title, 'from_network': str(i.from_network.fulltitle), 'ip_address': str(i.ip_address),
                      'description': sanitizer.pure_text(i.description)} for i in all_excluded_hosts]
    emit("excluded hosts changed", {'hosts': excluded_hosts}, namespace="/hosts-excluded", to=current_room_name)


@socketio.on('join_room', namespace="/hosts")
@authenticated_only
def join_hosts_room(data):
    try:
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == int(data))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join incorrect hosts room {data}")
        return None
    if not project_role_can_make_action(current_user, models.Host(), 'index', project=project):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join hosts room #{data}, in which he has no rights to")
        return None
    room = data
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' join hosts room #{data}")
    join_room(room, namespace="/hosts")


@socketio.on('delete host', namespace='/hosts')
@authenticated_only
def delete_host(data):
    r = get_current_room()
    if r is None:
        return False
    _, current_room_name = r
    try:
        host = db.session.scalars(sa.select(models.Host).where(models.Host.id == int(data['host_id']))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        return None
    if not project_role_can_make_action(current_user, host, 'update'):
        return None
    db.session.delete(host)
    db.session.commit()
    emit('host list updated', namespace="/hosts", to=current_room_name)


@socketio.on('exclude host', namespace='/hosts')
@authenticated_only
def exclude_host_from_research(data):
    r = get_current_room()
    if r is None:
        return False
    _, current_room_name = r
    try:
        host = db.session.scalars(sa.select(models.Host).where(models.Host.id == int(data['host_id']))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        return None
    if not project_role_can_make_action(current_user, host, 'update'):
        return None
    host.excluded = True
    db.session.add(host)
    db.session.commit()
    emit('host list updated', namespace='/hosts', to=current_room_name)


@socketio.on('join_room', namespace="/service-inventory")
@authenticated_only
def join_service_inventory_room(data):
    try:
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == int(data))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join incorrect service-inventory room {data}")
        return None
    if not project_role_can_make_action(current_user, models.Service(), 'update', project=project) or not project_role_can_make_action(current_user, models.Host(), 'update', project=project):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join service-inventory room #{data}, in which he has no rights to")
        return None
    room = data
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' join service-inventory room #{data}")
    join_room(room, namespace="/service-inventory")


@socketio.on('update data', namespace="/service-inventory")
@authenticated_only
def update_inventory_data(data):
    r = get_current_room()
    if r is None:
        return False
    project_id, current_room_name = r
    try:
        service = db.session.scalars(sa.select(models.Service).where(models.Service.id == data['service_id'])).one()
        device_type = db.session.scalars(sa.select(models.DeviceType).where(models.DeviceType.id == int(data['device_type_id']))).first()
        device_vendor = db.session.scalars(sa.select(models.DeviceVendor).where(models.DeviceVendor.id == int(data['device_vendor_id']))).first()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError, KeyError):
        return None
    if not project_role_can_make_action(current_user, service.host, 'update') or not project_role_can_make_action(current_user, service, 'update'):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to update service and host via service-inventory on project #{project_id}, in which he has no rights to")
    service.title = sanitizer.escape(data['service_title'])
    service.description = sanitizer.sanitize(data['service_description'])
    service.host.title = sanitizer.escape(data['host_title'])
    service.host.description = sanitizer.sanitize(data['host_description'])
    service.device_type = device_type
    service.device_vendor = device_vendor
    service.has_been_inventoried = True
    db.session.commit()
    ns = db.session.scalars(sa.select(models.Service).join(models.Service.host, isouter=True).join(models.Host.from_network, isouter=True)
                            .where(sa.and_(models.Service.has_been_inventoried == False, models.Network.project_id == project_id,
                                           sa.or_(models.Service.screenshot_http_id != None, models.Service.screenshot_https_id != None)))).first()
    ret_data = {'service_id': ns.id, 'service_title': ns.title or '', 'service_description': ns.description or '', 'host_title': ns.host.title or '', 'host_description': ns.host.description or '',
                'host_device_type': str(ns.host.device_type_id), 'host_device_vendor': str(ns.host.device_vendor_id), 'obj_title': str(ns.fulltitle)}
    if ns.screenshot_http_id is not None:
        ret_data['screenshot_http'] = url_for('files.download_file', file_id=ns.screenshot_http_id)
        ret_data['http_title'] = ns.http_title
    else:
        ret_data['screenshot_http'] = None
        ret_data['http_title'] = ''
    if ns.screenshot_https_id is not None:
        ret_data['screenshot_https'] = url_for('files.download_file', file_id=ns.screenshot_https_id)
        ret_data['https_title'] = ns.https_title
    else:
        ret_data['screenshot_https'] = None
        ret_data['https_title'] = ''
    return ret_data