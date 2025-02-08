import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db
from app.helpers.general_helpers import utcnow
from app.helpers.admin_helpers import project_object_with_permissions
from datetime import datetime
from typing import Optional
from flask_babel import lazy_gettext as _l


@project_object_with_permissions
class ChatMessage(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    created_at: so.Mapped[datetime] = so.mapped_column(default=utcnow, info={'label': _l('Created at')})
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l('Added by')})
    created_by: so.Mapped["User"] = so.relationship(lazy='joined', foreign_keys='ChatMessage.created_by_id', info={'label': _l('Added by')}) # type: ignore
    project_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project.id', ondelete='CASCADE'), info={'label': _l('Project')})
    project: so.Mapped["Project"] = so.relationship(lazy='select', foreign_keys=[project_id], backref=so.backref("chat_messages", info={'label': _l("Chat messages")}, cascade="all, delete-orphan"), # type: ignore
                                                    info={'label': _l('Project')})
    text: so.Mapped[str] = so.mapped_column(info={'label': _l('Comment')})

    class Meta:
        verbose_name = _l('Chat message')
        verbose_name_plural = _l('Chat messages')
        icon = 'fa-solid fa-comments'
        project_permission_actions = {'index': _l("Show all chat message"), 'create': _l("Add new messages")}
