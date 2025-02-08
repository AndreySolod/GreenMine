from app import db
from flask import flash, has_request_context
from app.helpers.general_helpers import default_string_slug, utcnow
from app.helpers.admin_helpers import project_object_with_permissions
from typing import List, Set, Optional
from .files import FileData
import sqlalchemy as sa
import sqlalchemy.orm as so
import datetime
import wtforms
from app.controllers.forms import PickrColorField
from flask_babel import lazy_gettext as _l


@project_object_with_permissions
class ProjectReportTemplate(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    title: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l("Title")})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Description")})
    template_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('file_data.id', ondelete='CASCADE'), info={'label': _l("File template")})
    template: so.Mapped[FileData] = so.relationship(lazy='select', info={'label': _l("File template")})

    class Meta:
        verbose_name = _l("Report template")
        verbose_name_plural = _l("Report templates")
        icon = "fa-brands fa-squarespace"
        project_permission_actions = {'index': _l("Show object list"), 'create': _l("Generate new report from template")}