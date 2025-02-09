from app import db, side_libraries, logger
from app.controllers.credentials import bp
from flask_login import login_required, current_user
from flask import request, render_template, url_for, redirect, flash, abort, jsonify
from app.models import Credential, Project
from app.helpers.general_helpers import get_or_404
from app.helpers.projects_helpers import get_default_environment
from app.helpers.credential_helpers import NameThatHash
import app.controllers.credentials.forms as forms
from flask_babel import lazy_gettext as _l
from app.helpers.roles import project_role_can_make_action, project_role_can_make_action_or_abort


@bp.route('/index')
@login_required
def credential_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to get list credentials with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = db.get_or_404(Project, project_id)
    project_role_can_make_action_or_abort(current_user, Credential(), 'index', project=project)
    creds = db.session.scalars(db.select(Credential).where(db.and_(Credential.project_id == project_id, Credential.archived == False, Credential.is_pentest_credentials == False))).all()
    ctx = get_default_environment(Credential(project=project), 'index')
    side_libraries.library_required('bootstrap_table')
    context = {'credentials': creds, 'project': project}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request all credentials on project #{project_id}")
    side_libraries.library_required('contextmenu')
    return render_template('credentials/index.html', **context, **ctx)


@bp.route('/pentest-index')
@login_required
def pentest_credential_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to get list credentials with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = db.get_or_404(Project, project_id)
    project_role_can_make_action_or_abort(current_user, Credential(), 'pentest_index', project=project)
    creds = db.session.scalars(db.select(Credential).where(db.and_(Credential.project_id == project_id, Credential.archived == False, Credential.is_pentest_credentials == True))).all()
    ctx = get_default_environment(Credential(project=project), 'pentest-index')
    context = {'credentials': creds}
    side_libraries.library_required('bootstrap_table')
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request all pentest credentials on project #{project_id}")
    side_libraries.library_required('contextmenu')
    return render_template('credentials/pentest-index.html', **context, **ctx)



@bp.route('/new', methods=["GET", "POST"])
@login_required
def credential_new():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to create new credential with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, Project, project_id)
    project_role_can_make_action_or_abort(current_user, Credential(), 'create', project=project)
    form = forms.CredentialCreateForm(project_id)
    if form.validate_on_submit():
        cred = Credential()
        form.populate_obj(db.session, cred, current_user)
        cred.project_id = project_id
        db.session.add(cred)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new credential #{cred.id}")
        flash(_l("Credential for «%(login)s» has been successfully added", login=cred.login), 'success')
        if form.submit_and_add_new.data:
            return redirect(url_for('credentials.credential_new', **request.args))
        if project_role_can_make_action(current_user, cred, 'show'):
            return redirect(url_for('credentials.credential_show', credential_id=cred.id))
        return redirect(url_for('credentials.credential_index', project_id=project_id))
    elif request.method == 'GET':
        form.load_default_data(db.session, Credential)
        form.load_data_from_json(request.args)
    ctx = get_default_environment(Credential(project=project), 'new')
    return render_template('credentials/new.html', form=form, **ctx)


@bp.route("/<credential_id>")
@bp.route("/<credential_id>/show")
@login_required
def credential_show(credential_id):
    try:
        credential_id = int(credential_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to get credential with non-integer credential_id {credential_id}")
        abort(404)
    cred = db.get_or_404(Credential, credential_id)
    project_role_can_make_action_or_abort(current_user, cred, 'show')
    ctx = get_default_environment(cred, 'show')
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('ckeditor')
    context = {'credential': cred,
               'edit_related_services': forms.EditRelatedServicesForm(cred)}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request credential #{cred.id}")
    return render_template('credentials/show.html', **context, **ctx)


@bp.route("/<credential_id>/edit", methods=["GET", "POST"])
@login_required
def credential_edit(credential_id):
    try:
        credential_id = int(credential_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to edit credential with non-integer credential_id {credential_id}")
        abort(400)
    cred = get_or_404(db.session, Credential, credential_id)
    project_role_can_make_action_or_abort(current_user, cred, 'update')
    form = forms.CredentialEditForm(cred.project_id)
    if form.validate_on_submit():
        form.populate_obj(db.session, cred)
        cred.updated_by_id = current_user.id
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit credential #{cred.id}")
        flash(_l('Credential #%(cred_id)s successfully changed', cred_id=credential_id), 'success')
        return redirect(url_for('credentials.credential_show', credential_id=cred.id))
    elif request.method == 'GET':
        form.load_exist_value(cred)
    ctx = get_default_environment(cred, 'edit')
    return render_template('credentials/edit.html', form=form, **ctx)


@bp.route("/<int:credential_id>/delete", methods=["POST"])
@login_required
def credential_delete(credential_id):
    cred = get_or_404(db.session, Credential, credential_id)
    project_role_can_make_action_or_abort(current_user, cred, 'delete')
    project_id = cred.project_id
    msg = _l("Credential #%(cred_id)s has been successfully deleted", cred_id=credential_id)
    db.session.delete(cred)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete credential #{credential_id}")
    flash(msg, 'success')
    return redirect(url_for('credentials.credential_index', project_id=project_id))


@bp.route('/gethashtype/<hash_value>')
@login_required
def get_hash_type(hash_value):
    hashes_list = NameThatHash().identify(hash_value)
    hashes_list.sort(key=lambda x: x.is_popular, reverse=True)
    if len(hashes_list) == 0:
        return jsonify({'default_hash': 0, 'anothers': []})
    fst = hashes_list[0]
    jhl = [i.to_send_dict() for i in hashes_list]
    return jsonify({'default_hash': fst.id, 'title': fst.title, 'anothers': jhl[1::]})
