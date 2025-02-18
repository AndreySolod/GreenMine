from flask import render_template, abort, redirect, url_for, flash, request, g
from flask_login import current_user, login_required
from app.controllers.action_modules import bp
from app.models import Project
from app import db, side_libraries
from app.helpers.projects_helpers import get_default_environment
from app.helpers.general_helpers import get_or_404
from app import automation_modules
from flask_babel import lazy_gettext as _l
from app.action_modules import AutomationModules
from app.helpers.roles import project_role_can_make_action_or_abort
from app import logger


@bp.route('/index')
@login_required
def action_modules_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        abort(400)
    project = db.get_or_404(Project, project_id)
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
@login_required
def module_run(module_name):
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        abort(400)
    module = automation_modules.get(module_name)
    if module is None:
        abort(404)
    project = get_or_404(db.session, Project, project_id)
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