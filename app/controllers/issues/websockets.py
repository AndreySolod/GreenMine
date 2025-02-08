from app import socketio, db, logger
from app.helpers.general_helpers import authenticated_only
from app.helpers.projects_helpers import get_current_room
from flask_socketio import emit, join_room
from flask import url_for
from app.helpers.roles import project_role_can_make_action
from flask_login import current_user
import app.models as models
import sqlalchemy as sa
import sqlalchemy.exc as exc
from bs4 import BeautifulSoup


@socketio.on("join_room", namespace="/issue")
@authenticated_only
def join_current_issue_room(data):
    try:
        issue = db.session.scalars(sa.select(models.Issue).where(models.Issue.id == int(data))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join incorrect issues room {data}")
        return None
    if not project_role_can_make_action(current_user, issue, 'show'):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join issues room #{data}, in which he has no rights to")
        return None
    room = data
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' join issue room #{data}")
    join_room(room, namespace="/issue")


@socketio.on('edit related services', namespace='/issue')
@authenticated_only
def edit_related_services(data):
    r = get_current_room()
    if r is None:
        return False
    issue_id, current_room_name = r
    try:
        issue = db.session.scalars(sa.select(models.Issue).where(models.Issue.id == int(issue_id))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        return None
    if not project_role_can_make_action(current_user, issue, 'update'):
        return None
    try:
        services = db.session.scalars(sa.select(models.Service).join(models.Service.host).join(models.Host.from_network)
                                      .where(sa.and_(models.Service.id.in_([int(i) for i in data['related_services']]),
                                                                          models.Network.project_id==issue.project_id))).all()
        updated_services = set(issue.services)
        updated_services = updated_services.union(set(services))
        issue.services = services
        db.session.commit()
    except (ValueError, TypeError, KeyError):
        return None
    new_services = []
    for i in issue.services:
        ns = {'id': i.id, 'title': i.title, 'ip_address': str(i.host.ip_address), 'port': i.port, 'technical': i.technical}
        ns['transport_level_protocol'] = '' if i.transport_level_protocol is None else i.transport_level_protocol.title
        ns['access_protocol'] = '' if i.access_protocol is None else i.access_protocol.title
        new_services.append(ns)
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit related services on issue #{issue.id}")
    emit('change related services', {'rows': new_services},
         namespace='/issue', to=current_room_name)
    for service in updated_services:
        new_issues = [{'id': i.id, 'title': i.title, 'description': BeautifulSoup(i.description, 'lxml').text, 'status': i.status.title} for i in service.issues]
        emit('change related issues', {'rows': new_issues},
            namespace='/service', to=str(service.id))


@socketio.on('edit related tasks', namespace='/issue')
@authenticated_only
def relate_issue_to_service(data):
    r = get_current_room()
    if r is None:
        return False
    issue_id, current_room_name = r
    try:
        issue = db.session.scalars(sa.select(models.Issue).where(models.Issue.id == int(issue_id))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        return None
    if not project_role_can_make_action(current_user, issue, 'update'):
        return None
    try:
        now_tasks = db.session.scalars(sa.select(models.ProjectTask).where(sa.and_(models.ProjectTask.id.in_([int(i) for i in data['related_tasks']]),
                                                                          models.ProjectTask.project_id==issue.project_id))).all()
        update_tasks = set(issue.tasks_by_issue)
        update_tasks = update_tasks.union(set(now_tasks))
        issue.tasks_by_issue = now_tasks
        db.session.commit()
    except(ValueError, TypeError, KeyError):
        return None
    new_tasks = []
    for i in issue.tasks_by_issue:
        nr = {'id': i.id, 'title': i.title, 'state': i.state.title, 'readiness': i.readiness}
        nr['tracker'] = '' if i.tracker is None else i.tracker.title
        nr['priority'] = '' if i.priority is None else i.priority.title
        nr['assigned_to'] = '' if i.assigned_to is None else i.assigned_to.title
        new_tasks.append(nr)
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit related tasks on issue #{issue.id}")
    emit('change related tasks', {'rows': new_tasks},
         namespace='/issue', to=current_room_name)
    for task in update_tasks:
        new_issues = [{'id': i.id, 'title': i.title, 'description': BeautifulSoup(i.description, 'lxml').text, 'status': i.status.title} for i in task.issues]
        emit('change related issues', {'rows': new_issues},
            namespace='/task', to=str(task.id))
