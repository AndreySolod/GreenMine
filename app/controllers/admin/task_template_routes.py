from app import db, side_libraries, logger
from flask import render_template, flash, redirect, url_for, abort, request
from flask_login import current_user
from app.controllers.admin import bp
from app.helpers.admin_helpers import DefaultEnvironment
from app.helpers.general_helpers import get_or_404
import app.models as models
import sqlalchemy as sa
import sqlalchemy.exc as exc
import json
import app.controllers.admin.task_templates_forms as forms
from flask_babel import lazy_gettext as _l


@bp.route('/tasks/templates/index')
def task_template_index():
    templs = db.session.scalars(sa.select(models.ProjectTaskTemplate)).all()
    trackers = {i: t for i, t in db.session.execute(sa.select(models.ProjectTaskTracker.id, models.ProjectTaskTracker.title))}
    priorities = {i: t for i, t in db.session.execute(sa.select(models.ProjectTaskPriority.id, models.ProjectTaskPriority.title))}
    filters = {'ProjectTaskTracker': json.dumps(trackers), 'ProjectTaskPriority': json.dumps(priorities)}
    ctx = DefaultEnvironment('task_template_index')()
    side_libraries.library_required('bootstrap_table')
    context = {'templates': templs, 'filters': filters}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request all project task templates")
    return render_template('task_templates/index.html', **ctx, **context)


@bp.route('/tasks/templates/<template_id>/show')
def task_template_show(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    try:
        templ = db.session.scalars(sa.select(models.ProjectTaskTemplate).where(models.ProjectTaskTemplate.id == template_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    ctx = DefaultEnvironment('task_template_show', templ)()
    context = {'template': templ}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request project task template #{templ.id}")
    return render_template('task_templates/show.html', **ctx, **context)


@bp.route('/tasks/templates/new', methods=['GET', 'POST'])
def task_template_new():
    form = forms.TaskTemplateCreateForm()
    if form.validate_on_submit():
        templ = models.ProjectTaskTemplate()
        form.populate_obj(db.session, templ, current_user)
        db.session.add(templ)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new task template #{templ.id}: '{templ.title}'")
        flash(_l("New task template created successfully"), 'success')
        return redirect(url_for('admin.task_template_show', template_id=templ.id))
    elif request.method == 'GET':
        form.load_default_data(db.session, models.ProjectTaskTemplate)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment('task_template_new')()
    context = {'form': form, 'need_ckeditor': True}
    return render_template('task_templates/new.html', **ctx, **context)



@bp.route('/tasks/templates/<template_id>/edit', methods=['GET', 'POST'])
def task_template_edit(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    templ = get_or_404(db.session, models.ProjectTaskTemplate, template_id)
    form = forms.TaskTemplateEditForm()
    if form.validate_on_submit():
        form.populate_obj(db.session, templ)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit project task template #{templ.id}: '{templ.title}'")
        flash(_l("Task template successfully updated"), 'success')
        return redirect(url_for('admin.task_template_show', template_id=templ.id))
    elif request.method == "GET":
        form.load_exist_value(templ)
    ctx = DefaultEnvironment('task_template_edit', templ)()
    context = {'form': form, 'need_ckeditor': True}
    return render_template('task_templates/new.html', **ctx, **context)

    


@bp.route('/tasks/templates/<template_id>/delete', methods=['POST'])
def task_template_delete(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    templ = get_or_404(db.session, models.ProjectTaskTemplate, template_id)
    i, t = templ.id, templ.title
    db.session.delete(templ)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete project task template #{i}: '{t}'")
    flash(_l("Task template successfully deleted"), 'success')
    return redirect(url_for('admin.task_template_index'))