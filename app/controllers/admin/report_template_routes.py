from app import db, side_libraries
from flask import render_template, flash, redirect, url_for, abort, request
from flask_login import current_user
from app.controllers.admin import bp
from app.helpers.admin_helpers import DefaultEnvironment
from app.helpers.general_helpers import get_or_404
import app.models as models
import sqlalchemy as sa
import sqlalchemy.exc as exc
import json
import app.controllers.admin.report_template_forms as forms
from flask_babel import lazy_gettext as _l
from app import logger


@bp.route('/report_templates/index')
def report_template_index():
    templates = db.session.scalars(sa.select(models.ProjectReportTemplate)).all()
    ctx = DefaultEnvironment()()
    side_libraries.library_required('bootstrap_table')
    return render_template('report_templates/admin_index.html', **ctx, templates=templates)


@bp.route('/report_templates/new', methods=['GET', 'POST'])
def report_template_new():
    form = forms.ReportTemplateCreateForm()
    if form.validate_on_submit():
        templ = models.ProjectReportTemplate()
        db.session.add(templ)
        form.populate_obj(db.session, templ, current_user)
        templ.description = templ.description.replace('\n', ' ').replace('\r', ' ')
        templ_pattern = models.FileData(title=form.template.data.filename, description=str(_l("Template for Report Templates %(templ_name)s", templ_name=form.title.data)))
        templ_pattern.extension = form.template.data.filename.split('.')[-1]
        templ_pattern.data = form.template.data.read()
        templ.template = templ_pattern
        db.session.add(templ_pattern)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create a new report template #{templ.id}: '{templ.title}'")
        flash(_l("New report template successfully created!"), 'success')
        return redirect(url_for('admin.report_template_show', template_id=templ.id))
    elif request.method == 'GET':
        form.load_default_data(db.session, models.ProjectReportTemplate)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment()()
    return render_template('report_templates/admin_new.html', **ctx, form=form)


@bp.route('/report_templates/<template_id>/show')
def report_template_show(template_id: str):
    try:
        template_id = int(template_id)
        template = db.session.scalars(sa.select(models.ProjectReportTemplate).where(models.ProjectReportTemplate.id == template_id)).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        abort(400)
    ctx = DefaultEnvironment(template)()
    context = {'template': template}
    return render_template('report_templates/admin_show.html', **ctx, **context)


@bp.route('/report_templates/<template_id>/edit', methods=['GET', 'POST'])
def report_template_edit(template_id: str):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    templ = get_or_404(db.session, models.ProjectReportTemplate, template_id)
    form = forms.ReportTemplateEditForm()
    if form.validate_on_submit():
        form.populate_obj(db.session, templ, current_user)
        templ.description = templ.description.replace('\n', ' ').replace('\r', ' ')
        if form.template.data:
            db.session.delete(templ.template)
            templ_pattern = models.FileData(title=form.template.data.filename, description=_l("Template for Report Templates %(templ_name)s", templ_name=form.title.data))
            templ_pattern.extension = form.template.data.filename.split('.')[-1]
            templ_pattern.data = form.template.data.read()
            templ.template = templ_pattern
            db.session.add(templ_pattern)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' update report template #{templ.id}: '{templ.title}'")
        flash(_l("Report template #%(templ_id)s successfully updated!", templ_id=templ.id), 'success')
        return redirect(url_for('admin.report_template_show', template_id=templ.id))
    elif request.method == 'GET':
        form.load_exist_value(templ)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment(templ)()
    return render_template('report_templates/admin_edit.html', **ctx, form=form)


@bp.route('/report_templates/<template_id>/delete', methods=['POST', 'DELETE'])
def report_template_delete(template_id: str):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    templ = db.get_or_404(models.ProjectReportTemplate, template_id)
    db.session.delete(templ.template)
    db.session.delete(templ)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete report template #{templ.id}")
    flash(_l("Report templates #%(templ_id)s successfully deleted!", templ_id=template_id), 'success')
    return redirect(url_for('admin.report_template_index'))