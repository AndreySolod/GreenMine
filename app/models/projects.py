from app import db, sanitizer
from app.models.files import FileDirectory
from app.helpers.admin_helpers import project_enumerated_object, project_object_with_permissions
from typing import List, Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.orm import validates
from sqlalchemy.inspection import inspect
import datetime
from sqlalchemy import event
from sqlalchemy.orm.session import Session as SessionBase
from flask_babel import lazy_gettext as _l
from flask import url_for
from bs4 import BeautifulSoup
from .networks import Network, Host, Service
from .datatypes import ID, StringSlug, CreatedAt, UpdatedAt, Archived


@project_object_with_permissions
class Project(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(50), index=True, info={'label': _l("Title")})
    archived: so.Mapped[Archived]
    description: so.Mapped[str] = so.mapped_column(info={'label': _l("Description"), 'description': _l("Project description - additional information not specified in other fields")})
    created_at: so.Mapped[CreatedAt]
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete="SET NULL"), info={'label': _l("Created by")})
    created_by: so.Mapped["User"] = so.relationship(lazy='joined', foreign_keys=[created_by_id], info={'label': _l("Created by")}) # type: ignore
    updated_at: so.Mapped[UpdatedAt]
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Updated by")})
    updated_by: so.Mapped["User"] = so.relationship(lazy='joined', foreign_keys=[updated_by_id], info={'label': _l("Updated by")}) # type: ignore
    start_at: so.Mapped[datetime.date] = so.mapped_column(info={'label': _l("Start date"), 'description': _l("Start date of work on the project")})
    end_at: so.Mapped[datetime.date] = so.mapped_column(info={'label': _l("End date"), 'description': _l("End date of work on the project")})
    leader_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Manager"), 'description': _l("The person responsible for this project")})
    leader: so.Mapped['User'] = so.relationship(lazy='joined', foreign_keys=[leader_id], info={'label': _l("Manager"), 'description': _l("The person responsible for this project")}) # type: ignore
    tasks: so.Mapped[List["ProjectTask"]] = so.relationship(back_populates="project", cascade="all, delete-orphan", info={'label': _l("Tasks"), 'description': _l("Tasks performed within the framework of the project")}) # type: ignore
    networks: so.Mapped[List[Network]] = so.relationship(lazy='select', back_populates='project', info={'label': _l("Networks")}, cascade='all,delete-orphan')
    participants: so.Mapped[List["UserRoleHasProject"]] = so.relationship(back_populates="project", lazy='select', cascade='all, delete-orphan', order_by="UserRoleHasProject.role_id", info={'label': _l("Participants")})
    additional_parameters: so.Mapped[List["ProjectAdditionalFieldData"]] = so.relationship(lazy='select', info={'label': _l("Additional fields")}, back_populates="project", cascade="all,delete-orphan") # type: ignore

    @validates("end_at")
    def validates_end_at(self, key, end_at):
        if not (self.start_at is None) and (end_at < self.start_at):
            raise ValueError("The start date cannot be later than the end date")
        return end_at

    @validates("start_at")
    def validates_start_at(self, key, start_at):
        if not (self.end_at is None) and self.end_at < start_at:
            raise ValueError("The start date cannot be later than the end date")
        return start_at

    @property
    def fulltitle(self):
        return _l("Project #%(project_id)s: «%(title)s»", project_id=self.id, title=sanitizer.sanitize(sanitizer.unescape(self.title)))

    def to_dict(self):
        cols = inspect(self.__class__).column_attrs.keys()
        res = {}
        for col in cols:
            res[col] = inspect(self).attrs[col].value
        return res
    
    @property
    def grouped_participants(self):
        if len(self.participants) == 0:
            return {}
        current_role = self.participants[0].role
        intermediate = {current_role: []}
        for p in self.participants:
            if p.role in intermediate:
                intermediate[p.role].append(p.user)
            else:
                intermediate[p.role] = [p.user]
        gps = {}
        for keys, values in intermediate.items():
            gps[keys] = ', '.join(map(lambda x: '<a href="' + url_for('users.user_show', user_id=x.id) + '">' + BeautifulSoup(x.title, "lxml").text + '</a>', values))
        return gps
    
    @property
    def hosts(self):
        return db.session.scalars(sa.select(Host).join(Host.from_network, isouter=True).where(Network.project_id == self.id)).all()
    
    @property
    def services(self):
        return db.session.scalars(sa.select(Service).join(Service.host, isouter=True).join(Host.from_network, isouter=True).where(Network.project_id == self.id)).all()

    class Meta:
        verbose_name = _l("Project")
        verbose_name_plural = _l("Projects")
        icon = 'fa fa-home'
        icon_index = 'fa-solid fa-list-check'
        project_permission_actions = {'show': _l("Show object card"), 'update': _l("Edit and update object"), 'delete': _l("Delete object"),
                                      'edit_participants': _l("Edit participants of project"), "archive": _l("Archive project"), 'show_charts': _l("View status charts"),
                                      'show_additional_parameters': _l("Show additional parameters"), 'edit_additional_parameters': _l("Edit additional parameters")}
        global_permission_actions = {'index': _l("Show object list"), 'create': _l("Create object")}


@event.listens_for(SessionBase, 'before_commit')
def update_project_default_value_if_not_exist(session):
    projects = [p for p in session.new if isinstance(p, Project)]
    for project in projects:
        if project.file_directories == []:
            fd = FileDirectory(title='/', project=project, created_by_id=project.created_by_id)
            session.add(fd)


@project_enumerated_object
class ProjectRole(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    string_slug: so.Mapped[StringSlug]
    title: so.Mapped[str] = so.mapped_column(sa.String(35), info={'label': _l("Title")})
    description: so.Mapped[str] = so.mapped_column(info={'label': _l("Description")})
    actions: so.Mapped[List["RoleHasProjectObjectAction"]] = so.relationship(lazy='select', back_populates="role", cascade="all,delete-orphan", info={'label': _l("Actions on project objects"), 'on_form': False})

    class Meta:
        verbose_name = _l("Project role")
        verbose_name_plural = _l("Project roles")
        title_new = _l("Add new project role")
        icon = "fa-solid fa-person-walking-dashed-line-arrow-right"
        column_index = ['id', 'title', 'description']


class UserRoleHasProject(db.Model):
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True, info={'label': _l("User")})
    user: so.Mapped['User'] = so.relationship(lazy='joined', back_populates="project_roles", info={'label': _l("User")}) # type: ignore
    project_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Project.id, ondelete='CASCADE'), primary_key=True, info={'label': _l('Project')})
    project: so.Mapped[Project] = so.relationship(lazy='joined', info={'label': _l("Project")}, back_populates='participants')
    role_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(ProjectRole.id, ondelete='CASCADE'), primary_key=True, info={'label': _l("Project role")})
    role: so.Mapped[ProjectRole] = so.relationship(lazy='joined', info={'label': _l("Project role")})


class RoleHasProjectObjectAction(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    role_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(ProjectRole.id, ondelete='CASCADE'), info={'label': _l("Project role")})
    role: so.Mapped[ProjectRole] = so.relationship(lazy='joined', back_populates='actions', info={'label': _l("Project role")})
    object_class_name: so.Mapped[str] = so.mapped_column(sa.String(40), info={'label': _l("Project object")})
    action: so.Mapped[str] = so.mapped_column(sa.String(40), info={'label': _l("Object action")})
    is_granted: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l("Is granted")})

    __table_args__ = (
        sa.UniqueConstraint('role_id', 'object_class_name', 'action', name='unique_role_object_class_and_action_together'),
    )

    class Meta:
        verbose_name = _l("The rights of the role on the project")
        verbose_name_plural = _l("The rights of the role on the projects")