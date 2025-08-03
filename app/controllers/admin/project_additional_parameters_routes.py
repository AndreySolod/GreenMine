from app import db, side_libraries, logger
import app.models as models
import sqlalchemy as sa
from app.helpers.admin_helpers import DefaultEnvironment
from app.controllers.admin import bp
from flask import url_for, flash, abort, redirect, render_template, request, jsonify
import app.controllers.admin.project_additional_parameters_forms as forms
from flask_babel import lazy_gettext as _l
from flask_login import current_user
from app.helpers.general_helpers import find_data_by_request_params


@bp.route('/project-parameters/index')
def project_additional_parameters_index():
    param_groups = db.session.scalars(sa.select(models.ProjectAdditionalFieldGroup).order_by(models.ProjectAdditionalFieldGroup.order_number.asc())).all()
    ctx = DefaultEnvironment('project_additional_parameters_index')()
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('contextmenu')
    return render_template('project_additional_parameters/admin_index.html', **ctx, param_groups=param_groups)


@bp.route('/project-parameters/<group_id>/index-by-group')
def project_additional_parameters_index_data(group_id):
    try:
        group_id = int(group_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to get project parameter data with non-integer group_id: {group_id}")
        abort(400)
    group = db.get_or_404(models.ProjectAdditionalFieldGroup, group_id)
    sql, sql_count = find_data_by_request_params(models.ProjectAdditionalField, request, ['id', 'string_slug', 'title', 'help_text', 'description', 'field_type'])
    sql = sql.where(models.ProjectAdditionalField.group_id == group_id)
    sql_count = sql_count.where(models.ProjectAdditionalField.group_id == group_id)
    rows = []
    for i in db.session.scalars(sql).all():
        row = {'id': i.id, 'string_slug': i.string_slug, 'title': i.title, 'help_text': i.help_text, 'description': i.description, 'field_type': str(i.get_name_by_field_type())}
        rows.append(row)
    return jsonify({'total': db.session.scalars(sql_count).one(), 'rows': rows})


@bp.route('/project-parameters/new', methods=["GET", "POST"])
def project_additional_parameters_new():
    form = forms.ProjectAdditionalParameterCreateForm()
    if form.validate_on_submit():
        additional_field = models.ProjectAdditionalField()
        db.session.add(additional_field)
        form.populate_obj(db.session, additional_field, current_user)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create a new project parameter #{additional_field.id}")
        flash(_l("Additional parameters successfully created!"), 'success')
        return redirect(url_for('admin.project_additional_parameters_index'))
    elif request.method == 'GET':
        form.load_default_data(db.session, models.ProjectAdditionalField)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment('project_additional_parameters_new')()
    return render_template('project_additional_parameters/admin_new.html', **ctx, form=form)


@bp.route('/project-parameters/<parameter_id>/edit', methods=["GET", "POST"])
def project_additional_parameters_edit(parameter_id):
    try:
        param = db.get_or_404(models.ProjectAdditionalField, int(parameter_id))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to edit project parameter data with non-integer parameter_id: {parameter_id}")
        abort(400)
    form = forms.ProjectAdditionalParameterEditForm(param)
    if form.validate_on_submit():
        form.populate_obj(db.session, param)
        db.session.add(param)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit project additional parameter #{param.id}")
        flash(_l("Additional parameter successfully updated!"), 'success')
        return redirect(url_for('admin.project_additional_parameters_index'))
    elif request.method == 'GET':
        form.load_exist_value(param)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment('project_additional_parameters_edit', param)()
    return render_template('project_additional_parameters/admin_edit.html', **ctx, form=form)


@bp.route('/project-parameters/<parameter_id>/delete', methods=["POST"])
def project_additional_parameter_delete(parameter_id):
    try:
        param = db.get_or_404(models.ProjectAdditionalField, int(parameter_id))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to delete project parameter data with non-integer parameter_id: {parameter_id}")
        abort(400)
    db.session.delete(param)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete project parameter #{parameter_id}")
    flash(_l("Project additional parameter #%(param_id)s successfully deleted!", param_id=parameter_id), 'success')
    return redirect(url_for('admin.project_additional_parameters_index'))