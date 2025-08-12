from app import db, logger
import app.models as models
from app.controllers.projects import bp
import app.controllers.projects.forms as forms
from flask_login import current_user
import sqlalchemy as sa
import sqlalchemy.exc as exc
from flask import url_for, flash, redirect, abort, render_template, request
from app.helpers.projects_helpers import get_default_environment
from flask_babel import lazy_gettext as _l
from app.helpers.roles import project_role_can_make_action_or_abort


@bp.route('/<project_id>/additional_parameters/index')
def project_additional_parameter_index(project_id):
    try:
        project = db.get_or_404(models.Project, int(project_id))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to get project additional parameters with non-integer project_id: {project_id}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, project, 'show_additional_parameters')
    # Сперва проверяем, что все дополнительные параметры присутствуют в БД, если какой-то отсутствует - создаём
    all_additional_field = db.session.scalars(sa.select(models.ProjectAdditionalField)).all()
    all_groups = db.session.scalars(sa.select(models.ProjectAdditionalFieldGroup).order_by(models.ProjectAdditionalFieldGroup.order_number.asc())).all()
    for i in all_additional_field:
        project_field = db.session.scalars(sa.select(models.ProjectAdditionalFieldData).where(sa.and_(models.ProjectAdditionalFieldData.project_id == project.id,
                                                                                                        models.ProjectAdditionalFieldData.field_type_id == i.id))).first()
        if project_field is None:
            project_field = models.ProjectAdditionalFieldData(project_id=project_id, field_type_id=i.id)
            db.session.add(project_field)
    db.session.commit()
    # Теперь берём все поля, сгруппированные по ProjectAdditionalFieldGroup, и вместе с ними рендерим шаблон:
    fields = db.session.scalars(sa.select(models.ProjectAdditionalFieldData).join(models.ProjectAdditionalFieldData.field_type, isouter=True)
                                .join(models.ProjectAdditionalField.group, isouter=True).where(models.ProjectAdditionalFieldData.project_id == project.id)
                                .order_by(models.ProjectAdditionalFieldGroup.order_number.asc())).all()
    grouped_fields = {i: [] for i in all_groups}
    for f in fields:
        grouped_fields[f.field_type.group].append(f)
    ctx = get_default_environment(project, 'project_additional_parameters_index')
    context = {'groups': all_groups, 'grouped_fields': grouped_fields, 'project': project}
    return render_template('project_additional_parameters/index.html', **ctx, **context)


@bp.route('/<project_id>/additional_parameters/edit', methods=['GET', 'POST'])
def project_additional_parameter_edit(project_id):
    try:
        project = db.session.get(models.Project, int(project_id))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to edit project additional parameters with non-integer project_id: {project_id}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, project, 'edit_additional_parameters')
    # Сперва проверяем, что все дополнительные параметры присутствуют в БД, если какой-то отсутствует - создаём
    all_additional_field = db.session.scalars(sa.select(models.ProjectAdditionalField)).all()
    for i in all_additional_field:
        project_field = db.session.scalars(sa.select(models.ProjectAdditionalFieldData).where(sa.and_(models.ProjectAdditionalFieldData.project_id == project.id,
                                                                                                        models.ProjectAdditionalFieldData.field_type_id == i.id))).first()
        if project_field is None:
            project_field = models.ProjectAdditionalFieldData(project_id=project_id, field_type_id=i.id)
            db.session.add(project_field)
    db.session.commit()
    # Теперь создаём форму для обработки параметров
    form = forms.get_additional_parameters_form(project)()
    if form.validate_on_submit():
        form.populate_parameters(project)
        db.session.commit()
        flash(_l("Additional parameters are successfully updated"), 'success')
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' update additional parameters on project #{project.id}")
        return redirect(url_for('projects.project_additional_parameter_index', project_id=project.id))
    elif request.method == 'GET':
        form.load_exist_value(project)
    ctx = get_default_environment(project, 'project_additional_parameter_edit')
    # Отдельно берём все дополнительные поля для данного объекта
    all_groups = db.session.scalars(sa.select(models.ProjectAdditionalFieldGroup).order_by(models.ProjectAdditionalFieldGroup.order_number.asc())).all()
    fields = db.session.scalars(sa.select(models.ProjectAdditionalFieldData).join(models.ProjectAdditionalFieldData.field_type, isouter=True)
                                .join(models.ProjectAdditionalField.group, isouter=True).where(models.ProjectAdditionalFieldData.project_id == project.id)
                                .order_by(models.ProjectAdditionalFieldGroup.order_number.asc())).all()
    grouped_fields = {i: [] for i in all_groups}
    for f in fields:
        grouped_fields[f.field_type.group].append((f, getattr(form, 'param_' + str(f.id))))
    context = {'grouped_fields': grouped_fields, 'groups': all_groups, 'form': form, 'ckeditor_height': '200px'}
    return render_template('project_additional_parameters/edit.html', **ctx, **context)