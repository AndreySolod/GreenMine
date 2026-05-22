import json
import sqlalchemy as sa
from app import db, side_libraries, logger, automation_modules
from app.controllers.domains import bp
from flask import request, redirect, url_for, render_template, flash, abort, jsonify, send_file, g
from flask_login import current_user
import app.models as models
from app.helpers.general_helpers import get_or_404, get_bootstrap_table_json_data, BootstrapTableSearchParams
from app.helpers.projects_helpers import get_default_environment
import app.controllers.domains.forms as forms
from flask_babel import lazy_gettext as _l
from io import BytesIO
from app.helpers.roles import project_role_can_make_action, project_role_can_make_action_or_abort
import sqlalchemy.exc as exc
import ipaddress


@bp.route('/index')
def domain_index():
    try:
        project_id = int(request.args.get("project_id"))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index domains with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.Domain(), 'index', project=project)
    ctx = get_default_environment(models.Domain(project=project), 'index')
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('contextmenu')
    context = {'project': project}
    return render_template('domains/index.html', **context, **ctx)


@bp.route('/index-data')
def domain_index_data():
    try:
        project_id = int(request.args.get("project_id"))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index domain data with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.Domain(), 'index', project=project)
    additional_params: BootstrapTableSearchParams = {'obj': models.Domain,
            'column_index': ['id', 'title', 'created_at', 'created_by.title-input', 'updated_at', 'updated_by.title-input',
                             'description', 'domain_controllers', 'hosts', 'credentials.login-input'],
            'base_select': lambda x: x.where(models.Domain.project_id == project_id)}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index domains data on project #{project_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/new', methods=['GET', 'POST'])
def domain_new():
    try:
        project_id = int(request.args.get("project_id"))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request create domain with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.Domain(), 'create', project=project)
    form = forms.DomainCreateForm(project)
    if form.validate_on_submit():
        domain = models.Domain(project=project)
        db.session.add(domain)
        form.populate_obj(db.session, domain, current_user)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new domain #{domain.id}")
        flash(_l("Domain #%(domain_id)s has been successfully added", domain_id=domain.id), 'success')
        if form.submit_and_add_new.data:
            return redirect(url_for('domains.domain_new', **request.args))
        if project_role_can_make_action(current_user, domain, 'show'):
            return redirect(url_for('domains.domain_show', domain_id=domain.id))
        return redirect(url_for('domains.domain_index', project_id=project_id))
    elif request.method == 'GET':
        form.load_data_from_json(request.args)
    ctx = get_default_environment(models.Domain(project=project), 'new')
    return render_template('domains/new.html', **ctx, form=form)


@bp.route('/<domain_id>/show')
def domain_show(domain_id: str):
    try:
        domain_id = int(domain_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request show domain with non-integer domain_id {domain_id}")
        abort(400)
    domain = get_or_404(db.session, models.Domain, domain_id)
    project_role_can_make_action_or_abort(current_user, domain, 'show')
    filters = {"OperationSystemFamily": json.dumps({i: t for i, t in db.session.execute(sa.select(models.OperationSystemFamily.id, models.OperationSystemFamily.title))}),
               "DeviceType": json.dumps({i: t for i, t in db.session.execute(sa.select(models.DeviceType.id, models.DeviceType.title))}),
               'hash_types': json.dumps({i: t for i, t in db.session.execute(sa.select(models.HashType.id, models.HashType.title).select_from(models.Credential).join(models.Credential.hash_type).where(models.Credential.project_id == domain.project_id))}),
               'check_wordlists': json.dumps({i: t for i, t in db.session.execute(sa.select(models.CheckWordlist.id, models.CheckWordlist.title))})}
    ctx = get_default_environment(domain, 'show')
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('ckeditor')
    return render_template('domains/show.html', **ctx, domain=domain, filters=filters)


@bp.route('/<domain_id>/edit', methods=["GET", "POST"])
def domain_edit(domain_id: str):
    try:
        domain_id = int(domain_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request edit domain with non-integer domain_id {domain_id}")
        abort(400)
    domain = get_or_404(db.session, models.Domain, domain_id)
    project_role_can_make_action_or_abort(current_user, domain, 'update')
    form = forms.DomainEditForm(domain.project)
    if form.validate_on_submit():
        form.populate_obj(db.session, domain)
        domain.updated_by_id = current_user.id
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit domain {domain.id}")
        flash(_l("Domain #%(domain_id)s successfully changed", domain_id=domain.id), 'success')
        return redirect(url_for('domains.domain_show', domain_id=domain.id))
    elif request.method == 'GET':
        form.load_exist_value(domain)
        form.load_data_from_json(request.args)
    ctx = get_default_environment(domain, 'edit')
    return render_template('domains/edit.html', form=form, **ctx)


@bp.route('/<domain_id>/delete', methods=["POST"])
def domain_delete(domain_id: str):
    try:
        domain_id = int(domain_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request edit domain with non-integer domain_id {domain_id}")
        abort(400)
    domain = get_or_404(db.session, models.Domain, domain_id)
    project_id = domain.project_id
    project_role_can_make_action_or_abort(current_user, domain, 'delete')
    msg = _l("Domain #%(domain_id)s has been successfully deleted", domain_id=domain_id)
    db.session.delete(domain)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete domain {domain_id}")
    flash(msg, 'success')
    return redirect(url_for('domains.domain_index', project_id=project_id))
