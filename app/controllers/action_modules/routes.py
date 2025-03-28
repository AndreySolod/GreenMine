from flask import render_template, abort, redirect, url_for, flash, request, g
from flask_login import current_user
from app.controllers.action_modules import bp
from app import db, side_libraries
from app.helpers.projects_helpers import get_default_environment
from app.helpers.general_helpers import get_bootstrap_table_json_data
from app import automation_modules
from flask_babel import lazy_gettext as _l
from app.action_modules import AutomationModules
from app.helpers.roles import project_role_can_make_action_or_abort
from app import logger
import app.models as models


@bp.route('/index')
def action_modules_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        abort(400)
    project = db.get_or_404(models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, AutomationModules(), 'index', project=project)
    ms = automation_modules.action_modules
    modules = []
    for m in ms:
        if hasattr(m, 'show_on_exploit_list') and m.show_on_exploit_list or not hasattr(m, 'show_on_exploit_list'):
            modules.append(m)
    ctx = get_default_environment(automation_modules, 'index', proj=project)
    side_libraries.library_required('bootstrap_table')
    context = {'action_modules': modules, 'project': project}
    return render_template('action_modules/index.html', **ctx, **context)


@bp.route('/<module_name>/run', methods=['GET', "POST"])
def module_run(module_name):
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        abort(400)
    module = automation_modules.get(module_name)
    if module is None:
        abort(404)
    project = db.get_or_404(models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, AutomationModules(), 'create', project=project)
    form = module.run_form(project_id)
    if form.validate_on_submit():
        module.run(form, current_user, request.files, locale=g.locale, project_id=project_id)
        flash(_l("The module has been sent for execution"), 'success')
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' was startet a task '{module_name}'")
        return redirect(url_for('action_modules.action_modules_index', project_id=project_id))
    ctx = get_default_environment(automation_modules, 'run', proj=project, action_module=module)
    context = {'form': form, 'project': project}
    return render_template('action_modules/run_module.html', **ctx, **context)


@bp.route("/default-credentials/index")
def default_credentials_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        abort(400)
    project = db.get_or_404(models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, AutomationModules(), 'default_credentials', project=project)
    ctx = get_default_environment(models.DefaultCredential(), 'index', proj=project)
    side_libraries.library_required('bootstrap_table')
    return render_template('action_modules/default_credentials.html', **ctx, project=project)


@bp.route("/default-credentials/index-data")
def default_credentials_index_data():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request default credentials index with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, AutomationModules(), 'default_credentials', project_id=project_id)
    additional_params = {'obj': models.DefaultCredential, 'column_index': ['id', 'title', 'login', 'password', 'comment'],
                         'base_select': lambda x: x}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request default credentials index from project #{project_id}")
    return get_bootstrap_table_json_data(request, additional_params)