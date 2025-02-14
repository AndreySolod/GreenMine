import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db, logger
import json
import app.models as models
from app.controllers.networks import bp
from app.helpers.general_helpers import get_bootstrap_table_json_data, bootstrap_table_argument_parsing
from flask import abort, request, jsonify, current_app
from flask_login import login_required, current_user
from app.helpers.roles import project_role_can_make_action_or_abort
import sqlalchemy.exc as exc


@bp.route('/networks/<network_id>/get-hosts')
@login_required
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
@login_required
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
    additional_params = {'obj': models.Service, 'column_index': ['id', 'title', 'technical', 'port', 'access_protocol'],
                         'base_select': lambda x: x.join(models.Service.host).where(models.Host.id == host_id)}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request services from host #{host_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/services/get-select2-data')
@login_required
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
    data = db.session.scalars(sa.select(models.Service).join(models.Service.host).join(models.Host.from_network)
                              .where(sa.and_(models.Network.project_id==project_id,
                                             (sa.cast(models.Host.ip_address, sa.String) + ':' + sa.cast(models.Service.port, sa.String()) + " " + models.Service.title).ilike('%' + query + '%')))
                                             .limit(current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"] + 1)
                              .offset((page - 1) * current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"])).all()
    more = len(data) == current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"] + 1
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request service on project #{project_id} via select2-data")
    result = {'results': [{'id': i.id, 'text': i.treeselecttitle} for i in data[:min(len(data), current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"]):]], 'pagination': {'more': more}}
    return jsonify(result)


@bp.route('/hosts/get-select2-data')
@login_required
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
    data = db.session.scalars(sa.select(models.Host).join(models.Host.from_network).where(sa.and_(("«" + sa.func.ifnull(models.Host.title, "") + "»: " + models.Host.ip_address).ilike('%' + query + '%'),
                                                                                                  models.Network.project_id == project_id))
                                                    .limit(current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"] + 1)
                                                    .offset((page - 1) * current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"])).all()
    for i in data:
        if i.title is None:
            print(i)
    more = len(data) == current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"] + 1
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request host on project #{project_id} via select2-data")
    print('i.title:', data[0].title, data[0].treeselecttitle, type(data[0].title))
    result = {'results': [{'id': i.id, 'text': i.treeselecttitle} for i in data[:min(len(data), current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"]):]], 'pagination': {'more': more}}
    return jsonify(result)


@bp.route('/services/index-by-all-services-port-data')
@login_required
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
    sql = sql.outerjoin(models.Service.host).outerjoin(models.Host.from_network).where(models.Network.project_id == project_id).outerjoin(
        models.Service.transport_level_protocol).outerjoin(models.DefaultPortAndTransportProto,
        db.and_(models.Service.port == models.DefaultPortAndTransportProto.port, models.Service.transport_level_protocol_id == models.DefaultPortAndTransportProto.transport_level_protocol_id)
                                                          ).outerjoin(models.DefaultPortAndTransportProto.access_protocol)
    sql_total = sql_total.outerjoin(models.Service.host).outerjoin(models.Host.from_network).where(models.Network.project_id == project_id).outerjoin(
        models.Service.transport_level_protocol).outerjoin(models.DefaultPortAndTransportProto, 
        db.and_(models.Service.port == models.DefaultPortAndTransportProto.port, models.Service.transport_level_protocol_id == models.DefaultPortAndTransportProto.transport_level_protocol_id)
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
@login_required
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
                         .where(sa.and_(models.Network.project_id==project_id, models.Service.port == port, models.Service.transport_level_protocol_id == transport_level_protocol))}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request service index from project #{project_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/hosts/get-select2-interfaces-data')
@login_required
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
                                                                                                  models.Host.ip_address.ilike("%" + query + "%")))
                                                                                                  .limit(current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"] + 1)
                                                                                                  .offset((page - 1) * current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"])).all()
    more = len(data) == current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"] + 1
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request interfaces for host {host.id} via select2-data")
    result = {'results': [{'id': i.id, 'text': str(i.ip_address)} for i in data[:min(len(data), current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"]):]], 'pagination': {'more': more}}
    return jsonify(result)