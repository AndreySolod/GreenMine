from app import db
from app.helpers.general_helpers import default_string_slug
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_babel import lazy_gettext as _l
from typing import Optional, Set
from app.helpers.admin_helpers import project_enumerated_object
import datetime


@project_enumerated_object
class ProjectAdditionalFieldGroup(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(100), info={'label': _l("Title")})
    order_number: so.Mapped[int] = so.mapped_column(info={'label': _l("Order number")})
    fields: so.Mapped[Set["ProjectAdditionalField"]] = so.relationship(lazy='select', back_populates="group", info={'label': _l("Additional fields"), 'on_form': False}, cascade='all,delete-orphan')

    def __repr__(self):
        return f"<ProjectAdditionalFieldGroup '{self.title}' with id='{self.id}'>"

    class Meta:
        verbose_name = _l("A group of additional project fields")
        verbose_name_plural = _l("Groups of additional project fields")
        title_new = _l("Add new group of additional project fields")
        column_index = ['id', 'string_slug', 'title', 'order_number']


class ProjectAdditionalField(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(150), info={'label': _l("Title")})
    help_text: so.Mapped[Optional[str]] = so.mapped_column(sa.String(150), info={'label': _l("Help text"), 'help_text': _l("The text that appears in the pop-up window")})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Description")})
    field_type: so.Mapped[str] = so.mapped_column(info={'label': _l("Field type")})
    group_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(ProjectAdditionalFieldGroup.id, ondelete='CASCADE'), info={'label': _l("Group")})
    group: so.Mapped[ProjectAdditionalFieldGroup] = so.relationship(lazy='select', back_populates="fields", info={'label': _l("Group")})
    project_fields: so.Mapped["ProjectAdditionalFieldData"] = so.relationship(lazy='select', back_populates='field_type', info={'label': _l("Created fields")}, cascade='all,delete')

    class Meta:
        verbose_name = _l("Project additional field")
        verbose_name_plural = _l("Project additional fields")
        icon = "fa-solid fa-building"
    
    @staticmethod
    def get_all_field_names():
        return {'StringField': _l("String field"), "TextAreaField": _l("Text Area Field"), "IntegerField": _l("Integer Field"),
                 "BooleanField": _l("Boolean Field"), "WysiwygField": _l("Wysiwyg Field")}

    def get_name_by_field_type(self):
        names = self.get_all_field_names()
        if self.field_type not in names:
            raise AttributeError(f"Looks like your database is corrupt: name '{self.field_type}' did not register in field names")
        return str(names[self.field_type])


class ProjectAdditionalFieldData(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    updated_at: so.Mapped[Optional[datetime.datetime]] = so.mapped_column(info={"label": _l("Updated at")})
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Updated by")})
    updated_by: so.Mapped["User"] = so.relationship(lazy='select', foreign_keys=[updated_by_id], info={"label": _l("Updated by")}) # type: ignore
    field_type_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(ProjectAdditionalField.id, ondelete='CASCADE'), info={'label': _l("Field type")})
    field_type: so.Mapped[ProjectAdditionalField] = so.relationship(lazy='select', back_populates="project_fields", info={'label': _l("Field type")})
    project_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project.id', ondelete='CASCADE'), info={'label': _l("Project")})
    project: so.Mapped["Project"] = so.relationship(lazy='select', info={'label': _l("Project")}, back_populates='additional_parameters') # type: ignore
    data: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Field data"), 'was_escaped': True})

    __table_args__ = (sa.UniqueConstraint('field_type_id', 'project_id', name='_unique_field_type_id_and_project_id_together'),)