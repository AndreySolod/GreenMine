from app import db, side_libraries, logger
from flask import render_template, flash, redirect, url_for, abort, request, send_file
from flask_login import current_user
from app.controllers.admin import bp
from app.helpers.admin_helpers import DefaultEnvironment
from app.helpers.general_helpers import objects_export, objects_import
import app.models as models
import sqlalchemy as sa
import sqlalchemy.exc as exc
import json
from io import BytesIO
import app.controllers.admin.task_templates_forms as forms
from flask_babel import lazy_gettext as _l


@bp.route('/tasks/templates/index')
def task_template_index():
    templs = db.session.scalars(sa.select(models.ProjectTaskTemplate)).all()
    trackers = {i: t for i, t in db.session.execute(sa.select(models.ProjectTaskTracker.id, models.ProjectTaskTracker.title))}
    priorities = {i: t for i, t in db.session.execute(sa.select(models.ProjectTaskPriority.id, models.ProjectTaskPriority.title))}
    filters = {'ProjectTaskTracker': json.dumps(trackers), 'ProjectTaskPriority': json.dumps(priorities)}
    ctx = DefaultEnvironment()()
    side_libraries.library_required('bootstrap_table')
    context = {'templates': templs, 'filters': filters, 'import_task_templates': forms.TaskTemplateImportForm()}
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
    ctx = DefaultEnvironment(templ)()
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
    ctx = DefaultEnvironment()()
    context = {'form': form, 'need_ckeditor': True}
    return render_template('task_templates/new.html', **ctx, **context)



@bp.route('/tasks/templates/<template_id>/edit', methods=['GET', 'POST'])
def task_template_edit(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    template = db.get_or_404(models.ProjectTaskTemplate, template_id)
    form = forms.TaskTemplateEditForm(template)
    if form.validate_on_submit():
        form.populate_obj(db.session, template)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit project task template #{template.id}: '{template.title}'")
        flash(_l("Task template successfully updated"), 'success')
        return redirect(url_for('admin.task_template_show', template_id=template.id))
    elif request.method == "GET":
        form.load_exist_value(template)
    ctx = DefaultEnvironment(template)()
    context = {'form': form, 'need_ckeditor': True}
    return render_template('task_templates/new.html', **ctx, **context)

    


@bp.route('/tasks/templates/<template_id>/delete', methods=['POST'])
def task_template_delete(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    templ = db.get_or_404(models.ProjectTaskTemplate, template_id)
    i, t = templ.id, templ.title
    db.session.delete(templ)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete project task template #{i}: '{t}'")
    flash(_l("Task template successfully deleted"), 'success')
    return redirect(url_for('admin.task_template_index'))


@bp.route('/tasks/templates/export')
def task_template_export():
    try:
        selected = request.args.get('selected')
        if not selected is None and not selected == '':
            selected_ids = list(map(int, selected.split(',')))
        else:
            selected_ids = []
    except (ValueError, TypeError):
        abort(400)
    task_template_data = json.dumps(objects_export(db.session.scalars(sa.select(models.ProjectTaskTemplate).where(models.ProjectTaskTemplate.id.in_(selected_ids))).all()))
    params = {'as_attachment': True, 'download_name': 'Project_task_templates.json'}
    buf = BytesIO()
    buf.write(task_template_data.encode())
    buf.seek(0)
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request export task templates")
    return send_file(buf, **params)


@bp.route('/tasks/templates/import', methods=['POST'])
def task_template_import():
    form = forms.TaskTemplateImportForm()
    if form.validate_on_submit():
        file_parsed = objects_import(models.ProjectTaskTemplate, request.files.get(form.import_file.name).read().decode('utf8'),
                                     form.override_exist.data)
        if file_parsed:
            db.session.commit()
            logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' imported the task templates")
            flash(_l("Import was completed successfully"), 'success')
        else:
            flash(_l("Errors when parsing file"), 'error')
    else:
        flash(_l("Errors when parsing file"), 'error')
    return redirect(url_for('admin.task_template_index'))