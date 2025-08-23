from app import db
import sqlalchemy as sa
import sqlalchemy.orm as so
from typing import Optional
from flask_babel import lazy_gettext as _l, LazyString
from .datatypes import ID, StringSlug
import enum


class AuthenticationMethod(enum.Enum):
    PASSWORD = _l("Password")
    REQUEST_HEADER = _l("Request header")


class GlobalSettings(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    main_page_name: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l('Title of the cover page')})
    text_main_page: so.Mapped[str] = so.mapped_column(info={'label': _l('Text of the cover page')})
    default_language_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('application_language.id', ondelete='SET NULL'), info={'label': _l('Default application language')})
    default_language: so.Mapped["ApplicationLanguage"] = so.relationship(lazy='joined', info={'label': _l('Default application language')})
    m2m_join_symbol: so.Mapped[str] = so.mapped_column(sa.String(10), info={'label': _l("Many-To-Many join symbol in table cell")}, server_default=";<br>")
    m2m_max_items: so.Mapped[int] = so.mapped_column(default=4, server_default='4',
                                                     info={'label': _l("Many-To-Many max items in table cell")})
    pagination_element_count_select2: so.Mapped[int] = so.mapped_column(default=30, server_default='30', info={'label': _l("Select item count"), 'help_text': _l("The number of items that will be loaded into the selection field one at a time")})
    password_min_length: so.Mapped[int] = so.mapped_column(default=1, server_default='1',
                                                           info={'label': _l("Password min length")})
    password_lifetime: so.Mapped[int] = so.mapped_column(default=3650, server_default='3650',
                                                         info={'label': _l("Password lifetime (days)")})
    password_lowercase_symbol_require: so.Mapped[bool] = so.mapped_column(default=False, server_default=sa.false(), info={'label': _l("Required to use lowercase letters")})
    password_uppercase_symbol_require: so.Mapped[bool] = so.mapped_column(default=False, server_default=sa.false(),
                                                                          info={'label': _l("Required to use uppercase letters")})
    password_numbers_require: so.Mapped[bool] = so.mapped_column(default=False, server_default=sa.false(),
                                                                 info={'label': _l("Require to use numbers")})
    password_special_symbols_require: so.Mapped[bool] = so.mapped_column(default=False, server_default=sa.false(),
                                                                         info={'label': _l("Require to use specias symbols")})
    authentication_method: so.Mapped[AuthenticationMethod] = so.mapped_column(default=AuthenticationMethod.PASSWORD,
                                                             server_default=sa.text("PASSWORD"), info={'label': _l("Authentication method")})
    authentication_request_header_name: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l("Authentication request header name"), 'description': _l("A field name of request header, that contains a user login")}, server_default="X-User-Login")
    authentication_request_header_allow_registration: so.Mapped[bool] = so.mapped_column(default=False, server_default=sa.false(), info={'label': _l("Allow registration by request header"), 'description': _l("If true and user, that specified in request header is not exist - than specified user will be created")})
    

class ApplicationLanguage(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    string_slug: so.Mapped[StringSlug]
    title: so.Mapped[str] = so.mapped_column(sa.String(10), info={'label': _l('Title')})
    code: so.Mapped[str] = so.mapped_column(sa.String(8), info={'label': _l('Language code')})


class BackgroundTaskOptions(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l('Title')})
    description: so.Mapped[str]= so.mapped_column(sa.String(250), info={'label': _l('Parameter description')})
    module_name: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l('Module name')})
    inner_name: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l('Inner parameter name')})
    inner_value: so.Mapped[str] = so.mapped_column(sa.String(255), info={'label': _l('Parameter value')})