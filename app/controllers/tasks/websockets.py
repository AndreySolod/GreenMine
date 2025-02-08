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
from app.extensions.moment import moment
import textwrap
from jinja2.filters import Markup
from bs4 import BeautifulSoup


@socketio.on("join_room", namespace="/tasks")
@authenticated_only
def join_task_room(data):
    try:
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == int(data))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError):
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join incorrect task list room {data}")
        return None
    if not project_role_can_make_action(current_user, models.ProjectTask(), 'index', project=project):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join task list room #{data}, in which he has no rights to")
        return None
    room = data
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' join task list room #{data}")
    join_room(room, namespace="/tasks")


@socketio.on('change element', namespace="/tasks")
@authenticated_only
def change_task_status(data):
    r = get_current_room()
    if r is None:
        return False
    project_id, current_room_name = r
    try:
        task_id = int(data['itemId'])
        to_state_id = int(data['targetColumnId'])
        to_priority_id = int(data['targetGroupId'])
    except (ValueError, TypeError, KeyError):
        return False
    try:
        task = db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.id == task_id)).one()
        to_state = db.session.scalars(sa.select(models.TaskState).where(models.TaskState.id == to_state_id)).one()
        to_priority = db.session.scalars(sa.select(models.ProjectTaskPriority).where(models.ProjectTaskPriority.id == to_priority_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        return False
    if not project_role_can_make_action(current_user, task, 'update'):
        return {'status': 'fail', 'message': 'You have no right to perform this action'}
    if to_state_id not in ([i.id for i in task.state.can_switch_to_state] + [task.state.id]):
        return {'status': 'fail', 'message': "The specified transition between statuses is prohibited!"}
    task.state = to_state
    task.priority = to_priority
    task.updated_by_id = current_user.id
    db.session.add(task)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit status of task #{task_id}")
    emit('refresh', {'get_data': True}, namespace="/tasks", to=current_room_name, include_self=False)
    return {'status': 'success'}


@socketio.on('change group', namespace='/tasks')
@authenticated_only
def change_priority_order(data):
    return {'message': 'Пока что не поддерживается'}


@socketio.on('get data', namespace='/tasks')
@authenticated_only
def get_tasks_kanban_board(data):
    r = get_current_room()
    if r is None:
        return False
    project_id, current_room_name = r
    conf = {"row": []}
    try:
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == project_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        return False
    project_role_can_make_action(current_user, models.ProjectTask(), 'kanban', project=project)
    tasks = db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.project_id==project.id)).all()
    statuses = db.session.execute(sa.select(models.TaskState.id, models.TaskState.title, models.TaskState.color, models.TaskState.icon)).all()
    priorities = db.session.execute(sa.select(models.ProjectTaskPriority.id, models.ProjectTaskPriority.title, models.ProjectTaskPriority.description,
                                              models.ProjectTaskPriority.color)).all()
    for id, title, color, icon in statuses:
        conf["row"].append({"COLUMN_ID": id,
                            "COLUMN_TITLE": title,
                            "COLUMN_ICON": icon,
                            "COLUMN_COLOR": color,
                            "COLUMN_HEADER_STYLE": f"border-color: {color}"})
    for id, title, description, color in priorities:
        conf["row"].append({"GROUP_ID": id,
                            "GROUP_TITLE": title,
                            "GROUP_ICON": "fa-solid fa-circle-exclamation",
                            "GROUP_HEADER_STYLE": f"background-color:{color}",
                            "GROUP_FOOTER": description})
    for task in tasks:
        conf["row"].append({"COLUMN_ID": task.state_id,
                            "COLUMN_TITLE": task.state.title,
                            "COLUMN_ICON": task.state.icon,
                            "COLUMN_HEADER_STYLE": f"border-color: {task.state.color}",
                            "GROUP_ID": task.priority_id,
                            "GROUP_TITLE": task.priority.title,
                            "GROUP_ICON": "fa-solid fa-circle-exclamation",
                            "GROUP_FOOTER": task.priority.description,
                            "ID": task.id,
                            "TITLE": task.title,
                            "FOOTER": textwrap.shorten(BeautifulSoup(Markup.unescape(task.description), 'lxml').get_text(separator="\n"), width=100, placeholder='...'),
                            "ICON": "",
                            "LINK": url_for('tasks.projecttask_show', projecttask_id=task.id),
                            "ICON_COLOR": "",
                            "HEADER_STYLE": ""})
    return conf


@socketio.on("join_room", namespace="/task")
@authenticated_only
def join_current_task_room(data):
    try:
        task = db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.id == int(data))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join incorrect task room {data}")
        return None
    if not project_role_can_make_action(current_user, task, 'show'):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join task room #{data}, in which he has no rights to")
        return None
    room = data
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' join task room #{data}")
    join_room(room, namespace="/task")


@socketio.on("relate task", namespace="/task")
@authenticated_only
def change_related_tasks(data):
    r = get_current_room()
    if r is None:
        return False
    task_id, current_room_name = r
    try:
        task = db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.id == int(task_id))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        return None
    if not project_role_can_make_action(current_user, task, 'update'):
        return None
    try:
        new_related_tasks = db.session.scalars(sa.select(models.ProjectTask).where(sa.and_(models.ProjectTask.id.in_([int(i) for i in data['related_tasks'] if int(i) != task.id]),
                                                                                       models.ProjectTask.project_id == task.project_id))).all()
        update_related_tasks = set(task.related_tasks)
        task.unrelate_tasks(*task.related_tasks)
        task.relate_tasks(*new_related_tasks)
        update_related_tasks = update_related_tasks.union(set(new_related_tasks))
        update_related_tasks.add(task)
        db.session.add(task)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit related tasks on task #{task.id}")
    except (ValueError, TypeError):
        return None
    def good_date(to_moment_date):
        if to_moment_date is None:
            return ''
        return moment(to_moment_date).format('LL')
    for nt in update_related_tasks:
        emit('change related tasks', {'tasks': [{'id': i.id, 'title': i.tracker.title + ' #' + str(i.id) + ': ' + i.title,
                                                'link': url_for('tasks.projecttask_show', projecttask_id=i.id),
                                                'state': i.state.title, 'readiness': str(i.readiness),
                                                'date_start': good_date(i.date_start), 'date_end': good_date(i.date_end)} for i in nt.related_tasks]},
            namespace='/task', to=str(nt.id))


@socketio.on('untie task', namespace='/task')
@authenticated_only
def untie_task(data):
    r = get_current_room()
    if r is None:
        return False
    task_id, current_room_name = r
    try:
        task = db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.id == int(task_id))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        return None
    if not project_role_can_make_action(current_user, task, 'update'):
        return None
    try:
        untie_task = db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.id == int(data))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError):
        return None
    task.unrelate_tasks(untie_task)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit related tasks on task #{task.id}")
    def good_date(to_moment_date):
        if to_moment_date is None:
            return ''
        return moment(to_moment_date).format('LL')
    emit('change related tasks', {'tasks': [{'id': i.id, 'title': i.tracker.title + ' #' + str(i.id) + ': ' + i.title,
                                             'link': url_for('tasks.projecttask_show', projecttask_id=i.id),
                                             'state': i.state.title, 'readiness': str(i.readiness),
                                             'date_start': good_date(i.date_start), 'date_end': good_date(i.date_end)} for i in task.related_tasks]},
         namespace='/task', to=current_room_name)
    emit('change related tasks', {'tasks': [{'id': i.id, 'title': f'{i.tracker.title} #{i.id}: {i.title}',
                                             'link': url_for('tasks.projecttask_show', projecttask_id=i.id),
                                             'state': i.state.title, 'readiness': str(i.readiness),
                                             'date_start': good_date(i.date_start), 'date_end': good_date(i.date_end)} for i in untie_task.related_tasks]},
         namespace='/task', to=str(untie_task.id))


@socketio.on('edit related issues', namespace='/task')
@authenticated_only
def edit_related_issues(data):
    r = get_current_room()
    if r is None:
        return False
    task_id, current_room_name = r
    try:
        task = db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.id == int(task_id))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        return None
    if not project_role_can_make_action(current_user, task, 'update'):
        return None
    try:
        issues = db.session.scalars(sa.select(models.Issue).where(sa.and_(models.Issue.id.in_([int(i) for i in data['related_issues']]),
                                                                          models.Issue.project_id==task.project_id))).all()
        task.issues = set(issues)
        db.session.commit()
    except (ValueError, TypeError, KeyError):
        return None
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit related issues on task #{task.id}")
    new_issues = [{'id': i.id, 'title': i.title, 'description': BeautifulSoup(i.description, 'lxml').text, 'status': i.status.title} for i in task.issues]
    emit('change related issues', {'rows': new_issues},
         namespace='/task', to=current_room_name)


@socketio.on('edit related services', namespace='/task')
@authenticated_only
def edit_related_services(data):
    r = get_current_room()
    if r is None:
        return False
    task_id, current_room_name = r
    try:
        task = db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.id == int(task_id))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        return None
    if not project_role_can_make_action(current_user, task, 'update'):
        return None
    try:
        services = db.session.scalars(sa.select(models.Service).join(models.Service.host).join(models.Host.from_network)
                                      .where(sa.and_(models.Service.id.in_([int(i) for i in data['related_services']]),
                                                                          models.Network.project_id==task.project_id))).all()
        updated_services = set(task.services)
        updated_services = updated_services.union(set(services))
        task.services = set(services)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit related servicese on task #{task.id}")
    except (ValueError, TypeError, KeyError):
        return None
    new_services = []
    for i in task.services:
        ns = {'id': i.id, 'title': i.title, 'ip_address': str(i.host.ip_address), 'port': i.port, 'technical': i.technical}
        ns['transport_level_protocol'] = '' if i.transport_level_protocol is None else i.transport_level_protocol.title
        ns['access_protocol'] = '' if i.access_protocol is None else i.access_protocol.title
        new_services.append(ns)
    emit('change related services', {'rows': new_services},
         namespace='/task', to=current_room_name)
    for service in updated_services:
        new_tasks = []
        for i in service.tasks:
            nr = {'id': i.id, 'title': i.title, 'state': i.state.title, 'readiness': i.readiness}
            nr['tracker'] = '' if i.tracker is None else i.tracker.title
            nr['priority'] = '' if i.priority is None else i.priority.title
            nr['assigned_to'] = '' if i.assigned_to is None else i.assigned_to.title
            new_tasks.append(nr)
        emit('change related tasks', {'rows': new_tasks},
            namespace='/service', to=str(service.id))


@socketio.on('delete related files', namespace='/task')
@authenticated_only
def edit_related_files(data):
    r = get_current_room()
    if r is None:
        return False
    task_id, current_room_name = r
    try:
        task = db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.id == int(task_id))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        return None
    try:
        file_data_id = db.session.scalars(sa.select(models.FileData.id).join(models.FileHasTask).join(models.ProjectTask).where(sa.and_(models.FileData.id == int(data['file_id']), models.ProjectTask.id == task_id))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError, KeyError):
        return None
    if not project_role_can_make_action(current_user, task, 'update'):
        return None
    db.session.execute(sa.delete(models.FileData).where(models.FileData.id == file_data_id))
    db.session.execute(sa.delete(models.FileHasTask).where(models.FileHasTask.filedata_id == file_data_id))
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit related files on task #{task.id}")
    emit('file deleted', {'file_id': file_data_id}, to=current_room_name, namespace='/task')