import json
import sqlalchemy as sa
from app import db, side_libraries, logger
from app.controllers.networks import bp
from werkzeug.utils import secure_filename
from flask import request, redirect, url_for, render_template, flash, abort, jsonify, send_file
from flask_login import login_required, current_user
import app.models as models
from app.helpers.general_helpers import get_or_404, get_bootstrap_table_json_data
from app.helpers.projects_helpers import get_default_environment
import app.controllers.networks.forms as forms
from flask_babel import lazy_gettext as _l
from io import BytesIO
from app.helpers.roles import project_role_can_make_action, project_role_can_make_action_or_abort
import sqlalchemy.exc as exc


@bp.route("/networks/index")
@login_required
def network_index():
    try:
        project_id = int(request.args.get("project_id"))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index network with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.Network(), 'index', project=project)
    networks = {i: t for i, t in db.session.execute(sa.select(models.Network.id, models.Network.title).where(models.Network.project_id==project_id))}
    operation_systems = {i: t for i, t in db.session.execute(sa.select(models.OperationSystemFamily.id, models.OperationSystemFamily.title))}
    transport_level_protocols = {i: t for i, t in db.session.execute(sa.select(models.ServiceTransportLevelProtocol.id, models.ServiceTransportLevelProtocol.title))}
    port_states = {i: t for i, t in db.session.execute(sa.select(models.ServicePortState.id, models.ServicePortState.title))}
    device_types = {i: t for i, t in db.session.execute(sa.select(models.DeviceType.id, models.DeviceType.title))}
    device_vendors = {i: t for i, t in db.session.execute(sa.select(models.DeviceVendor.id, models.DeviceVendor.title))}
    filters = {"Network": json.dumps(networks), "OperationSystemFamily": json.dumps(operation_systems),
               "ServiceTransportLevelProtocol": json.dumps(transport_level_protocols), 'ServicePortState': json.dumps(port_states),
               'DeviceType': json.dumps(device_types), 'DeviceVendor': json.dumps(device_vendors)}
    ctx = get_default_environment(models.Network(project=project), 'index')
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('ckeditor')
    side_libraries.library_required('contextmenu')
    context = {'filters': filters, 'project': project}
    return render_template('networks/index.html', **context, **ctx)


@bp.route('/newtorks/index-data')
@login_required
def network_index_data():
    try:
        project_id = int(request.args.get("project_id"))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index network with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, models.Network(), 'index', project_id=project_id)
    additional_params = {'obj': models.Network, 'column_index': ['id', 'title', 'description', 'ip_address', 'internal_ip', 'asn', 'connect_cmd'],
                         'base_select': lambda x: x.where(models.Network.project_id == project_id)}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index network on project #{project_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/networks/host-by-network-data')
@login_required
def host_by_network_data():
    try:
        network_id = int(request.args.get('network_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index host by network with non-integer network_id {request.args.get('network_id')}")
        abort(400)
    try:
        project = db.session.scalars(sa.select(models.Project).join(models.Project.networks).where(models.Network.id == network_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(400)
    project_role_can_make_action_or_abort(current_user, models.Host(), 'index', project=project)
    additional_params = {'obj': models.Host, 'column_index': ['id', 'title', 'description', 'ip_address', 'mac', 'operation_system_family', 'operation_system_gen', 'device_type', 'device_vendor'],
                         'base_select': lambda x: x.where(models.Host.from_network_id == network_id)}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index host by network on network #{network_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route("/networks/new", methods=["GET", "POST"])
@login_required
def network_new():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request create network with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.Network(), 'create', project=project)
    form = forms.NetworkCreateForm(project_id)
    if form.validate_on_submit():
        network = models.Network()
        db.session.add(network)
        form.populate_obj(db.session, network, current_user)
        network.project_id = project_id
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new newtork {network.id}")
        flash(_l("Network #%(network_id)s has been successfully added", network_id=network.id), 'success')
        if form.submit_and_add_new.data:
            return redirect(url_for('networks.network_new', **request.args))
        if project_role_can_make_action(current_user, network, 'show'):
            return redirect(url_for('networks.network_show', network_id=network.id))
        return redirect(url_for('networks.network_index', project_id=project_id))
    elif request.method == "GET":
        form.load_data_from_json(request.args)
    ctx = get_default_environment(models.Network(project=project), 'new')
    context = {'form': form}
    return render_template('networks/new.html', **context, **ctx)


@bp.route('/hosts/index-data')
@login_required
def host_index_data():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request host index with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, models.Host(), 'index', project_id=project_id)
    additional_params = {'obj': models.Host, 'column_index': ['id', 'from_network', 'title', 'technical', 'description', 'ip_address', 'mac', 'operation_system_family', 'operation_system_gen', 'device_type', 'device_vendor', 'device_model.title-input'],
                         'base_select': lambda x: x.join(models.Host.from_network).where(sa.and_(models.Network.project_id==project_id, models.Host.excluded==False))}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request host index from project #{project_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/hosts/service-by-host-data')
@login_required
def service_by_host_data():
    try:
        host_id = int(request.args.get('host_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request service index with non-integer host_id {request.args.get('host_id')}")
        abort(400)
    try:
        project = db.session.scalars(sa.select(models.Project).join(models.Project.networks).join(models.Network.to_hosts).where(models.Host.id == host_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    project_role_can_make_action_or_abort(current_user, models.Service(), 'index', project=project)
    additional_params = {'obj': models.Service, 'column_index': ['id', 'title', 'port', 'access_protocol.title-input', 'transport_level_protocol', 'port_state', 'port_state_reason'],
                         'base_select': lambda x: x.where(models.Service.host_id == host_id)}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request service index on host #{host_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route("/hosts/index")
@login_required
def host_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request host index with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.Host(), 'index', project=project)
    networks = {i: t for i, t in db.session.execute(sa.select(models.Network.id, models.Network.title).where(models.Network.project_id==project_id))}
    operation_systems = {i: t for i, t in db.session.execute(sa.select(models.OperationSystemFamily.id, models.OperationSystemFamily.title))}
    transport_level_protocols = {i: t for i, t in db.session.execute(sa.select(models.ServiceTransportLevelProtocol.id, models.ServiceTransportLevelProtocol.title))}
    port_states = {i: t for i, t in db.session.execute(sa.select(models.ServicePortState.id, models.ServicePortState.title))}
    device_types = {i: t for i, t in db.session.execute(sa.select(models.DeviceType.id, models.DeviceType.title))}
    device_vendors = {i: t for i, t in db.session.execute(sa.select(models.DeviceVendor.id, models.DeviceVendor.title))}
    filters = {"Network": json.dumps(networks), "OperationSystemFamily": json.dumps(operation_systems),
               "ServiceTransportLevelProtocol": json.dumps(transport_level_protocols), 'ServicePortState': json.dumps(port_states),
               "DeviceType": json.dumps(device_types), "DeviceVendor": json.dumps(device_vendors)}
    ctx = get_default_environment(models.Host(), 'index', proj=project)
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('contextmenu')
    context = {'filters': filters, 'project': project}
    return render_template('hosts/index.html', **context, **ctx)


@bp.route('/hosts/excluded-index')
@login_required
def hosts_excluded_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request hosts excluded index with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.Host(), 'index', project=project)
    excluded_hosts = db.session.scalars(sa.select(models.Host).join(models.Host.from_network).where(sa.and_(models.Network.project_id == project_id, models.Host.excluded==True))).all()
    ctx = get_default_environment(models.Host(), 'excluded-index', proj=project)
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('contextmenu')
    context = {'project': project, 'hosts': excluded_hosts}
    return render_template('hosts/excluded-index.html', **ctx, **context)


@bp.route("/hosts/new", methods=["GET", "POST"])
@login_required
def host_new():
    try:
        project_id = int(request.args.get('project_id'))
    except ValueError:
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request host create with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.Host(), 'create', project=project)
    form = forms.HostFormNew(project_id)
    if form.validate_on_submit():
        host = models.Host()
        db.session.add(host)
        form.populate_obj(db.session, host, current_user)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new host #{host.id}")
        flash(_l("Host #%(host_id)s has been successfully added", host_id=host.id), 'success')
        if form.submit_and_add_new.data:
            return redirect(url_for('networks.host_new', **request.args))
        if project_role_can_make_action(current_user, host, 'show'):
            return redirect(url_for('networks.host_show', host_id=host.id))
        return redirect(url_for('networks.host_index', project_id=project_id))
    elif request.method == 'GET':
        form.load_default_data(db.session, models.Host)
        form.load_data_from_json(request.args)
    ctx = get_default_environment(models.Host(), 'new', proj=project)
    return render_template('hosts/new.html', form=form, **ctx)


@bp.route('/service/index-data')
@login_required
def service_index_data():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request service index with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, models.Service(), 'index', project_id=project_id)
    additional_params = {'obj': models.Service, 'column_index': ['id', 'title', 'host.ip_address-input', 'host.device_type.id-select', 'host.device_vendor.id-select', 'port', 'access_protocol.title-input', 'transport_level_protocol', 'port_state', 'port_state_reason', 'technical'],
                         'base_select': lambda x: x.join(models.Service.host).join(models.Host.from_network).where(sa.and_(models.Network.project_id==project_id, models.Host.excluded == False))}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request service index from project #{project_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/service/index')
@login_required
def service_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request service index with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.Service(), 'index', project=project)
    ctx = get_default_environment(models.Service(), 'index', proj=project)
    transport_level_protocols = {i: t for i, t in db.session.execute(sa.select(models.ServiceTransportLevelProtocol.id, models.ServiceTransportLevelProtocol.title))}
    port_states = {i: t for i, t in db.session.execute(sa.select(models.ServicePortState.id, models.ServicePortState.title))}
    device_types = {i: t for i, t in db.session.execute(sa.select(models.DeviceType.id, models.DeviceType.title))}
    device_vendors = {i: t for i, t in db.session.execute(sa.select(models.DeviceVendor.id, models.DeviceVendor.title))}
    filters = {'ServiceTransportLevelProtocol': json.dumps(transport_level_protocols), 'ServicePortState': json.dumps(port_states),
               'DeviceType': json.dumps(device_types), "DeviceVendor": json.dumps(device_vendors)}
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('contextmenu')
    context = {'filters': filters, 'project': project}
    return render_template('services/index.html', **context, **ctx)


@bp.route('/service/new', methods=['GET', "POST"])
@login_required
def service_new():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request create service with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.Service(), 'create', project=project)
    form = forms.ServiceFormNew(project_id)
    if form.validate_on_submit():
        service = models.Service()
        db.session.add(service)
        form.populate_obj(db.session, service, current_user)
        if form.temp_screenshot_http.data:
            scr = models.FileData()
            filename = secure_filename(form.temp_screenshot_http.data.filename)
            scr.title = filename
            scr.extension = filename.split('.')[-1]
            scr.description = _l("Screenshot for service %(port)s by host #%(host_id)s on project #%(project_id)s", port=service.port, host_id=service.host_id, project_id=project_id)
            scr.data = request.files[form.temp_screenshot_http.name].read()
            service.screenshot = scr
            db.session.add(scr)
        if form.temp_screenshot_https.data:
            scr = models.FileData()
            filename = secure_filename(form.temp_screenshot_https.data.filename)
            scr.title = filename
            scr.extension = filename.split('.')[-1]
            scr.description = _l("Screenshot for service %(port)s by host #%(host_id)s on project #%(project_id)s", port=service.port, host_id=service.host_id, project_id=project_id)
            scr.data = request.files[form.temp_screenshot_https.name].read()
            service.screenshot = scr
            db.session.add(scr)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new service {service.id}")
        flash(_l("Service #%(service_id)s has been successfully added", service_id=service.id), 'success')
        if project_role_can_make_action(current_user, service, 'show'):
            return redirect(url_for('networks.service_show', service_id=service.id))
        return redirect(url_for('networks.service_index', project_id=project_id))
    elif request.method == 'GET':
        form.load_data_from_json(request.args)
    ctx = get_default_environment(models.Service(), 'new', proj=project)
    return render_template('services/new.html', form=form, **ctx)


@bp.route("/services/index-by-port")
@login_required
def services_index_by_port():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request service index with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.Service(), 'index', project=project)
    ctx = get_default_environment(models.Service(), 'index_by_port', proj=project)
    transport_level_protocols = {i: t for i, t in db.session.execute(sa.select(models.ServiceTransportLevelProtocol.id, models.ServiceTransportLevelProtocol.title))}
    rtlp = {t: i for i, t in transport_level_protocols.items()}
    port_states = {i: t for i, t in db.session.execute(sa.select(models.ServicePortState.id, models.ServicePortState.title))}
    filters = {'ServiceTransportLevelProtocol': json.dumps(transport_level_protocols), 'ServicePortState': json.dumps(port_states), "reversed_TransportLevelProtocol": rtlp}
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('contextmenu')
    context = {'filters': filters, 'project': project}
    return render_template('services/index_group_by_port.html', **context, **ctx)


@bp.route("/networks/<network_id>/")
@bp.route("/networks/<network_id>/show")
@login_required
def network_show(network_id):
    try:
        network_id = int(network_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request network with non-integer network_id {network_id}")
        abort(404)
    network = db.get_or_404(models.Network, network_id)
    project_role_can_make_action_or_abort(current_user, network, 'show')
    operation_systems = {i: t for i, t in db.session.execute(sa.select(models.OperationSystemFamily.id, models.OperationSystemFamily.title))}
    device_types = {i: t for i, t in db.session.execute(sa.select(models.DeviceType.id, models.DeviceType.title))}
    filters = {'OperationSystemFamily': json.dumps(operation_systems), 'DeviceType': json.dumps(device_types)}
    ctx = get_default_environment(network, 'show')
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('ckeditor')
    context = {'network': network, 'filters': filters}
    return render_template('networks/show.html', **context, **ctx)


@bp.route("/networks/<network_id>/edit", methods=["GET", "POST"])
@login_required
def network_edit(network_id):
    try:
        network_id = int(network_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request network edit with non-integer network_id {network_id}")
        abort(400)
    network = get_or_404(db.session, models.Network, network_id)
    project_role_can_make_action_or_abort(current_user, network, 'update')
    form = forms.NetworkEditForm(network.ip_address, network.project_id)
    if form.validate_on_submit():
        form.populate_obj(db.session, network)
        network.updated_by_id = current_user.id
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit network {network.id}")
        flash(_l("Network #%(network_id)s successfully changed", network_id=network.id), 'success')
        return redirect(url_for('networks.network_show', network_id=network.id))
    elif request.method == 'GET':
        form.load_exist_value(network)
        form.load_data_from_json(request.args)
    ctx = get_default_environment(network, 'edit')
    return render_template('networks/edit.html', form=form, **ctx)


@bp.route("/networks/<network_id>/delete", methods=["POST"])
@login_required
def network_delete(network_id):
    try:
        network_id = int(network_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request network delete with non-integer network_id {network_id}")
        abort(400)
    network = get_or_404(db.session, models.Network, network_id)
    project_role_can_make_action_or_abort(current_user, network, 'delete')
    project_id = network.project_id
    msg = _l("Network #%(network_id)s has been successfully deleted", network_id=network_id)
    db.session.delete(network)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete network {network_id}")
    flash(msg, 'success')
    return redirect(url_for('networks.network_index', project_id=project_id))


@bp.route("/hosts/<host_id>")
@bp.route("/hosts/<host_id>/show")
@login_required
def host_show(host_id):
    try:
        host_id = int(host_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request host index with non-integer host_id {host_id}")
        abort(404)
    host = db.get_or_404(models.Host, host_id)
    project_role_can_make_action_or_abort(current_user, host, 'show')
    ctx = get_default_environment(host, 'show')
    filters = {'IssueStatus': json.dumps({i: t for i, t in db.session.execute(sa.select(models.IssueStatus.id, models.IssueStatus.title))})}
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('ckeditor')
    context = {'host': host, 'filters': filters,
               'dns_name_form': forms.NewHostDNSnameForm(), 'edit_related_objects_form': forms.EditRelatedObjectsHostForm(host)}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request host #{host.id}")
    side_libraries.library_required('contextmenu')
    return render_template('hosts/show.html', **context, **ctx)


@bp.route("/hosts/<host_id>/edit", methods=["GET", "POST"])
@login_required
def host_edit(host_id):
    try:
        host_id = int(host_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request host edit with non-integer host_id {host_id}")
        abort(404)
    host = get_or_404(db.session, models.Host, host_id)
    project_role_can_make_action_or_abort(current_user, host, 'update')
    form = forms.HostFormEdit(host.ip_address, host.from_network.project_id)
    if form.validate_on_submit():
        form.populate_obj(db.session, host)
        host.updated_by_id = current_user.id
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit host #{host.id}")
        flash(_l("Host #%(host_id)s successfully changed", host_id=host_id), 'success')
        return redirect(url_for('networks.host_show', host_id=host.id))
    elif request.method == 'GET':
        form.load_exist_value(host)
        form.load_data_from_json(request.args)
    ctx = get_default_environment(host, 'edit')
    return render_template('hosts/edit.html', form=form, **ctx)


@bp.route('/hosts/<int:host_id>/include-to-research', methods=['POST'])
@login_required
def add_host_to_research(host_id: int):
    host = get_or_404(db.session, models.Host, host_id)
    project_role_can_make_action_or_abort(current_user, host, 'update')
    host.excluded = False
    db.session.add(host)
    db.session.commit()
    return redirect(url_for('networks.host_show', host_id=host.id))


@bp.route('/hosts/<int:host_id>/exclude-from-research', methods=['POST'])
@login_required
def exclude_host_from_research(host_id: int):
    host = db.get_or_404(models.Host, host_id)
    project_role_can_make_action_or_abort(current_user, host, 'update')
    host.excluded = True
    db.session.add(host)
    db.session.commit()
    return redirect(url_for('networks.host_show', host_id=host.id))


@bp.route("/hosts/<int:host_id>/delete", methods=["POST"])
@login_required
def host_delete(host_id):
    host = get_or_404(db.session, models.Host, host_id)
    project_role_can_make_action_or_abort(current_user, host, 'delete')
    msg = _l("Host #%(host_id)s has been successfully deleted", host_id=host_id)
    project_id = host.from_network.project_id
    db.session.delete(host)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete host #{host_id}")
    flash(msg, 'success')
    return redirect(url_for('networks.host_index', project_id=project_id))


@bp.route('/service/<service_id>')
@bp.route('/service/<service_id>/show')
@login_required
def service_show(service_id):
    try:
        service_id = int(service_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request service with non-integer service_id {service_id}")
        abort(400)
    service = db.get_or_404(models.Service, service_id)
    project_role_can_make_action_or_abort(current_user, service, 'show')
    ctx = get_default_environment(service, 'show')
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('ckeditor')
    context = {'service': service, 'edit_related_objects': forms.EditRelatedObjectsForm(service)}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request service #{service_id}")
    return render_template('services/show.html', **context, **ctx)


@bp.route('/service/<service_id>/edit', methods=["GET", "POST"])
def service_edit(service_id):
    try:
        service_id = int(service_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request service edit with non-integer service_id {service_id}")
        abort(400)
    service = get_or_404(db.session, models.Service, service_id)
    project_role_can_make_action_or_abort(current_user, service, 'update')
    form = forms.ServiceFormEdit(service.port, service.host.from_network.project_id)
    if form.validate_on_submit():
        form.populate_obj(db.session, service)
        service.updated_by_id = current_user.id
        if form.temp_screenshot_http.data:
            if service.screenshot_http:
                db.session.delete(service.screenshot)
            scr = models.FileData()
            filename = secure_filename(form.temp_screenshot_http.data.filename)
            scr.title = filename
            scr.extension = filename.split('.')[-1]
            scr.description = str(_l("Screenshot for service %(port)s by host #%(host_id)s on project #%(project_id)s", port=service.port, host_id=service.host_id, project_id=service.host.from_network.project_id))
            scr.data = request.files[form.temp_screenshot_http.name].read()
            service.screenshot_http = scr
            db.session.add(scr)
        if form.temp_screenshot_https.data:
            if service.screenshot_https:
                db.session.delete(service.screenshot_https)
            scr = models.FileData()
            scr.title = secure_filename(form.temp_screenshot_https.data.filename)
            scr.extension = filename.split('.')[-1]
            scr.description = str(_l("Screenshot for service %(port)s by host #%(host_id)s on project #%(project_id)s", port=service.port, host_id=service.host_id, project_id=service.host.from_network.project_id))
            scr.data = request.files[form.temp_screenshot_https.name].read()
            service.screenshot_https = scr
            db.session.add(scr)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit service {service.id}")
        flash(_l("Service «%(serv_title)s» successfully changed", serv_title=service.fulltitle), 'success')
        return redirect(url_for('networks.service_show', service_id=service.id))
    elif request.method == 'GET':
        form.load_exist_value(service)
        form.load_data_from_json(request.args)
    ctx = get_default_environment(service, 'edit')
    return render_template('services/new.html', form=form, **ctx)


@bp.route("/service/<int:service_id>/delete", methods=["POST"])
def service_delete(service_id):
    service = get_or_404(db.session, models.Service, service_id)
    project_role_can_make_action_or_abort(current_user, service, 'delete')
    msg = _l("Service #%(service_id)s has been successfully deleted", service_id=service_id)
    project_id = service.host.from_network.project_id
    db.session.delete(service)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete service {service.id}")
    flash(msg, 'success')
    return redirect(url_for('networks.service_index', project_id=project_id))


@bp.route("/service/getdefaultaccessprotocol/<port>/<transport_proto>")
@login_required
def get_default_access_proto(port, transport_proto):
    try:
        port = int(port)
        transport_proto = int(transport_proto)
    except (ValueError, TypeError):
        abort(400)
    proto = db.session.scalars(sa.select(models.DefaultPortAndTransportProto).where(sa.and_(models.DefaultPortAndTransportProto.port==port, models.DefaultPortAndTransportProto.transport_level_protocol_id==transport_proto))).first()
    if proto is not None:
        return jsonify({'proto': proto.access_protocol.id, 'title': proto.access_protocol.title})
    else:
        abort(404)


@bp.route('/networks/generate-all-included-ip')
@login_required
def generate_all_included_ip_addresses():
    try:
        project_id = int(request.args.get('project_id'))
        network_ids = list(map(int, request.args.get('network_ids').split(',')))
    except (ValueError, TypeError, AttributeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request generate all included ip with non-integer project_id {request.args.get('project_id')}"
                       f"and network_ids {request.args.get('network_ids')}")
        abort(400)
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.Network(), 'index', project=project)
    networks = db.session.scalars(sa.select(models.Network).where(models.Network.id.in_(network_ids))).all()
    ip_list = set()
    send_data = BytesIO()
    excluded_ips = db.session.scalars(sa.select(models.Host.ip_address).join(models.Host.from_network).where(models.Network.project_id == project_id)).all()
    for n in networks:
        for i in n.ip_address:
            if i in excluded_ips:
                continue
            ip_list.add(str(i))
    send_data.write("\n".join(list(ip_list)).encode())
    send_data.seek(0)
    return send_file(send_data, 'text/plain', True, 'ip_list.txt')
