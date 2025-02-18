from app import db
from app.helpers.general_helpers import default_string_slug, utcnow
from app.helpers.admin_helpers import project_enumerated_object, project_object_with_permissions
from app.models.datatypes import LimitedLengthString
from .generic import HasComment, HasHistory
from typing import List, Set, Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.orm.session import Session as SessionBase
from sqlalchemy import event
import datetime
import wtforms
from flask_babel import lazy_gettext as _l


class HashTypeHasPrototype(db.Model):
    hash_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('hash_type.id'), primary_key=True)
    prototype_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('hash_prototype.id'), primary_key=True)


@project_enumerated_object
class HashPrototype(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    regex: so.Mapped[str] = so.mapped_column(sa.String(500), unique=True, index=True, info={'label': _l("Regular Expression"), 'was_escaped': True})
    title = so.synonym('regex')
    hash_types: so.Mapped[Set["HashType"]] = so.relationship(secondary=HashTypeHasPrototype.__table__, primaryjoin='HashPrototype.id==HashTypeHasPrototype.prototype_id', secondaryjoin='HashTypeHasPrototype.hash_id==HashType.id', back_populates='regexs', lazy='select', info={'label': _l("Hash types")})

    class Meta:
        verbose_name = _l("Hash prototype")
        verbose_name_plural = _l("Hash prototypes")
        title_new = _l("Add hash prototype")
        column_index = ['id', 'regex', 'hash_types']


@project_enumerated_object
class HashType(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    archived: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l('Archived')})
    string_slug: so.Mapped[str] = so.mapped_column(LimitedLengthString(80), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(80), info={'label': _l("Title")})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Hash description"), 'form': wtforms.TextAreaField})
    hashcat_mode: so.Mapped[Optional[str]] = so.mapped_column(sa.String(20), info={'label': _l('HashCat-mode')})
    john_mode: so.Mapped[Optional[str]] = so.mapped_column(sa.String(40), info={'label': _l('JohnTheRipper-mode')})
    is_popular: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l('A popular type')})
    extended: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l('Extended mode')})
    regexs: so.Mapped[Set["HashPrototype"]] = so.relationship(secondary=HashTypeHasPrototype.__table__, primaryjoin="HashType.id==HashTypeHasPrototype.hash_id", secondaryjoin="HashTypeHasPrototype.prototype_id==HashPrototype.id", back_populates='hash_types', lazy='select', info={'label': _l('Regular Expressions')})

    def to_send_dict(self):
        return {'title': self.title, 'description': self.description, 'hashcat_mode': self.hashcat_mode, 'john_mode': self.john_mode, 'is_popular': self.is_popular}

    class Meta:
        verbose_name = _l('Hash type')
        verbose_name_plural = _l('Hash types')
        title_new = _l('Add hash type')
        column_index = ['id', 'archived', 'string_slug', 'title', 'description', 'hashcat_mode', 'john_mode', 'is_popular', 'extended']


@project_enumerated_object
class CheckWordlist(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l('Slug')})
    title: so.Mapped[str] = so.mapped_column(sa.String(40), info={'label': _l('Title')})
    description: so.Mapped[str] = so.mapped_column(info={'label': _l('Description'), 'form': wtforms.TextAreaField})

    class Meta:
        verbose_name = _l('Wordlist')
        verbose_name_plural = _l('Wordlists')
        title_new = _l('Add new wordlist')
        column_index = ['id', 'string_slug', 'title', 'description']


class CredentialByService(db.Model):
    credential_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('credential.id', ondelete='CASCADE'), primary_key=True)
    service_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('service.id', ondelete='CASCADE'), primary_key=True)


class CredentialByReceivedHost(db.Model):
    credential_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('credential.id', ondelete='CASCADE'), primary_key=True)
    host_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('host.id', ondelete='CASCADE'), primary_key=True)


@project_object_with_permissions
class Credential(HasComment, db.Model, HasHistory):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    archived: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l('Archived')})
    project_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project.id', ondelete='CASCADE'), info={'label': _l('Project')})
    project: so.Mapped["Project"] = db.relationship(lazy='select', backref=so.backref('credentials', cascade='all, delete-orphan'), info={'label': _l('Project')}) # type: ignore
    created_at: so.Mapped[datetime.datetime] = so.mapped_column(default=utcnow, info={"label": _l("Created at")})
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l('Created by')})
    created_by: so.Mapped["User"] = so.relationship(lazy='select', foreign_keys="Credential.created_by_id", info={'label': _l('Created by')}) # type: ignore
    updated_at: so.Mapped[Optional[datetime.datetime]] = so.mapped_column(info={"label": _l('Updated at')})
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete="SET NULL"), info={'label': _l('Updated by')})
    updated_by: so.Mapped['User'] = so.relationship(lazy='select', foreign_keys="Credential.updated_by_id", info={'label': _l('Updated by')}) # type: ignore
    login: so.Mapped[str] = so.mapped_column(sa.String(40), info={'label': _l('Login')})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l('Additional information')})
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l('Password hash')})
    hash_type_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(HashType.id, ondelete='SET NULL'), info={'label': _l('Hash type')})
    hash_type: so.Mapped['HashType'] = so.relationship(lazy='select', info={'label': _l('Hash type')})
    check_wordlist_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(CheckWordlist.id, ondelete='SET NULL'),
                                                                   info={'label': _l("Checked on wordlist")})
    check_wordlist: so.Mapped['CheckWordlist'] = so.relationship(lazy='select', info={'label': _l("Checked on wordlist")})
    password: so.Mapped[Optional[str]] = so.mapped_column(sa.String(70), info={'label': _l('Password')})
    services: so.Mapped[Set["Service"]] = so.relationship(secondary=CredentialByService.__table__, primaryjoin=id==CredentialByService.credential_id, # type: ignore
                                                           secondaryjoin='CredentialByService.service_id==Service.id', back_populates='credentials',
                                                           lazy='select', info={'label': _l("Related services")})
    is_pentest_credentials: so.Mapped[bool] = so.mapped_column(default=False, index=True, info={'label': _l("Only for pentest")})
    received_from: so.Mapped[Set["Host"]] = so.relationship(secondary=CredentialByReceivedHost.__table__, primaryjoin=id==CredentialByReceivedHost.credential_id, # type: ignore
                                                             secondaryjoin="CredentialByReceivedHost.host_id==Host.id", lazy='select',
                                                             info={'label': _l("Comprometation source"), 'help_text': _l("An source host in which a credential were be founded")})

    @property
    def fulltitle(self):
        return _l("Credential #%(cred_id)s for login «%(login)s»", cred_id=self.id, login=self.login)
    
    @property
    def treeselecttitle(self):
        return f'{self.login}:{self.password}'

    @property
    def service_list_as_text(self):
        return '\n'.join([i.shorttitle for i in self.services])

    class Meta:
        verbose_name = _l("Credential")
        verbose_name_plural = _l("Credentials")
        icon = 'fa-solid fa-key'
        icon_index = 'fa-solid fa-key'
        title_new = _l("Add new credential")
        project_permission_actions = {'index': _l("Show object list"), 'pentest_index': _l("Show created object list"), 'create': _l("Create new object"), 'show': _l("Show object card"),
                                      'update': _l("Edit and update object"), 'delete': _l("Delete object"), 'add_comment': _l("Add comment to object"),
                                      'show_comments': _l("Show comment list of object"), 'show_history': _l("Show object history")}


class CredentialImportTemplate(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    string_slug: so.Mapped[str] = so.mapped_column(LimitedLengthString(80), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(80), info={'label': _l("Title")})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Template description")})
    login_column_number: so.Mapped[Optional[int]] = so.mapped_column(info={'label': _l("Login column number")})
    password_hash_column_number: so.Mapped[Optional[int]] = so.mapped_column(info={'label': _l("Password hash column number")})
    description_column_number: so.Mapped[Optional[int]] = so.mapped_column(info={'label': _l("Additional description column number")})
    password_column_number: so.Mapped[Optional[int]] = so.mapped_column(info={'label': _l("Password column number")})
    static_login: so.Mapped[Optional[str]] = so.mapped_column(sa.String(Credential.login.type.length), info={'label': _l("Static login")})
    static_password_hash: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Static password hash")})
    static_hash_type_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(HashType.id, ondelete='CASCADE'), info={'label': _l("Static hash type")})
    static_hash_type: so.Mapped[HashType] = so.relationship(lazy='select', info={'label': _l("Static hash type")})
    static_check_wordlist_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(CheckWordlist.id, ondelete='CASCADE'), info={'label': _l("Static check wordlist")})
    static_check_wordlist: so.Mapped[CheckWordlist] = so.relationship(lazy='select', info={'label': _l("Static check wordlist")})
    static_description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Static description")})
    
    class Meta:
        verbose_name = _l("Credential import template")
        verbose_name_plural = _l("Credential import templates")
        icon = 'fa-brands fa-keycdn'