import json
from flask import render_template, flash, redirect, url_for, request, abort, jsonify
from flask_login import current_user
from app.controllers.issues import bp
from app import db, side_libraries, logger
from app.models import Issue, Project, IssueStatus, IssueTemplate
from app.helpers.general_helpers import get_or_404, get_bootstrap_table_json_data
from app.helpers.projects_helpers import get_default_environment
import app.controllers.issues.forms as forms
from sqlalchemy import exc
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_babel import lazy_gettext as _l
from app.helpers.roles import project_role_can_make_action_or_abort, project_role_can_make_action


@bp.route('/index')
def issue_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index all issue with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = db.get_or_404(Project, project_id)
    project_role_can_make_action_or_abort(current_user, Issue(), 'index', project=project)
    issue_statuses = {i: t for i, t in db.session.execute(sa.select(IssueStatus.id, IssueStatus.title))}
    filters = {'IssueStatus': json.dumps(issue_statuses)}
    ctx = get_default_environment(Issue(project=project), 'index')
    side_libraries.library_required('bootstrap_table')
    context = {'project': project, 'filters': filters, 'Issue': Issue}
    return render_template('issues/index.html', **context, **ctx)


@bp.route('/index-data')
def issue_data_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index all issue with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, Issue(), 'index', project_id=project_id)
    additional_params = {'obj': Issue, 'column_index': ['id', 'title', 'description', 'status.id-select', 'cvss', 'cve'],
                         'base_select': lambda x: x.where(db.and_(Issue.project_id==project_id, Issue.archived == False))}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request all issues on project #{project_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/exist-index')
def exist_issue_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request exist issue index with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = db.get_or_404(Project, project_id)
    project_role_can_make_action_or_abort(current_user, Issue(), 'index', project=project)
    issue_statuses = {i: t for i, t in db.session.execute(sa.select(IssueStatus.id, IssueStatus.title))}
    filters = {'IssueStatus': json.dumps(issue_statuses)}
    ctx = get_default_environment(Issue(project=project), 'exist-index')
    side_libraries.library_required('bootstrap_table')
    context = {'project': project, 'filters': filters, 'Issue': Issue}
    return render_template('issues/exist-index.html', **context, **ctx)


@bp.route('/exist-index-data')
def exist_issue_data_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request exist issue index with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, Issue(), 'index', project_id=project_id)
    aliased = so.aliased(IssueStatus)
    additional_params = {'obj': Issue, 'column_index': ['id', 'title', 'description', 'status.id-select', 'cvss', 'cve'],
                         'base_select': lambda x: x.join(Issue.status.of_type(aliased)).where(db.and_(Issue.project_id==project_id, Issue.archived == False, aliased.string_slug != 'fixed'))}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request exist issues on project #{project_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/positive-index')
def positive_issue_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request positive index issue with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = db.get_or_404(Project, project_id)
    project_role_can_make_action_or_abort(current_user, Issue(), 'index', project=project)
    issue_statuses = {i: t for i, t in db.session.execute(sa.select(IssueStatus.id, IssueStatus.title))}
    filters = {'IssueStatus': json.dumps(issue_statuses)}
    ctx = get_default_environment(Issue(project=project), 'positive-index')
    side_libraries.library_required('bootstrap_table')
    context = {'project': project, 'filters': filters, 'Issue': Issue}
    return render_template('issues/positive-index.html', **context, **ctx)


@bp.route('/positive-index-data')
def positive_issue_data_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request positive index data issue with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, Issue(), 'index', project_id=project_id)
    aliased = so.aliased(IssueStatus)
    additional_params = {'obj': Issue, 'column_index': ['id', 'title', 'description', 'status.id-select', 'cvss', 'cve'],
                         'base_select': lambda x: x.join(Issue.status.of_type(aliased)).where(db.and_(Issue.project_id==project_id, Issue.archived==False, aliased.string_slug == 'fixed'))}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request positive issues on project #{project_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/new', methods=['GET', 'POST'])
def issue_new():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request create issue with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, Project, project_id)
    project_role_can_make_action_or_abort(current_user, Issue(), 'create', project=project)
    form = forms.IssueCreateForm(project_id)
    if form.validate_on_submit():
        issue = Issue()
        form.populate_obj(db.session, issue, current_user)
        issue.project_id = project_id
        db.session.add(issue)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new issue #{issue.id}")
        flash(_l("Issue #%(issue_id)s has been successfully added", issue_id=issue.id), 'success')
        if form.submit_and_add_new.data:
            return redirect(url_for('issues.issue_new', **request.args))
        if project_role_can_make_action(current_user, issue, 'show'):
            return redirect(url_for('issues.issue_show', issue_id=issue.id))
        return redirect(url_for('issues.issue_index', project_id=project_id))
    elif request.method == 'GET':
        form.load_default_data(db.session, Issue)
        form.load_data_from_json(request.args)
    patterns = db.session.scalars(sa.select(IssueTemplate).where(IssueTemplate.archived == False)).all()
    ctx = get_default_environment(Issue(project=project), 'new')
    context = {'form': form, 'ckeditor_height': '100px', 'patterns': patterns}
    return render_template('issues/new.html', **context, **ctx)


@bp.route('/data-by-template/<template_id>')
def issue_data_by_template(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request issue template with non-integer id {template_id}")
        abort(400)
    try:
        templ = db.session.scalars(sa.select(IssueTemplate).where(IssueTemplate.id==template_id)).one()
    except (exc.NoResultFound, exc.MultipleResultsFound):
        abort(404)
    res = {"title": templ.issue_title,
           "description": templ.issue_description,
           "fix": templ.issue_fix,
           "technical": templ.issue_technical,
           "riscs": templ.issue_riscs,
           "references": templ.issue_references,
           "cvss": templ.issue_cvss,
           'slug': templ.string_slug}
    if templ.issue_cve_id is None:
        res["cve_id"] = 0
    else:
        res["cve_id"] = templ.issue_cve_id
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request issue template #{template_id}")
    return jsonify(res)


@bp.route('/<issue_id>')
@bp.route('/<issue_id>/show')
def issue_show(issue_id):
    try:
        issue_id = int(issue_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request issue with non-integer id {issue_id}")
        abort(404)
    issue = db.get_or_404(Issue, issue_id)
    project_role_can_make_action_or_abort(current_user, issue, 'show')
    ctx = get_default_environment(issue, 'show')
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('ckeditor')
    context = {'issue': issue, 'edit_related_objects': forms.EditRelatedObjectsForm(issue)}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request issue #{issue.id}")
    return render_template('issues/show.html', **context, **ctx)


@bp.route('/<int:issue_id>/edit', methods=['GET', 'POST'])
def issue_edit(issue_id):
    issue = get_or_404(db.session, Issue, issue_id)
    project_role_can_make_action_or_abort(current_user, issue, 'update')
    form = forms.IssueEditForm(issue.project_id)
    if form.validate_on_submit():
        form.populate_obj(db.session, issue)
        issue.updated_by_id = current_user.id
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit issue #{issue.id}")
        flash(_l("Issue #%(issue_id)s successfully changed", issue_id=issue_id), 'success')
        return redirect(url_for('issues.issue_show', issue_id=issue.id))
    elif request.method == 'GET':
        form.load_exist_value(issue)
    ctx = get_default_environment(issue, 'edit')
    context = {'form': form, 'ckeditor_height': '100px'}
    return render_template('issues/edit.html', **context, **ctx)


@bp.route('/<int:issue_id>/delete', methods=["POST"])
def issue_delete(issue_id):
    issue = get_or_404(db.session, Issue, issue_id)
    project_role_can_make_action_or_abort(current_user, issue, 'delete')
    project_id = issue.project_id
    msg = _l("Issue #%(issue_id)s has been successfully deleted", issue_id=issue_id)
    db.session.delete(issue)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete issue #{issue_id}")
    flash(msg, 'success')
    return redirect(url_for('issues.issue_index', project_id=project_id))


@bp.route('/carousel')
def issue_carousel():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request carousel with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, Project, project_id)
    project_role_can_make_action_or_abort(current_user, Issue(), 'index', project=project)
    confirmed_status = db.session.scalars(sa.select(IssueStatus).where(IssueStatus.string_slug == 'confirmed')).one()
    issues = db.session.scalars(sa.select(Issue).where(Issue.project_id==project_id, Issue.archived==False, Issue.status_id == confirmed_status.id).order_by(sa.desc(Issue.cvss))).all()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request carousel for project #{project_id}")
    ctx = get_default_environment(Issue(project=project), 'carousel')
    context = {'issues': issues}
    return render_template('issues/carousel.html', **context, **ctx)