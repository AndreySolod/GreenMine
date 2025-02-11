from app import db, logger
from flask import flash, has_request_context
from app.helpers.general_helpers import default_string_slug, utcnow, get_complementary_color
from app.helpers.admin_helpers import project_enumerated_object, project_status_object, project_object_with_permissions
from flask import url_for
from typing import List, Set, Optional
from .generic import HasComment, HasHistory, UserNotification, Comment
from .files import FileData
import sqlalchemy as sa
import sqlalchemy.orm as so
import sqlalchemy.exc as exc
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import validates
from sqlalchemy.orm.session import Session as SessionBase
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import event
import datetime
import wtforms
from app.controllers.forms import PickrColorField
from flask_babel import lazy_gettext as _l
from flask_socketio import emit
from flask_login import current_user
from app.extensions.moment import moment


class StateToStateTask(db.Model):
    from_state_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('task_state.id', ondelete='CASCADE'), primary_key=True)
    to_state_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('task_state.id', ondelete='CASCADE'), primary_key=True)


@project_enumerated_object
@project_status_object
class TaskState(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(20), info={'label': _l("Title")})
    color: so.Mapped[int] = so.mapped_column(sa.String(60), info={'label': _l("Color"), 'form': PickrColorField})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Description"), 'form': wtforms.TextAreaField})
    icon: so.Mapped[Optional[str]] = so.mapped_column(sa.String(30), info={'label': _l("Icon")})
    can_switch_to_state: so.Mapped[Set["TaskState"]] = so.relationship(secondary=StateToStateTask.__table__,
                                                                        primaryjoin=(StateToStateTask.from_state_id == id),
                                                                        secondaryjoin=(StateToStateTask.to_state_id == id),
                                                                        back_populates='can_switch_from_state', info={'label': _l("Can switch to the status"), 'on_form': False})
    can_switch_from_state: so.Mapped[Set["TaskState"]] = so.relationship(secondary=StateToStateTask.__table__,
                                                                          primaryjoin=(StateToStateTask.to_state_id == id),
                                                                          secondaryjoin=(StateToStateTask.from_state_id == id),
                                                                          back_populates='can_switch_to_state', info={'label': _l("Can switch from the status"), 'on_form': False})

    def __repr__(self):
        return f"<TaskState {self.title} with color '{self.color}'>"

    class Meta:
        verbose_name = _l("Task status")
        verbose_name_plural = _l("Task statuses")
        title_new = _l("Add task status")
        description = _l("Used to mark the current stage of the task.")
        column_index = ['id', 'string_slug', 'title', 'color', 'description']


@project_enumerated_object
class ProjectTaskPriority(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(20), index=True, info={'label': _l("Title")})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Description"), 'form': wtforms.TextAreaField})
    color: so.Mapped[Optional[str]] = so.mapped_column(sa.String(60), info={'label': _l("Color"), 'form': PickrColorField})
    is_default: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l("Default")})

    def __repr__(self):
        return "Priority '{}'".format(self.title)

    class Meta:
        verbose_name = _l("Task priority")
        verbose_name_plural = _l("Task priorities")
        title_new = _l("Add new task priority")
        description = _l("It is used to simplify filtering by issue")
        column_index = ['id', 'string_slug', 'title', 'description', 'color', 'is_default']


@project_enumerated_object
class ProjectTaskTracker(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(35), info={'label': _l("Title")})

    class Meta:
        verbose_name = _l("Task tracker")
        verbose_name_plural = _l("Task trackers")
        title_new = _l("Add new task tracker")
        description = _l("It is used to simplify filtering by issue")
        column_index = ['id', 'string_slug', 'title']


class TaskRelatedToTask(db.Model):
    first_related_task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project_task.id', ondelete='CASCADE'), primary_key=True)
    second_related_task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project_task.id', ondelete='CASCADE'), primary_key=True)


class ObserversToTask(db.Model):
    observer_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
    task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project_task.id', ondelete='CASCADE'), primary_key=True)


class ServiceHasTask(db.Model):
    service_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('service.id', ondelete='CASCADE'), primary_key=True)
    task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project_task.id', ondelete='CASCADE'), primary_key=True)


class FileHasTask(db.Model):
    filedata_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('file_data.id', ondelete='CASCADE'), primary_key=True)
    task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project_task.id', ondelete='CASCADE'), primary_key=True)


@project_object_with_permissions
class ProjectTask(HasComment, db.Model, HasHistory):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    archived: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l("Archived")})
    title: so.Mapped[str] = so.mapped_column(sa.String(30), info={'label': _l("Theme")})
    description: so.Mapped[str] = so.mapped_column(info={'label': _l("Description"), 'help_text': _l("Detailed description - what exactly needs to be done")})
    created_at: so.Mapped[datetime.datetime] = so.mapped_column(default=utcnow, info={'label': _l("Created at"), 'help_text': _l("The date and time the task was created. It is filled in automatically")})
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Created by")})
    created_by: so.Mapped['User'] = so.relationship(lazy='select', foreign_keys=[created_by_id], info={'label': _l("Created by")}) # type: ignore
    updated_at: so.Mapped[Optional[datetime.datetime]] = so.mapped_column(info={"label": _l("Updated at"), 'help_text': _l("It is filled in automatically when the task is changed")})
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Updated by"), 'help_text': _l("The user who updated the task")})
    updated_by: so.Mapped["User"] = so.relationship(lazy='select', foreign_keys=[updated_by_id], info={"label": _l("Updated by"), 'help_text': _l("The user who updated the task")}) # type: ignore
    tracker_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(ProjectTaskTracker.id, ondelete='SET NULL'), info={'label': _l("Tracker"), 'help_text': _l("A hypothesis about a possible problem")})
    tracker: so.Mapped["ProjectTaskTracker"] = so.relationship(lazy='select',
                                                               info={'label': _l("Tracker"),
                                                                     'help_text': _l("A hypothesis about a possible problem")})
    priority_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(ProjectTaskPriority.id,
                                                   ondelete='SET NULL'), info={'label': _l("Priority"),
                                                                               'help_text': _l("The assigned priority of the task. Simplifies filtering by tasks")})
    priority: so.Mapped["ProjectTaskPriority"] = so.relationship(lazy='joined',
                                                                 info={'label': _l("Priority"),
                                                                       'help_text': _l("The assigned priority of the task. Simplifies filtering by tasks")})
    project_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project.id',
                                                  ondelete='CASCADE'), info={'label': _l("Project"), 'help_text': _l("The project to which the task belongs")})
    project: so.Mapped["Project"] = so.relationship(lazy='select', back_populates="tasks", info={'label': _l("Project"), 'help_text': _l("The project to which the task belongs")}) # type: ignore
    state_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(TaskState.id, ondelete='SET NULL'), info={'label': _l("Status"), 'help_text': _l("The status of a task is the state in which the task is located")})
    state: so.Mapped["TaskState"] = so.relationship(lazy='select', info={'label': _l("Status"), 'help_text': _l("The status of a task is the state in which the task is located")})
    assigned_to_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Assigned to")})
    assigned_to: so.Mapped["User"] = so.relationship(foreign_keys=[assigned_to_id], backref=so.backref("assigned_tasks", lazy='select', info={'label': _l("Assigned tasks")}), # type: ignore
                                                     info={'label': _l("Assigned to")})
    date_start: so.Mapped[Optional[datetime.date]] = so.mapped_column(default=utcnow, info={'label': _l("The planned start date for solving the task")})
    date_end: so.Mapped[Optional[datetime.date]] = so.mapped_column(info={'label': _l("The planned end date for solving the task")})
    readiness: so.Mapped[int] = so.mapped_column(sa.SmallInteger, default=0, info={'label': _l("Readiness")})
    parent_task_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('project_task.id', ondelete='CASCADE'), info={'label': _l("Parent task")})
    parent_task: so.Mapped["ProjectTask"] = so.relationship(lazy='select', backref=so.backref('subtasks', info={'label': _l("Subtasks")}),
                                                            join_depth=2, foreign_keys=[parent_task_id], remote_side=[id], info={'label': _l("Parent task")})
    
    observers: so.Mapped[Set['User']] = so.relationship(secondary=ObserversToTask.__table__, # type: ignore
                                                         primaryjoin=id==ObserversToTask.task_id,
                                                         secondaryjoin='ObserversToTask.observer_id==User.id',
                                                         lazy='select', info={'label': _l("Observers")})
    estimation_time_cost: so.Mapped[Optional[datetime.timedelta]] = so.mapped_column(info={'label': _l("Time cost estimation")})
    issues: so.Mapped[Set["Issue"]] = so.relationship(secondary='issue_has_task', # type: ignore
                                                       primaryjoin='ProjectTask.id==IssueHasTask.task_id',
                                                       secondaryjoin='Issue.id==IssueHasTask.issue_id',
                                                       back_populates="tasks_by_issue", info={"label": _l("Issues")})
    services: so.Mapped[Set["Service"]] = so.relationship(secondary=ServiceHasTask.__table__, # type: ignore
                                                           primaryjoin=id==ServiceHasTask.task_id,
                                                           secondaryjoin='ServiceHasTask.service_id==Service.id',
                                                           back_populates='tasks', info={'label': _l("Assigned services")})
    related_tasks: so.Mapped[Set["ProjectTask"]] = so.relationship(secondary=TaskRelatedToTask.__table__,
                                                                    primaryjoin=id==TaskRelatedToTask.first_related_task_id,
                                                                    secondaryjoin=TaskRelatedToTask.second_related_task_id==id,
                                                                    lazy='select', info={'label': _l("Related tasks")})
    related_files: so.Mapped[List["FileData"]] = so.relationship(secondary=FileHasTask.__table__,
                                                                 primaryjoin=id==FileHasTask.task_id,
                                                                 secondaryjoin="FileHasTask.filedata_id==FileData.id",
                                                                 lazy='select', cascade='all,delete', info={'label': _l("Related files")})

    @validates("readiness")
    def validates_readiness(self, key, readiness):
        if readiness < 0 or readiness > 100:
            raise ValueError("Readiness should be in the range from 0 to 100")
        return readiness

    @validates("parent_task")
    def validates_parent_task_id(self, key, parent_task):
        if parent_task is not None and parent_task.project_id != self.project_id:
            raise ValueError('The parent task must belong to the same project as the child task')

        def _validate(task, parents=[]):
            if task in parents:
                raise ValueError("The task cannot be a parent for itself")
            elif task.parent_task is None:
                return True
            else:
                return _validate(task.parent_task, parents + [task])
        _validate(self)
        return parent_task

    def __repr__(self):
        return f"<ProjectTask '{self.title}' with id={self.id}>"
    
    def unrelate_tasks(self, *tasks: "ProjectTask") -> None:
        for task in tasks:
            self.related_tasks.remove(task)
            if self in task.related_tasks:
                task.related_tasks.remove(self)
    
    def relate_tasks(self, *tasks: "ProjectTask") -> None:
        for task in tasks:
            self.related_tasks.add(task)
            task.related_tasks.add(self)
    
    @property
    def related_files_info(self):
        return [{'id': i[0], 'title': i[1]} for i in db.session.execute(sa.select(FileData.id, FileData.title).join(FileHasTask).join(ProjectTask).where(ProjectTask.id == self.id))]

    class Meta:
        verbose_name = _l("Task")
        verbose_name_plural = _l("Tasks")
        icon = 'fa-solid fa-spider'
        icon_index = 'fa-solid fa-bugs'
        project_permission_actions = {'index': _l("Show object list"), 'kanban': _l("Show task kanban board"), 'create': _l("Create new object"), 'show': _l("Show object card"),
                                      'update': _l("Edit and update object"), 'delete': _l("Delete object"), 'add_comment': _l("Add comment to object"),
                                      'show_comments': _l("Show comment list of object"), 'show_history': _l("Show object history")}

    @hybrid_property
    def fulltitle(self):
        return _l("Task #%(task_id)s: «%(task_title)s»", task_id=self.id, task_title=self.title)
    
    @property
    def treeselecttitle(self):
        return self.fulltitle


@event.listens_for(SessionBase, 'before_commit')
def update_task_default_value(session):
    ''' Updated task default value. Set state to Initial state - state, that do not have "can_switch_from_state" '''
    nt = [u for u in session.new if isinstance(u, ProjectTask)]
    if len(nt) == 0:
        return None
    try:
        state_new = next(filter(lambda x: len(x.can_switch_from_state) == 0, session.scalars(sa.select(TaskState)).all()))
    except StopIteration:
        if has_request_context():
            flash(_l("There is no initial status for this object. The first one was chosen"), 'danger')
        state_new = session.scalars(sa.select(TaskState)).first()
    for n in nt:
        if n.state_id is None and n.state is None:
            n.state = state_new
            session.add(n)


def task_was_changed(task: ProjectTask) -> bool:
    ''' check if changed task attribute not is "comments" and "history" - for them we was sending another signals '''
    for a in inspect(task).attrs:
        if len(list(a.history.added) + list(a.history.deleted)) != 0 and a.key != 'comments' and a.key != 'history':
            return True
    return False


def get_current_attr(obj, attr: str):
    attr_class = inspect(obj.__class__).relationships[attr].entity.class_
    if inspect(obj).attrs[attr].history.added or inspect(obj).attrs[attr].history.deleted:
        return getattr(obj, attr)
    elif getattr(obj, attr + '_id') is not None:
        return db.session.get(attr_class, getattr(obj, attr + '_id'))
    else:
        return None


@event.listens_for(ProjectTask, 'after_update')
def emit_task_edited_signal_via_websocket(mapper, connection, target):
    """ Emitted signal "task edited" via WebSocket for update task page if any user has opened one """
    try:
        # refresh object to avoid problem with related objects (such as priority, tracker, etc). If do not refreshed object - this object may not updated
        # because changed not him, but "tracker_id", "priority_id", "state_id" etc.
        new_target = db.session.get(ProjectTask, target.id) # if not, some object from session (Comments for example) are detached
        if not task_was_changed(target) or not has_request_context(): # task was not changed - we did not send message
            return 
        tracker = get_current_attr(new_target, 'tracker')
        priority = get_current_attr(new_target, 'priority')
        state = get_current_attr(new_target, 'state')
        assigned_to = get_current_attr(new_target, 'assigned_to')
        data = {'title': new_target.title, 'tracker': tracker.title, 'state': state.title, 'state_background_color': state.color,
                'state_color': get_complementary_color(state.color), 'priority': priority.title, 'priority_background_color': priority.color,
                'priority_color': get_complementary_color(priority.color)}
    except (AttributeError, exc.MultipleResultsFound, exc.NoResultFound) as e:
        logger.error(f"models/tasks.py - error in function 'emit_task_edited_signal_via_websocket'. target: {new_target}, exception: {e}")
        return None
    if assigned_to is not None: # assigned_to was removed
        data['assigned_to_href'] = url_for('users.user_show', user_id=assigned_to.id)
        data['assigned_to_title'] = assigned_to.title
    else:
        data['assigned_to_href'] = '#'
        data['assigned_to_title'] = ''
    data['readiness'] = new_target.readiness
    data['estimation_time_cost'] = str(new_target.estimation_time_cost)
    data['date_start'] = moment(new_target.date_start).format('LL')
    data['date_end'] = moment(new_target.date_end).format('LL')
    data['description'] = new_target.description
    emit('task edited', data, namespace='/task', to=str(new_target.id)) # emit signal


@event.listens_for(ProjectTask, 'after_insert')
def create_new_notification_object_if_task_has_assigned_to_attribute(mapper, connection, target):
    ''' Create object UserNotification if created task has "assigned_to" attribute '''
    _l("A new task #%(task_id)s: «%(task_title)s» has been assigned to you")
    new_target = db.session.get(ProjectTask, target.id)
    if new_target.assigned_to and new_target.assigned_to.id != new_target.created_by_id:
        notif = UserNotification(to_user_id=new_target.assigned_to.id, description='A new task #%(task_id)s: «%(task_title)s» has been assigned to you')
        notif.technical_info = {'task_id': new_target.id, 'task_title': new_target.title}
        notif.link_to_object = url_for('tasks.projecttask_show', projecttask_id=new_target.id)
        if current_user == None or current_user.is_anonymous:
            notif.by_user = new_target.created_by
        else:
            notif.by_user_id = current_user.id
        db.technical_session.add(notif)


@event.listens_for(ProjectTask, 'after_update')
def create_notification_if_changed_with_assigned_user(mapper, connection, target):
    """ Added User notification in database to render him on template """
    _l("The task #%(task_id)s, that is in your responsibility has been changed")
    _l("A new task #%(task_id)s: «%(task_title)s» has been assigned to you")
    # check if assigned_to is changed:
    assign_history = list(inspect(target).attrs.assigned_to.history.added) + list(inspect(target).attrs.assigned_to.history.deleted)
    assign_history += list(inspect(target).attrs.assigned_to_id.history.added) + list(inspect(target).attrs.assigned_to_id.history.deleted)
    assigned_to = get_current_attr(target, 'assigned_to')
    if (assigned_to and current_user != None and not current_user.is_anonymous and current_user.id != assigned_to.id and len(assign_history) != 0):
        notif = UserNotification(to_user_id=assigned_to.id, description='A new task #%(task_id)s: «%(task_title)s» has been assigned to you')
    elif assigned_to and current_user != None and not current_user.is_anonymous and assigned_to.id != current_user.id and task_was_changed(target):
        notif = UserNotification(to_user_id=assigned_to.id, description='The task #%(task_id)s, that is in your responsibility has been changed')
    else:
        return None
    notif.technical_info = {'task_id': target.id, 'task_title': target.title}
    notif.link_to_object  = url_for('tasks.projecttask_show', projecttask_id=target.id)
    if not has_request_context() or current_user.is_anonymous:
        notif.by_user = target.updated_by
    else:
        notif.by_user_id = current_user.id
    db.technical_session.add(notif)


@event.listens_for(Comment, 'after_insert')
def create_notification_to_assigned_to_user_task_when_comment_added(mapper, connection, target: Comment):
    """ create UserNotification object when comment is added to ProjectTask and ProjectTask has assigned_to user """
    _l("A comment has been added to task #%(task_id)s, which is your responsibility.")
    if target.to_object.__class__.__name__ == 'ProjectTask':
        assigned_to = get_current_attr(target.to_object, 'assigned_to')
        if assigned_to is None:
            return None
        notif = UserNotification(to_user_id=assigned_to.id, description="A comment has been added to task #%(task_id)s, which is your responsibility.")
        notif.technical_info = {'task_id': target.to_object.id}
        notif.link_to_object = url_for('tasks.projecttask_show', projecttask_id=target.to_object.id)
        if not has_request_context() or current_user.is_anonymous:
            notif.by_user = target.created_by
        else:
            notif.by_user_id = current_user.id
        db.technical_session.add(notif)


class ProjectTaskTemplate(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    archived: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l("Archived")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l('Slug')})
    title: so.Mapped[str] = so.mapped_column(sa.String(30), info={'label': _l("Template title")})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Template description")})
    task_title: so.Mapped[str] = so.mapped_column(sa.String(ProjectTask.title.type.length), info={'label': _l("Task theme")})
    task_description: so.Mapped[str] = so.mapped_column(info={'label': _l("Task description")})
    task_tracker_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(ProjectTaskTracker.id, ondelete='SET NULL'), info={'label': _l('Task tracker')})
    task_tracker: so.Mapped[ProjectTaskTracker] = so.relationship(lazy='select', info={'label': _l("Task tracker")})
    task_priority_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(ProjectTaskPriority.id, ondelete='SET NULL'), info={'label': _l("Task priority")})
    task_priority: so.Mapped[ProjectTaskPriority] = so.relationship(lazy='select', info={'label': _l("Task priority")})
    task_estimation_time_cost: so.Mapped[Optional[datetime.timedelta]] = so.mapped_column(info={'label': _l("Task time cost estimation")})

    class Meta:
        verbose_name = _l('Project task template')
        verbose_name_plural = _l('Project task templates')
        icon = 'fa-solid fa-clipboard'