from app import db, side_libraries, logger
from app.helpers.roles import project_role_can_make_action_or_abort, project_role_can_make_action
from app.controllers.research_events import bp
from app.helpers.projects_helpers import get_default_environment
from flask import url_for, flash, redirect, abort, request, render_template
import sqlalchemy as sa
from flask_login import current_user
import app.models as models
import app.controllers.research_events.forms as forms
from flask_babel import lazy_gettext as _l
import json


@bp.route('/research-events/index')
def researcher_event_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request research events index with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = db.get_or_404(models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.PentestResearchEvent(), 'index', project=project)
    side_libraries.library_required("bootstrap_table")
    events = db.session.scalars(sa.select(models.PentestResearchEvent).where(models.PentestResearchEvent.project_id == project_id)).all()
    ctx = get_default_environment(models.PentestResearchEvent(project=project), 'index')
    context = {'events': events}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request research event index on project #{project.id}")
    return render_template("research_events/pentest-index.html", **ctx, **context)


@bp.route('/research-events/new', methods=["GET", "POST"])
def researcher_event_new():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request create researcher events with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = db.get_or_404(models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.PentestResearchEvent(), 'create', project=project)
    form = forms.PentestResearchEventCreateForm(project)
    if form.validate_on_submit():
        pre = models.PentestResearchEvent(project=project)
        form.populate_obj(db.session, pre, current_user)
        db.session.add(pre)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new research event #{pre.id}")
        flash(_l("New research event successfully added!"), 'success')
        if project_role_can_make_action(current_user, pre, 'show'):
            return redirect(url_for('pentest_events.researcher_event_show', event_id=pre.id))
        return redirect(url_for('pentest_events.researcher_event_index', project_id=project.id))
    elif request.method == 'GET':
        form.load_default_data(db.session, models.PentestResearchEvent)
        form.load_data_from_json(request.args)
    ctx = get_default_environment(models.PentestResearchEvent(project=project), 'new')
    context = {'form': form, 'project': project, 'ckeditor_height': '200px'}
    return render_template('research_events/pentest-new.html', **ctx, **context)


@bp.route('/research-events/<event_id>/show')
def researcher_event_show(event_id):
    try:
        event_id = int(event_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request show research event with non-integer event_id: {event_id}")
        abort(400)
    event = db.get_or_404(models.PentestResearchEvent, event_id)
    project_role_can_make_action_or_abort(current_user, event, 'show')
    ctx = get_default_environment(event, 'show')
    side_libraries.library_required('bootstrap_table')
    return render_template('research_events/pentest-show.html', **ctx, event=event)


@bp.route('/researcher-events/<event_id>/edit', methods=["GET", "POST"])
def researcher_event_edit(event_id):
    try:
        event_id = int(event_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request edit research event with non-integer event_id: {event_id}")
        abort(400)
    event = db.get_or_404(models.PentestResearchEvent, event_id)
    project_role_can_make_action_or_abort(current_user, event, 'update')
    form = forms.PentestResearchEventEditForm(event.project, event)
    if form.validate_on_submit():
        form.populate_obj(db.session, event, current_user)
        event.updated_by = current_user
        db.session.add(event)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit research event #{event.id}")
        flash(_l("Research event #%(event_id)s successfully updated!", event_id=event.id), 'success')
        if project_role_can_make_action(current_user, event, 'show'):
            return redirect(url_for('pentest_events.researcher_event_show', event_id=event.id))
        return redirect(url_for('pentest_events.researcher_event_index', project_id=event.project_id))
    elif request.method == 'GET':
        form.load_exist_value(event)
        form.load_data_from_json(request.args)
    ctx = get_default_environment(event, 'edit')
    context = {'form': form}
    return render_template('research_events/pentest-edit.html', **ctx, **context)


@bp.route('/researcher-events/<event_id>/delete', methods=["POST"])
def researcher_event_delete(event_id):
    try:
        event_id = int(event_id)
    except (ValueError, TypeError):
        abort(400)
    event = db.get_or_404(models.PentestResearchEvent, event_id)
    project_role_can_make_action_or_abort(current_user, event, 'delete')
    project_id = event.project_id
    db.session.delete(event)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete research event #{event_id}")
    flash(_l("Research event #%(event_id)s successfully deleted!",  event_id=event_id), 'success')
    return redirect(url_for('pentest_events.researcher_event_index', project_id=project_id))


@bp.route('detection-event/index')
def organization_detection_event_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request organization detection events index with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = db.get_or_404(models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.PentestOrganizationDetectionEvent(), 'index', project=project)
    side_libraries.library_required("bootstrap_table")
    events = db.session.scalars(sa.select(models.PentestOrganizationDetectionEvent).where(models.PentestOrganizationDetectionEvent.project_id == project_id)).all()
    ctx = get_default_environment(models.PentestOrganizationDetectionEvent(project=project), 'index')
    context = {'events': events}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request research event index on project #{project.id}")
    return render_template("research_events/organization-detection-index.html", **ctx, **context)


@bp.route('/detection-events/new', methods=["GET", "POST"])
def organization_detection_event_new():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request create organization detection event with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = db.get_or_404(models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.PentestOrganizationDetectionEvent(), 'create', project=project)
    form = forms.PentestOrganizationDetectionEventCreateForm(project)
    if form.validate_on_submit():
        pre = models.PentestOrganizationDetectionEvent(project=project)
        form.populate_obj(db.session, pre, current_user)
        db.session.add(pre)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new Organization detection event event #{pre.id}")
        flash(_l("New detection event successfully added!"), 'success')
        if project_role_can_make_action(current_user, pre, 'show'):
            return redirect(url_for('pentest_events.organization_detection_event_show', event_id=pre.id))
        return redirect(url_for('pentest_events.organization_detection_event_index', project_id=project.id))
    elif request.method == 'GET':
        form.load_default_data(db.session, models.PentestOrganizationDetectionEvent)
        form.load_data_from_json(request.args)
    ctx = get_default_environment(models.PentestOrganizationDetectionEvent(project=project), 'new')
    context = {'form': form, 'project': project}
    return render_template('research_events/organization-detection-new.html', **ctx, **context)


@bp.route('/detection-events/<event_id>/show')
def organization_detection_event_show(event_id):
    try:
        event_id = int(event_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request show organization detection event with non-integer event_id: {event_id}")
        abort(400)
    event = db.get_or_404(models.PentestOrganizationDetectionEvent, event_id)
    project_role_can_make_action_or_abort(current_user, event, 'show')
    ctx = get_default_environment(event, 'show')
    return render_template('research_events/organization-detection-show.html', **ctx, event=event)


@bp.route('/detection-events/<event_id>/edit', methods=["GET", "POST"])
def organization_detection_event_edit(event_id):
    try:
        event_id = int(event_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request edit organization detection event with non-integer event_id: {event_id}")
        abort(400)
    event = db.get_or_404(models.PentestOrganizationDetectionEvent, event_id)
    project_role_can_make_action_or_abort(current_user, event, 'update')
    form = forms.PentestOrganizationDetectionEventEditForm(event.project)
    if form.validate_on_submit():
        form.populate_obj(db.session, event, current_user)
        event.updated_by = current_user
        db.session.add(event)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit organization detectio event #{event.id}")
        flash(_l("Detection event #%(event_id)s successfully updated!", event_id=event.id), 'success')
        if project_role_can_make_action(current_user, event, 'show'):
            return redirect(url_for('pentest_events.organization_detection_event_show', event_id=event.id))
        return redirect(url_for('pentest_events.organization_detection_event_index', project_id=event.project_id))
    elif request.method == 'GET':
        form.load_exist_value(event)
        form.load_data_from_json(request.args)
    ctx = get_default_environment(event, 'edit')
    context = {'form': form}
    return render_template('research_events/organization-detection-edit.html', **ctx, **context)


@bp.route('/detection-event/<event_id>/delete', methods=["POST"])
def organization_detection_event_delete(event_id):
    try:
        event_id = int(event_id)
    except (ValueError, TypeError):
        abort(400)
    event = db.get_or_404(models.PentestOrganizationDetectionEvent, event_id)
    project_role_can_make_action_or_abort(current_user, event, 'delete')
    project_id = event.project_id
    db.session.delete(event)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete organization detection event #{event_id}")
    flash(_l("Organization detection event #%(event_id)s successfully deleted!",  event_id=event_id), 'success')
    return redirect(url_for('pentest_events.organization_detection_event_index', project_id=project_id))


@bp.route('/all-events/timeline')
def all_events_timeline():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request event timeline with non-integer project_id: {request.args.get('project_id')}")
        abort(400)
    project = db.get_or_404(models.Project, project_id)
    if not project_role_can_make_action(current_user, models.PentestResearchEvent(), 'show_timeline', project=project) and not (project_role_can_make_action(current_user, models.PentestOrganizationDetectionEvent(), 'show_timeline', project=project)):
        abort(401)
    event_list = []
    if project_role_can_make_action(current_user, models.PentestResearchEvent(), 'show_timeline', project=project):
        research_events = db.session.scalars(sa.select(models.PentestResearchEvent).where(models.PentestResearchEvent.project_id == project_id)).all()
        for e in research_events:
            event_list.append((e, 0))
    if project_role_can_make_action(current_user, models.PentestOrganizationDetectionEvent(), 'show_timeline', project=project):
        ode = db.session.scalars(sa.select(models.PentestOrganizationDetectionEvent).where(models.PentestOrganizationDetectionEvent.project_id == project_id)).all()
        for e in ode:
            event_list.append((e, 1))
    event_list.sort(key=lambda x: x[0].timestamp)
    ctx = get_default_environment(models.PentestResearchEvent(project=project), 'timeline')
    context = {'event_list': event_list}
    return render_template('research_events/timeline.html', **ctx, **context)


@bp.route('/research-events/pentest-chain')
def research_events_chain():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request pentest chain with non-integer project_id: {request.args.get('project_id')}")
        abort(400)
    project = db.get_or_404(models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.PentestResearchEvent(), 'pentest_chain', project=project)
    events = db.session.scalars(sa.select(models.PentestResearchEvent).where(models.PentestResearchEvent.project_id == project.id)).all()
    ctx = get_default_environment(models.PentestResearchEvent(project=project), 'pentest_chain')
    nodes = [{"id": i.id, "label": i.title} for i in events]
    edges = []
    for evt in events:
        if len(evt.follow_from_events) != 0:
            for fe in evt.follow_from_events:
                edges.append({'from': fe.id, 'to': evt.id, 'arrows': 'to'})
    context = {'nodes': json.dumps(nodes), 'edges': json.dumps(edges)}
    side_libraries.library_required('visjs')
    return render_template('research_events/pentest-chain.html', **ctx, **context)