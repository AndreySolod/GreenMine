from app import db
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_babel import lazy_gettext as _l
from typing import Optional, Set
from app.helpers.admin_helpers import project_enumerated_object
from .datatypes import ID, StringSlug, UpdatedAt
import enum


@project_enumerated_object
class ProjectAdditionalFieldGroup(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    string_slug: so.Mapped[StringSlug]
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


class ProjectAdditionalParameterFieldType(enum.Enum):
    StringField = _l("String field")
    TextAreaField = _l("Text area field")
    IntegerField = _l("Integer field")
    BooleanField = _l("Boolean field")
    DateField = _l("Date field")
    WysiwygField = _l("Wysiwyg field")


class ProjectAdditionalField(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    string_slug: so.Mapped[StringSlug]
    title: so.Mapped[str] = so.mapped_column(sa.String(150), info={'label': _l("Title")})
    help_text: so.Mapped[Optional[str]] = so.mapped_column(sa.String(150), info={'label': _l("Help text"), 'help_text': _l("The text that appears in the pop-up window")})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Description")})
    field_type: so.Mapped[ProjectAdditionalParameterFieldType] = so.mapped_column(default=ProjectAdditionalParameterFieldType.StringField,
                                                                         info={'label': _l("Field type")}, server_default=sa.text("StringField"))
    group_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(ProjectAdditionalFieldGroup.id, ondelete='CASCADE'), info={'label': _l("Group")})
    group: so.Mapped[ProjectAdditionalFieldGroup] = so.relationship(lazy='select', back_populates="fields", info={'label': _l("Group")})
    project_fields: so.Mapped["ProjectAdditionalFieldData"] = so.relationship(lazy='select', back_populates='field_type', info={'label': _l("Created fields")}, cascade='all,delete')

    class Meta:
        verbose_name = _l("Project additional field")
        verbose_name_plural = _l("Project additional fields")
        icon = "fa-solid fa-building"
    

class ProjectAdditionalFieldData(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    updated_at: so.Mapped[UpdatedAt]
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Updated by")})
    updated_by: so.Mapped["User"] = so.relationship(lazy='select', foreign_keys=[updated_by_id], info={"label": _l("Updated by")}) # type: ignore
    field_type_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(ProjectAdditionalField.id, ondelete='CASCADE'), info={'label': _l("Field type")})
    field_type: so.Mapped[ProjectAdditionalField] = so.relationship(lazy='select', back_populates="project_fields", info={'label': _l("Field type")})
    project_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project.id', ondelete='CASCADE'), info={'label': _l("Project")})
    project: so.Mapped["Project"] = so.relationship(lazy='select', info={'label': _l("Project")}, back_populates='additional_parameters') # type: ignore
    data: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Field data"), 'was_escaped': True})

    __table_args__ = (sa.UniqueConstraint('field_type_id', 'project_id', name='_unique_field_type_id_and_project_id_together'),)