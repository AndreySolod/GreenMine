from app import db, side_libraries, logger
from flask import render_template, redirect, flash, url_for, request, abort
from app.controllers.admin import bp
from app.helpers.admin_helpers import DefaultEnvironment
from flask_login import current_user
import app.models as models
from app.helpers.admin_helpers import get_all_project_objects
import sqlalchemy as sa
import sqlalchemy.exc as exc
import app.controllers.admin.roles_forms as forms
from flask_babel import lazy_gettext as _l
from flask_login import current_user


@bp.route('/project_roles/index')
def project_role_index():
    project_roles = db.session.scalars(sa.select(models.ProjectRole)).all()
    ctx = DefaultEnvironment('project_role_index')()
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('contextmenu')
    return render_template('admin/project_role_index.html', **ctx, project_roles=project_roles)


@bp.route('/project_roles/new', methods=['GET', 'POST'])
def project_role_new():
    form = forms.ProjectRoleCreateForm()
    if form.validate_on_submit():
        pr = models.ProjectRole()
        form.populate_obj(db.session, pr, current_user)
        db.session.add(pr)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' created new project role #{pr.id}: '{pr.title}'")
        flash(_l("New Project role successfully created"), 'success')
        return redirect(url_for('admin.project_role_index'))
    elif request.method == 'GET':
        form.load_default_data(db.session, models.ProjectRole)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment('project_role_new')()
    context = {'form': form}
    return render_template('admin/project_role_new.html', **ctx, **context)


@bp.route('/project_roles/<role_id>/edit', methods=['GET', 'POST'])
def project_role_edit(role_id):
    try:
        role_id = int(role_id)
    except (ValueError, TypeError):
        abort(400)
    try:
        pr = db.session.scalars(sa.select(models.ProjectRole).where(models.ProjectRole.id == role_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    form = forms.ProjectRoleEditForm(project_role=pr)
    if form.validate_on_submit():
        form.populate_obj(db.session, pr, current_user)
        db.session.add(pr)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' updated project role #{pr.id}: '{pr.title}'")
        flash(_l("Project role successfully edited!"), 'success')
        return redirect(url_for('admin.project_role_index'))
    elif request.method == 'GET':
        form.load_exist_value(pr)
    ctx = DefaultEnvironment('project_role_edit', pr)()
    context = {'form': form}
    return render_template('admin/project_role_edit.html', **ctx, **context)


@bp.route('/project_roles/<role_id>/delete', methods=['POST', 'DELETE'])
def project_role_delete(role_id):
    try:
        role_id = int(role_id)
    except (ValueError, TypeError):
        abort(400)
    try:
        pr = db.session.scalars(sa.select(models.ProjectRole).where(models.ProjectRole.id == role_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    if pr.string_slug == 'anonymous':
        flash(_l("Project role «Anonymous» cannot being deleted"), 'error')
        return redirect(url_for('admin.project_role_index'))
    i, t = pr.id, pr.title
    db.session.delete(pr)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete project role #{i}: '{t}'")
    flash(_l("Project role «%(project_role_title)s» was deleted successfully", project_role_title = t), 'success')
    return redirect(url_for('admin.project_role_index'))


@bp.route('/project_roles/permissions', methods=['GET', 'POST'])
def project_role_permissions():
    all_roles = db.session.scalars(sa.select(models.ProjectRole)).all()
    form = forms.get_project_role_permission_form(all_roles)()
    db.session.commit()
    if form.validate_on_submit():
        form.populate_permissions()
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit project role permissions")
        flash(_l("Permissions for project roles successfully updated"), 'success')
        return redirect(url_for('admin.project_role_index'))
    role_permissions = {}
    for o in get_all_project_objects():
        role_permissions[o] = {}
        for a in o.Meta.project_permission_actions.keys():
            role_permissions[o][a] = {}
            for r in all_roles:
                role_permissions[o][a][r] = getattr(form, 'role_' + str(r.id) + '____' + o.__name__ + '____' + a)
    ctx = DefaultEnvironment('project_role_permissions')()
    context = {'form': form, 'objs': get_all_project_objects(), 'roles': all_roles, 'role_permissions': role_permissions}
    return render_template('admin/role_permissions.html', **ctx, **context)