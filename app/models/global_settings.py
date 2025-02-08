from app import db
import sqlalchemy as sa
import sqlalchemy.orm as so
from typing import Optional
from app.helpers.general_helpers import default_string_slug
from flask_babel import lazy_gettext as _l


class GlobalSettings(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    main_page_name: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l('Title of the cover page')})
    text_main_page: so.Mapped[str] = so.mapped_column(info={'label': _l('Text of the cover page')})
    default_language_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('application_language.id', ondelete='SET NULL'), info={'label': _l('Default application language')})
    default_language: so.Mapped["ApplicationLanguage"] = so.relationship(lazy='joined', info={'label': _l('Default application language')})

class ApplicationLanguage(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l('Slug')})
    title: so.Mapped[str] = so.mapped_column(sa.String(10), info={'label': _l('Title')})
    code: so.Mapped[str] = so.mapped_column(sa.String(8), info={'label': _l('Language code')})


class BackgroundTaskOptions(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    title: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l('Title')})
    description: so.Mapped[str]= so.mapped_column(sa.String(250), info={'label': _l('Parameter description')})
    module_name: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l('Module name')})
    inner_name: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l('Inner parameter name')})
    inner_value: so.Mapped[str] = so.mapped_column(sa.String(255), info={'label': _l('Parameter value')})