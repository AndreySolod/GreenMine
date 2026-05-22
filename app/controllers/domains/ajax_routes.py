import sqlalchemy as sa
from app import db, logger
import app.models as models
from app.controllers.domains import bp
from app.helpers.general_helpers import get_bootstrap_table_json_data, BootstrapTableSearchParams
from flask import abort, request
from flask_login import current_user
from app.helpers.roles import project_role_can_make_action_or_abort
import sqlalchemy.exc as exc


@bp.route('/<domain_id>/get-domain-controllers')
def domain_controllers_to_domain(domain_id):
    try:
        domain_id = int(domain_id)
    except (ValueError, TypeError):
        abort(400)
    try:
        project_id = db.session.scalars(sa.select(models.Domain.project_id).where(models.Domain.id == domain_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    project_role_can_make_action_or_abort(current_user, models.Host(), 'index', project_id=project_id)
    additional_params: BootstrapTableSearchParams = {'obj': models.Host,
                                                     'column_index': ['id', 'title', 'ip_address', "labels.title-input", 'operation_system_family', 'operation_system_gen', 'device_type', 'device_vendor'],
                                                     'base_select': lambda x: x.where(models.Host.domain_controller_for_id == domain_id),
                                                     "convert_funcs": {"labels.title-input": lambda host: "".join(map(lambda t: f'<i class="{t.icon_class}" style="color: {t.icon_color}"></i>', host.labels))}}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request domain controllers from domain #{domain_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/<domain_id>/get-hosts')
def hosts_to_domain(domain_id):
    try:
        domain_id = int(domain_id)
    except (ValueError, TypeError):
        abort(400)
    try:
        project_id = db.session.scalars(sa.select(models.Domain.project_id).where(models.Domain.id == domain_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    project_role_can_make_action_or_abort(current_user, models.Host(), 'index', project_id=project_id)
    additional_params: BootstrapTableSearchParams = {'obj': models.Host,
                                                     'column_index': ['id', 'title', 'ip_address', "labels.title-input", 'operation_system_family', 'operation_system_gen', 'device_type', 'device_vendor'],
                                                     'base_select': lambda x: x.where(models.Host.domain_id == domain_id),
                                                     "convert_funcs": {"labels.title-input": lambda host: "".join(map(lambda t: f'<i class="{t.icon_class}" style="color: {t.icon_color}"></i>', host.labels))}}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request hosts from domain #{domain_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/<domain_id>/get-credentials')
def credentials_to_domain(domain_id):
    try:
        domain_id = int(domain_id)
    except (ValueError, TypeError):
        abort(400)
    try:
        project_id = db.session.scalars(sa.select(models.Domain.project_id).where(models.Domain.id == domain_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    project_role_can_make_action_or_abort(current_user, models.Credential(), 'index', project_id=project_id)
    additional_params: BootstrapTableSearchParams = {'obj': models.Credential,
                                                     'column_index': ['id', 'login', 'password_hash', 'password', 'hash_type', 'check_wordlist', 'is_admin'],
                                                     'base_select': lambda x: x.where(models.Credential.domain_id == domain_id),
                                                     "convert_funcs": {"labels.title-input": lambda host: "".join(map(lambda t: f'<i class="{t.icon_class}" style="color: {t.icon_color}"></i>', host.labels))}}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request hosts from domain #{domain_id}")
    return get_bootstrap_table_json_data(request, additional_params)