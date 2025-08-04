from app.controllers.admin import bp
from app import db, logger, side_libraries
import app.models as models
import sqlalchemy as sa
from app.helpers.admin_helpers import DefaultEnvironment
from flask_login import current_user
from flask import url_for, render_template, redirect, flash, request, abort
import app.controllers.admin.credential_templates_forms as forms
from flask_babel import lazy_gettext as _l


@bp.route('/credentials/templates/index')
def credential_template_index():
    templs = db.session.scalars(sa.select(models.CredentialImportTemplate)).all()
    ctx = DefaultEnvironment()()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request all credential templates")
    side_libraries.library_required('bootstrap_table')
    return render_template('credential_import_templates/index.html', **ctx, templates=templs)


@bp.route('/credentials/templates/new', methods=["GET", "POST"])
def credential_template_new():
    form = forms.CredentialImportTemplateFormCreate()
    if form.validate_on_submit():
        templ = models.CredentialImportTemplate()
        form.populate_obj(db.session, templ, current_user)
        db.session.add(templ)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new credential import template #{templ.id}")
        flash(_l("New Credential import template successfully added"), "success")
        return redirect(url_for('admin.credential_template_show', template_id=templ.id))
    elif request.method == 'GET':
        form.load_default_data(db.session, models.CredentialImportTemplate)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment()()
    return render_template('credential_import_templates/new.html', **ctx, form=form)


@bp.route('/credentials/templates/<template_id>/show')
def credential_template_show(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    template = db.get_or_404(models.CredentialImportTemplate, template_id)
    ctx = DefaultEnvironment(template)()
    return render_template('credential_import_templates/show.html', **ctx, template=template)


@bp.route('/credentials/templates/<template_id>/edit', methods=["GET", "POST"])
def credential_template_edit(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    template = db.get_or_404(models.CredentialImportTemplate, template_id)
    form = forms.CredentialImportTemplateFormEdit(template)
    if form.validate_on_submit():
        form.populate_obj(db.session, template, current_user)
        db.session.add(template)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' update credential import template #{template.id}")
        flash(_l("Credential import template successfully updated"), "success")
        return redirect(url_for('admin.credential_template_show', template_id=template.id))
    elif request.method == 'GET':
        print('template:', template)
        print('template.static_hash_type:', template.static_hash_type)
        form.load_exist_value(template)
    ctx = DefaultEnvironment(template)()
    return render_template('credential_import_templates/edit.html', **ctx, form=form)


@bp.route('/credentials/templates/<template_id>/delete', methods=["POST"])
def credential_template_delete(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    templ = db.get_or_404(models.CredentialImportTemplate, template_id)
    db.session.delete(templ)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete credential import template template #{template_id}")
    flash(_l("Credential import template successfully deleted"), 'success')
    return redirect(url_for('admin.credential_template_index'))