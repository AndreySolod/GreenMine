import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db, logger
import json
import app.models as models
from app.controllers.networks import bp
from app.helpers.general_helpers import get_bootstrap_table_json_data, bootstrap_table_argument_parsing
from flask import abort, request, jsonify, current_app
from flask_login import current_user
from app.helpers.roles import project_role_can_make_action_or_abort
import sqlalchemy.exc as exc
import binascii


@bp.route('/networks/<network_id>/get-hosts')
def host_to_network(network_id):
    try:
        network_id = int(network_id)
    except (ValueError, TypeError):
        abort(400)
    try:
        project_id = db.session.scalars(sa.select(models.Network.project_id).where(models.Network.id == network_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    project_role_can_make_action_or_abort(current_user, models.Host(), 'index', project_id=project_id)
    additional_params = {'obj': models.Host, 'column_index': ['id', 'title', 'ip_address', 'operation_system_family', 'operation_system_gen', 'device_type', 'device_vendor'],
                         'base_select': lambda x: x.where(models.Host.from_network_id == network_id)}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request hosts from network #{network_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/hosts/<host_id>/get-services')
def service_to_host(host_id):
    try:
        host_id = int(host_id)
    except (ValueError, TypeError):
        abort(400)
    try:
        project_id = db.session.scalars(sa.select(models.Network.project_id).join(models.Network.to_hosts).where(models.Host.id == host_id)).one()
    except (exc.NoResultFound, exc.MultipleResultsFound):
        abort(404)
    project_role_can_make_action_or_abort(current_user, models.Service(), 'index', project_id=project_id)
    additional_params = {'obj': models.Service, 'column_index': ['id', 'title', 'technical', 'port', 'access_protocol.title-input'],
                         'base_select': lambda x: x.join(models.Service.host, isouter=True).where(models.Host.id == host_id)}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request services from host #{host_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/services/get-select2-data')
def get_select2_service_data():
    try:
        page = int(request.args.get('page'))
    except TypeError:
        page = 1
    except ValueError:
        abort(400)
    try:
        project_id = int(request.args.get('project_id'))
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == project_id)).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        abort(400)
    project_role_can_make_action_or_abort(current_user, models.Service(), 'index', project=project)
    query = request.args.get('term') if request.args.get('term') else ''
    data = db.session.scalars(sa.select(models.Service).join(models.Service.host, isouter=True).join(models.Host.from_network, isouter=True).join(models.Service.transport_level_protocol, isouter=True)
                              .where(sa.and_(models.Network.project_id==project_id, models.Host.excluded == False,
                                             (sa.cast(models.Host.ip_address, sa.String) + ':' + sa.cast(models.Service.port, sa.String) + "/" + sa.func.ifnull(models.ServiceTransportLevelProtocol.title, "") + " " + sa.func.ifnull(models.Service.title, "")).ilike('%' + query + '%')))
                                             .limit(current_app.config["GlobalSettings"].pagination_element_count_select2 + 1)
                              .offset((page - 1) * current_app.config["GlobalSettings"].pagination_element_count_select2)).all()
    more = len(data) == current_app.config["GlobalSettings"].pagination_element_count_select2 + 1
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request service on project #{project_id} via select2-data")
    result = {'results': [{'id': i.id, 'text': i.treeselecttitle} for i in data[:min(len(data), current_app.config["GlobalSettings"].pagination_element_count_select2):]], 'pagination': {'more': more}}
    return jsonify(result)


@bp.route('/hosts/get-select2-data')
def get_select2_host_data():
    try:
        page = int(request.args.get('page'))
    except TypeError:
        page = 1
    except ValueError:
        abort(400)
    try:
        project_id = int(request.args.get('project_id'))
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == project_id)).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        abort(400)
    project_role_can_make_action_or_abort(current_user, models.Service(), 'index', project=project)
    query = request.args.get('term') if request.args.get('term') else ''
    data = db.session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(sa.and_(("«" + sa.func.ifnull(models.Host.title, "") + "»: " + models.Host.ip_address).ilike('%' + query + '%'),
                                                                                                  models.Network.project_id == project_id,
                                                                                                  models.Host.excluded == False))
                                                    .limit(current_app.config["GlobalSettings"].pagination_element_count_select2 + 1)
                                                    .offset((page - 1) * current_app.config["GlobalSettings"].pagination_element_count_select2)).all()
    more = len(data) == current_app.config["GlobalSettings"].pagination_element_count_select2 + 1
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request host on project #{project_id} via select2-data")
    result = {'results': [{'id': i.id, 'text': i.treeselecttitle} for i in data[:min(len(data), current_app.config["GlobalSettings"].pagination_element_count_select2):]], 'pagination': {'more': more}}
    return jsonify(result)


@bp.route('/hosts/get-select2-all-data')
def get_select2_all_host_data():
    ''' The same that get_select2_host_data, but with excluded host '''
    try:
        page = int(request.args.get('page'))
    except TypeError:
        page = 1
    except ValueError:
        abort(400)
    try:
        project_id = int(request.args.get('project_id'))
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == project_id)).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        abort(400)
    project_role_can_make_action_or_abort(current_user, models.Service(), 'index', project=project)
    query = request.args.get('term') if request.args.get('term') else ''
    data = db.session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(sa.and_(("«" + sa.func.ifnull(models.Host.title, "") + "»: " + models.Host.ip_address).ilike('%' + query + '%'),
                                                                                                  models.Network.project_id == project_id))
                                                    .limit(current_app.config["GlobalSettings"].pagination_element_count_select2 + 1)
                                                    .offset((page - 1) * current_app.config["GlobalSettings"].pagination_element_count_select2)).all()
    more = len(data) == current_app.config["GlobalSettings"].pagination_element_count_select2 + 1
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request host on project #{project_id} via select2-data")
    result = {'results': [{'id': i.id, 'text': i.treeselecttitle} for i in data[:min(len(data), current_app.config["GlobalSettings"].pagination_element_count_select2):]], 'pagination': {'more': more}}
    return jsonify(result)


@bp.route('/services/index-by-all-services-port-data')
def all_services_port_data():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index services port with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, models.Service(), 'index', project_id=project_id)
    search, sort, order, offset, limit, filter_data, _ = bootstrap_table_argument_parsing(request)
    sql_total = sa.select(sa.func.count(models.Service.port.distinct()))
    sql = sa.select(models.Service.port, models.ServiceTransportLevelProtocol.title, models.AccessProtocol.title)
    sql = sql.outerjoin(models.Service.host).outerjoin(models.Host.from_network).where(sa.and_(models.Network.project_id == project_id, models.Host.excluded == False)).outerjoin(
        models.Service.transport_level_protocol).outerjoin(models.DefaultPortAndTransportProto,
        sa.and_(models.Service.port == models.DefaultPortAndTransportProto.port, models.Service.transport_level_protocol_id == models.DefaultPortAndTransportProto.transport_level_protocol_id)
                                                          ).outerjoin(models.DefaultPortAndTransportProto.access_protocol)
    sql_total = sql_total.outerjoin(models.Service.host).outerjoin(models.Host.from_network).where(sa.and_(models.Network.project_id == project_id, models.Host.excluded == False)).outerjoin(
        models.Service.transport_level_protocol).outerjoin(models.DefaultPortAndTransportProto, 
        sa.and_(models.Service.port == models.DefaultPortAndTransportProto.port, models.Service.transport_level_protocol_id == models.DefaultPortAndTransportProto.transport_level_protocol_id)
                                                          ).outerjoin(models.DefaultPortAndTransportProto.access_protocol)
    where_search = [sa.cast(models.Service.port, sa.String).ilike('%' + search + '%'),
                    sa.cast(models.ServiceTransportLevelProtocol.title, sa.String).ilike('%' + search + '%'),
                    sa.cast(models.AccessProtocol.title, sa.String).ilike("%" + search + "%")]
    where_filter = []
    if filter_data.get('port_number'):
        where_filter.append(sa.cast(models.Service.port, sa.String).ilike('%' + filter_data.get('port_number') + '%'))
    if filter_data.get('transport_level_protocol'):
        where_filter.append(models.Service.transport_level_protocol_id == filter_data.get('transport_level_protocol'))
    if filter_data.get('default_access_protocol'):
        where_filter.append(sa.cast(models.AccessProtocol.title, sa.String).ilike('%' + filter_data.get('default_access_protocol') + '%'))
    sql = sql.where(sa.and_(sa.or_(*where_search), sa.and_(*where_filter)))
    sql_total = sql_total.where(sa.and_(*where_search),
                                        sa.and_(*where_filter))
    if sort == 'port_number' and order is not None:
        sql = sql.order_by(getattr(models.Service.port, order)())
    elif sort == 'transport_level_protocol' and order is not None:
        sql = sql.order_by(getattr(models.Service.transport_level_protocol_id, order)())
    elif sort == 'default_access_protocol':
        sql = sql.order_by(getattr(models.AccessProtocol.title, order)())
    else:
        sql = sql.order_by(models.Service.port.asc())
    sql = sql.limit(limit).offset(offset).distinct()
    total = db.session.execute(sql_total).one()[0]
    rows = db.session.execute(sql).all()
    lst = []
    for i in rows:
        lst.append({'port_number': str(i[0]), 'transport_level_protocol': i[1], 'default_access_protocol': i[2]})
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index service on project #{project_id}")
    return jsonify({'total': total, "rows": lst})


@bp.route('/services/services-by-port-data/<port>/<transport_level_protocol>')
def services_by_port_data(port, transport_level_protocol):
    try:
        port = int(port)
        transport_level_protocol = int(transport_level_protocol)
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index services by port with non-integer paramethers {request.args.get('project_id')}, {port}, {transport_level_protocol}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, models.Service(), 'index', project_id=project_id)
    additional_params = {'obj': models.Service, 'column_index': ['id', 'title', 'host.ip_address-input', 'port', 'access_protocol.title-input', 'transport_level_protocol', 'port_state', 'port_state_reason'],
                         'base_select': lambda x: x.join(models.Service.host).join(models.Host.from_network)
                         .where(sa.and_(models.Network.project_id==project_id, models.Service.port == port, models.Service.transport_level_protocol_id == transport_level_protocol,
                                        models.Host.excluded == False))}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request service index from project #{project_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/hosts/get-select2-interfaces-data')
def get_select2_hosts_interfaces_data():
    try:
        page = int(request.args.get('page'))
    except TypeError:
        page = 1
    except ValueError:
        abort(400)
    try:
        host_id = int(request.args.get('host_id'))
        host = db.session.scalars(sa.select(models.Host).where(models.Host.id == host_id)).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        abort(400)
    project_role_can_make_action_or_abort(current_user, host, 'index')
    query = request.args.get('term') if request.args.get('term') else ''
    data = db.session.scalars(sa.select(models.Host).outerjoin(models.Host.from_network).where(sa.and_(models.Host.id != host.id, models.Network.project_id == host.from_network.project_id,
                                                                                                       models.Host.excluded == False,
                                                                                                  models.Host.ip_address.ilike("%" + query + "%")))
                                                                                                  .limit(current_app.config["GlobalSettings"].pagination_element_count_select2 + 1)
                                                                                                  .offset((page - 1) * current_app.config["GlobalSettings"].pagination_element_count_select2)).all()
    more = len(data) == current_app.config["GlobalSettings"].pagination_element_count_select2 + 1
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request interfaces for host {host.id} via select2-data")
    result = {'results': [{'id': i.id, 'text': str(i.ip_address)} for i in data[:min(len(data), current_app.config["GlobalSettings"].pagination_element_count_select2):]], 'pagination': {'more': more}}
    return jsonify(result)


@bp.route('/network/graph/add_hosts')
def add_hosts_to_network_graph():
    try:
        network_id = int(request.args.get('network_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to request hosts to network graph with non-integer network_id {request.args.get('network_id')}")
        abort(400)
    network = db.get_or_404(models.Network, network_id)
    project_role_can_make_action_or_abort(current_user, network, 'show_graph')
    nodes = []
    edges = []
    for host in network.to_hosts:
        new_node = {'id': 'host_' + str(host.id), 'label': str(host.ip_address)}
        if host.operation_system_family and host.operation_system_family.icon:
            new_node["icon"] = {"face": "FontAwesome", "code": binascii.unhexlify(host.operation_system_family.icon.encode()).decode()} # to convert: make fontawesome code (like f17c), then binascii.hexlify("\uf17c".encode())
            new_node["shape"] = "icon"
        nodes.append(new_node)
        edges.append({'from': 'network_' + str(network.id), 'to': 'host_' + str(host.id)})
        for iface in host.interfaces:
            new_edge = {'from': 'host_' + str(host.id), 'to': 'host_' + str(iface.id), 'arrows': 'to,from'}
            new_edge_another = {'from': 'host_' + str(iface.id), 'to': 'host_' + str(host.id), 'arrows': 'to,from'}
            if not new_edge in edges and not new_edge_another in edges:
                edges.append(new_edge)
    return jsonify({'nodes': nodes, 'edges': edges})


@bp.route('/networks/graph/add_services')
def add_services_to_network_graph():
    try:
        host_id = int(request.args.get('host_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to request service to network graph with non-integer host_id {request.args.get('host_id')}")
        abort(400)
    host = db.get_or_404(models.Host, host_id)
    project_role_can_make_action_or_abort(current_user, host.from_network, 'show_graph')
    nodes = []
    edges = []
    for service in host.services:
        service_title = str(service.port) + ": " + service.title if service.title else str(service.port)
        nodes.append({'id': 'service_' + str(service.id), 'label': service_title, 'color': 'yellow'})
        edges.append({'from': 'host_' + str(host.id), 'to': 'service_' + str(service.id)})
        for accessible_host in service.accessible_from_hosts:
            edges.append({'from': 'host_' + str(accessible_host.id), 'to': 'service_' + str(service.id), 'arrows': 'to'})
    return jsonify({'nodes': nodes, 'edges': edges})


@bp.route('/services/accessible-from-hosts')
def hosts_from_which_service_are_avaliable():
    try:
        service_id = int(request.args.get('service_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to request hosts from which service are avaliable with non-integer service_id {request.args.get('service_id')}")
        abort(400)
    service = db.get_or_404(models.Service, service_id)
    project_role_can_make_action_or_abort(current_user, service, 'show')
    additional_params = {'obj': models.Host, 'column_index': ['id', 'from_network.title-input', 'title', 'ip_address', 'operation_system_family.title-input'],
                         'base_select': lambda x: x.join(models.Host.accessible_services).where(sa.and_(models.Service.id == service_id))}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request host from which service are avaliable with service_id {service_id}")
    return get_bootstrap_table_json_data(request, additional_params)