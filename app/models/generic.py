from app import db, sanitizer
from app.helpers.projects_helpers import create_history, load_history_script
from typing import List, Optional
from sqlalchemy import event
from .datatypes import JSONType, ID, CreatedAt, UpdatedAt, utcnow
import sqlalchemy as sa
import importlib
from sqlalchemy.orm import backref, foreign, remote, relationship
import sqlalchemy.orm as so
from sqlalchemy.orm.session import Session as SessionBase
from sqlalchemy.inspection import inspect
from markupsafe import Markup
from flask_babel import lazy_gettext as _l
from flask_babel import gettext
from flask_login import current_user
from flask_socketio import emit
from flask_sqlalchemy.model import camel_to_snake_case # Function to convert class name to table name in flask-sqlalchemy. Maybe change later...


class Reaction(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    is_positive: so.Mapped[bool]
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'))
    created_by: so.Mapped['User'] = so.relationship(lazy='select', foreign_keys="Reaction.created_by_id", back_populates='reactions') # type: ignore
    to_comment_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('comment.id', ondelete='CASCADE'))
    to_comment: so.Mapped['Comment'] = so.relationship(lazy='joined', back_populates='reactions')

    class Meta:
        verbose_name = _l("Reaction")
        verbose_name_plural = _l("Reactions")


class Comment(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    created_at: so.Mapped[CreatedAt]
    updated_at: so.Mapped[UpdatedAt]
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Created by")})
    created_by: so.Mapped['User'] = so.relationship(lazy='joined', foreign_keys='Comment.created_by_id', back_populates="created_comments", info={'label': "Created by"}) # type: ignore
    to_object_type: so.Mapped[str] = so.mapped_column(sa.String(50), index=True)
    to_object_id: so.Mapped[int]
    text: so.Mapped[str] = so.mapped_column(info={'label': _l("Text")})
    reply_to_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('comment.id', ondelete='CASCADE'), info={'label': _l("Reply to")})
    reply_to: so.Mapped["Comment"] = so.relationship(backref='replyed_comments', post_update=True,
                                                     lazy='select', join_depth=2,
                                                     foreign_keys='Comment.reply_to_id', remote_side=[id], info={'label': _l("Reply to")})
    reactions: so.Mapped[List["Reaction"]] = so.relationship(lazy='joined', back_populates="to_comment", cascade="all, delete-orphan", info={'label': _l("Reactions")})

    @property
    def to_object(self):
        return getattr(self, "to_object_%s" % self.to_object_type)

    def positive_reactions_count(self):
        return len(list(filter(lambda x: x.is_positive, self.reactions)))

    def negative_reactions_count(self):
        return len(list(filter(lambda x: not x.is_positive, self.reactions)))
    
    def has_reaction_by_user(self, user, is_positive: bool) -> bool:
        for reaction in self.reactions:
            if reaction.created_by_id == user.id and reaction.is_positive == is_positive:
                return True
        return False

    class Meta:
        verbose_name = _l("Comment")
        verbose_name_plural = _l("Comments")
        icon = "fa-solid fa-list"


class HasComment:
    """
    Mixin that used to create relationship with another classes for every parent object
    """

    @property
    def comments_desc(self):
        return list(reversed(self.comments))


@event.listens_for(HasComment, "mapper_configured", propagate=True)
def setup_listener_comment(mapper, class_):
    name = class_.__name__
    to_object_type = name.lower()
    class_.comments = relationship(
        Comment,
        primaryjoin=db.and_(
            class_.id == foreign(remote(Comment.to_object_id)),
            Comment.to_object_type == to_object_type,
        ),
        backref=backref(
            "to_object_%s" % to_object_type,
            primaryjoin=remote(class_.id) == foreign(Comment.to_object_id), overlaps="comments,to_object_%s,to_object_network,to_object_projecttask,to_object_host,to_object_credential,to_object_service,to_object_criticalvulnerability,to_object_issue,to_object_pentestresearchevent" % to_object_type
        ), order_by=(Comment.created_at.asc()), overlaps="comments,to_object_%s" % to_object_type, cascade="all, delete-orphan"
    )
    

    @event.listens_for(class_.comments, "append")
    def append_address(target, value, initiator):
        value.to_object_type = to_object_type


@event.listens_for(SessionBase, 'before_commit')
def update_datetime_comment_update(session):
    comments = [c for c in session.dirty if isinstance(c, Comment)]
    for comm in comments:
        comm.updated_at = utcnow()


class HasHistory:
    def __init_subclass__(cls):
        if hasattr(cls, '__tablename__'):
            new_table_name = cls.__tablename__
        else:
            new_table_name = camel_to_snake_case(cls.__name__)
        def as_text(self):
            """ Returned changes from history object as text value """
            if 'changes' not in self.changes:
                return ''
            param_text_list = []
            models = importlib.import_module('app.models')
            for history_element in self.changes['changes']:
                old_value = history_element['attrs'].get('old_value')
                new_value = history_element['attrs'].get('new_value')
                if history_element['action'] == 'modify_paramether':
                    param_text_list.append(_l("The value of the <b>«%(param_name)s»</b> was changed from <b>«%(old_value)s»</b> to <b>«%(new_value)s»</b>",
                                              param_name=gettext(history_element['attrs']['lazy_name']), old_value=sanitizer.sanitize(old_value),
                                              new_value=sanitizer.sanitize(new_value)))
                elif history_element['action'] == 'add_paramether':
                    param_text_list.append(_l("The <b>«%(param_name)s»</b> paramether is set to «%(new_value)s» value",
                                              param_name=gettext(history_element['attrs']['lazy_name']), new_value=sanitizer.sanitize(new_value)))
                elif history_element['action'] == 'delete_paramether':
                    param_text_list.append(_l("The <b>«%(param_name)s»</b> paramether, previously set to <b>«%(old_value)s»</b>, has been deleted",
                                              param_name=gettext(history_element['attrs']['lazy_name']), old_value=sanitizer.sanitize(old_value)))
                elif history_element['action'] == 'add_m2m_paramether':
                    attr_title = history_element['attrs']['title_attr']
                    value_class = getattr(models, history_element['attrs']['values_class'])
                    new_values = ", ".join([f"«<b>{getattr(x, attr_title)}</b>»" for x in db.session.scalars(sa.select(value_class).where(value_class.id.in_(history_element['attrs']['new_value'])))])
                    param_text_list.append(_l("The values %(new_value)s has been added to the paramether «%(param_name)s»",
                                              param_name=gettext(history_element['attrs']['lazy_name']), new_value=sanitizer.sanitize(new_values)))
                elif history_element['action'] == 'delete_m2m_paramether':
                    attr_title = history_element['attrs']['title_attr']
                    value_class = getattr(models, history_element['attrs']['values_class'])
                    removed_values = ", ".join([f"«<b>{getattr(x, attr_title)}</b>»" for x in db.session.scalars(sa.select(value_class).where(value_class.id.in_(history_element['attrs']['old_value'])))])
                    param_text_list.append(_l("The values %(old_value)s have been removed from the paramether «%(param_name)s»",
                                              param_name=gettext(history_element['attrs']['lazy_name']), old_value=sanitizer.sanitize(removed_values)))
                elif history_element['action'] == 'add_comment':
                    param_text_list.append(_l("Added a comment:<b><br />%(comment_text)s</b>", comment_text=history_element['attrs']['comment_text']))
            return str('<br />\n'.join(map(str, param_text_list)))
        
        def as_markup_text(self):
            ''' Returned changes from history object as Markup text value '''
            return Markup(self.as_text())
        params = {'id': sa.Column(sa.Integer(), primary_key=True),
                  'created_at': sa.Column(sa.DateTime(), default=utcnow),
                  'changes': sa.Column(JSONType(), info={'label': _l("Changes in object")}),
                  'to_object_id': sa.Column(sa.ForeignKey(new_table_name + ".id", ondelete='CASCADE')),
                  'to_object': so.relationship(cls.__name__, back_populates='history', lazy='select'),
                  'created_by_id': sa.Column(sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
                  'created_by': so.relationship("User", lazy='joined'), 'as_text': as_text, 'as_markup_text': as_markup_text}
        if hasattr(cls,'__tablename__'):
            params['__tablename__'] = cls.__tablename__ + '_history'
        history_object = type(cls.__name__ + "History", (db.Model,), params)
        history_object.load_history_script = staticmethod(load_history_script)
        cls.history = so.relationship(history_object, back_populates="to_object", lazy='select', cascade='all,delete', order_by=(history_object.created_at.asc()))

        @event.listens_for(history_object, 'after_insert')
        def emit_signal_new_history_element(mapper, connection, target):
            emit('history element added', {'id': target.id}, namespace='/generic', to=f"{cls.__name__}:{target.to_object.id}")

@event.listens_for(SessionBase, 'before_commit')
def create_history_for_objects(session):
    object_elements = [u for u in session.dirty if hasattr(u, 'history')]
    create_history(session, object_elements)


@event.listens_for(SessionBase, 'before_commit')
def updated_paramethers_updated_by_id_if_exist(session):
    object_elements = [u for u in session.dirty if hasattr(u, 'updated_by_id')]
    if current_user != None and not current_user.is_anonymous:
        for i in object_elements:
            i.updated_by_id = current_user.id


class UserNotification(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    to_user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id', ondelete='CASCADE'), info={'label': _l("Refer to user")})
    to_user: so.Mapped["User"] = so.relationship(foreign_keys=[to_user_id], lazy='select', backref=so.backref("notifications", info={'label': _l("User notifications")}, cascade='all,delete-orphan', # type: ignore
                                                                                                              order_by="UserNotification.created_at.desc()"),
                                                 info={'label': _l('Refer to user')})
    by_user_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("By user")})
    by_user: so.Mapped["User"] = so.relationship(foreign_keys=[by_user_id], lazy='joined', info={'label': _l("By user")}) # type: ignore
    description: so.Mapped[str] = so.mapped_column(info={'label': _l("Description")})
    technical_info: so.Mapped[Optional[dict]] = so.mapped_column(JSONType(), info={'label': _l("Technical detaled")})
    link_to_object: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l("Link to object")})
    created_at: so.Mapped[CreatedAt]

    class Meta:
        verbose_name = _l("Notification")
        verbose_name_plural = _l("Notifications")


@event.listens_for(UserNotification, 'after_insert')
def emit_signal_new_notification_to_user(mapper, connection, target):
    emit('new notification', {'notification_id': target.id}, namespace='/user', to=str(target.to_user_id))


@event.listens_for(SessionBase, 'after_commit')
def commit_technical_session_after_default_session(session):
    if (not 'is_technical' in session.info):
        db.technical_session.commit()


@event.listens_for(SessionBase, 'before_commit')
def clean_all_model_fields_from_xss(session):
    ''' Clean all new and dirty object from XSS tags via sanitizer.'''
    all_objs = [o for o in session.new]
    all_objs += [o for o in session.dirty]
    for o in all_objs:
        attrs = inspect(o.__class__).column_attrs
        for a in attrs:
            if a.columns[0].type.python_type != str or a.columns[0].info.get('was_escaped'):
                continue
            now_attr_data = getattr(o, a.key)
            if isinstance(now_attr_data, str):
                sanitized_data = sanitizer.sanitize(now_attr_data)
                if a.columns[0].type.length is None:
                    setattr(o, a.key, sanitized_data)
                elif len(sanitized_data) > a.columns[0].type.length:
                    now_attr_data = now_attr_data[:len(now_attr_data) - 1:]
                    while len(sanitizer.sanitize(now_attr_data)) > a.columns[0].type.length:
                        now_attr_data = now_attr_data[:len(now_attr_data) - 1:]
                setattr(o, a.key, sanitizer.sanitize(now_attr_data))
            