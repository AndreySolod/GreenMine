from app.controllers.admin import bp
from app import db, side_libraries, logger
import app.models as models
from app.helpers.general_helpers import objects_export, objects_import
from app.helpers.admin_helpers import DefaultEnvironment
from flask import url_for, render_template, redirect, abort, flash, request, send_file
import app.controllers.admin.issue_template_forms as issue_template_forms
from flask_login import current_user
import sqlalchemy as sa
from io import BytesIO
from flask_babel import lazy_gettext as _l
import json


@bp.route('/issues/templates/index')
def issue_template_index():
    templs = db.session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.archived == False)).all()
    ctx = DefaultEnvironment()()
    side_libraries.library_required('bootstrap_table')
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request all issue templates")
    return render_template('issue_templates/index.html', **ctx, templates=templs,
                           import_issue_templates=issue_template_forms.IssueTemplateImportForm())


@bp.route('/issues/templates/new', methods=["GET", "POST"])
def issue_template_new():
    form = issue_template_forms.IssueTemplateCreateForm()
    if form.validate_on_submit():
        templ = models.IssueTemplate()
        form.populate_obj(db.session, templ, current_user)
        db.session.add(templ)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new issue template #{templ.id}: '{templ.title}'")
        flash(_l("New Issue template successfully added"), "success")
        return redirect(url_for('admin.issue_template_show', template_id=templ.id))
    elif request.method == 'GET':
        form.load_default_data(db.session, models.IssueTemplate)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment()()
    context = {'form': form, "ckeditor_height": "100px"}
    return render_template('issue_templates/new.html', **ctx, **context)


@bp.route('/issues/templates/<template_id>/show')
def issue_template_show(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    template = db.get_or_404(models.IssueTemplate, template_id)
    ctx = DefaultEnvironment(template)()
    context = {'template': template}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request issue template #{template.id}")
    return render_template('issue_templates/show.html', **ctx, **context)


@bp.route('/issues/templates/<template_id>/edit', methods=["GET", "POST"])
def issue_template_edit(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    template = db.get_or_404(models.IssueTemplate, template_id)
    form = issue_template_forms.IssueTemplateEditForm(template)
    if form.validate_on_submit():
        form.populate_obj(db.session, template)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' update issue template #{template.id}: '{template.title}'")
        flash(_l("Issue template successfully updated"), 'success')
        return redirect(url_for('admin.issue_template_show', template_id=template.id))
    elif request.method == "GET":
        form.load_exist_value(template)
    ctx = DefaultEnvironment(template)()
    context = {'form': form, "ckeditor_height": "100px"}
    return render_template('issue_templates/new.html', **ctx, **context)


@bp.route('/issues/templates/<template_id>/delete', methods=["POST", "DELETE"])
def issue_template_delete(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    templ = db.get_or_404(models.IssueTemplate, template_id)
    t = templ.title
    db.session.delete(templ)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete issue template #{template_id}: '{t}'")
    flash(_l("Issue template successfully deleted"), 'success')
    return redirect(url_for('admin.issue_template_index'))


@bp.route('/issues/templates/export')
def issue_template_export():
    try:
        selected = request.args.get('selected')
        if not selected is None and not selected == '':
            selected_ids = list(map(int, selected.split(',')))
        else:
            selected_ids = []
    except (ValueError, TypeError):
        abort(400)
    issue_template_data = json.dumps(objects_export(db.session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.id.in_(selected_ids))).all()))
    params = {'as_attachment': True, 'download_name': 'Issue_templates.json'}
    buf = BytesIO()
    buf.write(issue_template_data.encode())
    buf.seek(0)
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request export issue templates")
    return send_file(buf, **params)


@bp.route('/issues/templates/import', methods=['POST'])
def issue_template_import():
    form = issue_template_forms.IssueTemplateImportForm()
    if form.validate_on_submit():
        file_parsed = objects_import(models.IssueTemplate, request.files.get(form.import_file.name).read().decode('utf8'),
                                     form.override_exist.data)
        if file_parsed:
            db.session.commit()
            logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' imported the issue templates")
            flash(_l("Import was completed successfully"))
        else:
            flash(_l("Errors when parsing file"))
    else:
        flash(_l("Errors when parsing file"))
    return redirect(url_for('admin.issue_template_index'))