from app import db
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from app.helpers.admin_helpers import project_enumerated_object, project_object_with_permissions
from app.controllers.forms import PickrColorField
from flask_babel import lazy_gettext as _l
from .datatypes import ID, StringSlug, CreatedAt, UpdatedAt, Archived


@project_enumerated_object
class NoteImportance(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    string_slug: so.Mapped[StringSlug]
    title: so.Mapped[str] = so.mapped_column(sa.String(40), info={'label': _l("Title")})
    color: so.Mapped[Optional[str]] = so.mapped_column(sa.String(60), info={'label': _l("Color"), 'form': PickrColorField})

    class Meta:
        verbose_name = _l("The importance of the note")
        verbose_name_plural = _l("Importances of the note")
        title_new = _l("Add the importance of a note")
        description = _l('It is used in notes in the project in order to highlight a particular note with a certain color')
        column_index = ['id', 'string_slug', 'title', 'color']


@project_object_with_permissions
class Note(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    archived: so.Mapped[Archived]
    created_at: so.Mapped[CreatedAt]
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Created by")})
    created_by: so.Mapped["User"] = so.relationship(lazy='select', foreign_keys=[created_by_id], info={'label': _l("Created by")}) # type: ignore
    updated_at: so.Mapped[UpdatedAt]
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete="SET NULL"), info={'label': _l("Updated by")})
    updated_by: so.Mapped['User'] = so.relationship(lazy='select', foreign_keys=[updated_by_id], info={'label': _l("Updated by")}) # type: ignore
    title: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l("Title")})
    description: so.Mapped[str] = so.mapped_column(info={'label': _l("The body of the note")})
    importance_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(NoteImportance.id, ondelete='SET NULL'), info={'label': _l("Importance")})
    importance: so.Mapped[NoteImportance] = so.relationship(lazy='joined', info={'label': _l("Importance")})
    project_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project.id', ondelete='CASCADE'), info={'label': _l("Project")})
    project: so.Mapped['Project'] = so.relationship(lazy='select', back_populates="notes", info={'label': _l("Project")}) # type: ignore

    class Meta:
        verbose_name = _l("Note")
        verbose_name_plural = _l("Notes")
        icon = 'fa-solid fa-note-sticky'
        icon_index = 'fa-solid fa-note-sticky'
        project_permission_actions = {'index': _l("Show object list"), 'create': _l("Create new object"), 'update': _l("Edit and update object"),
                                      'delete': _l("Delete object")}
