from app import db, login, logger
from flask import current_app
from app.helpers.general_helpers import default_string_slug, utcnow
from app.helpers.users_helpers import generate_avatar
from app.helpers.admin_helpers import project_enumerated_object
from unidecode import unidecode
import datetime
import os
import os.path
from typing import List, Optional
from app.extensions.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy import event
from sqlalchemy.orm.session import Session as SessionBase
from sqlalchemy.ext.hybrid import hybrid_property
import sqlalchemy.exc as exc
from .generic import Comment, Reaction
from .files import FileData
from markupsafe import Markup
from flask_babel import lazy_gettext as _l
import secrets
import json
from .global_settings import ApplicationLanguage


@project_enumerated_object
class UserPosition(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    title: so.Mapped[str] = so.mapped_column(sa.String(35), info={'label': _l("Title")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    is_default: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l("Default")})

    def __repr__(self):
        return f"<UserPosition '{self.title}', is_default={self.is_default}>"

    class Meta:
        verbose_name = _l("Position")
        verbose_name_plural = _l("Positions")
        title_new = _l("Add new position")
        column_index = ['id', 'string_slug', 'title', 'is_default']


class UserHasProgramLanguage(db.Model):
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
    programming_language_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('programming_language.id', ondelete='CASCADE'), primary_key=True)


@project_enumerated_object
class ProgrammingLanguageClass(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l(_l("ID"))})
    string_slug: so.Mapped[int] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l("Title")})
    programming_languages: so.Mapped[List["ProgrammingLanguage"]] = so.relationship(back_populates='language_class', cascade="all, delete-orphan", info={'label': _l("Programming languages")})

    @hybrid_property
    def treeselecttitle(self):
        return self.title

    def __repr__(self):
        return f"<ProgrammingLanguageClass '{self.title}' with id={self.id}>"

    def child(self):
        return self.programming_languages

    class Meta:
        verbose_name = _l("A class of programming languages")
        verbose_name_plural = _l("Classes of programming languages")
        title_new = _l("Add a new class of programming languages")
        description = _l("It is used to group programming languages")
        column_index = ['id', 'string_slug', 'title', 'programming_languages']


@project_enumerated_object
class ProgrammingLanguage(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l(_l("ID"))})
    title: so.Mapped[str] = so.mapped_column(sa.String(40), unique=True, info={'label': _l("Title")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    alias: so.Mapped[str] = so.mapped_column(sa.String(20), unique=True, info={'label': _l("Alias"), 'help_text': _l("A string used in the HTML code to denote a given language")})
    is_default: so.Mapped[bool] = so.mapped_column(default=False,  info={'label': _l("Is the default language")})
    language_class_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(ProgrammingLanguageClass.id, ondelete='CASCADE'), info={'label': _l("Belongs to the class")})
    language_class: so.Mapped["ProgrammingLanguageClass"] = so.relationship(lazy='joined', back_populates='programming_languages', info={'label': _l("Belongs to the class")})

    def parent(self):
        return self.language_class

    @hybrid_property
    def treeselecttitle(self):
        return self.title

    def __repr__(self):
        return f"<ProgrammingLanguage '{self.title}'>"

    class Meta:
        verbose_name = _l("Programming language")
        verbose_name_plural = _l("Programming languages")
        title_new = _l("Add new programming language")
        description = _l("It is used to indicate to CKEditor the need to mark a block of code with the appropriate language for further coloring of the code")
        column_index = ['id', 'string_slug', 'title', 'alias', 'is_default', 'language_class.title-select']


@project_enumerated_object
class ProgrammingLanguageTheme(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l(_l("ID"))})
    title: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l("Title")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    directory: so.Mapped[str] = so.mapped_column(sa.String(30), default='', info={'label': _l("Directory")})
    filename: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l("File Name")})
    is_default: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l("Default")})

    def __repr__(self):
        return f"<ProgrammingLanguageTheme '{self.title}' in directory '{self.directory}'>"

    def relative_path(self):
        return os.path.join(self.directory, self.filename)

    class Meta:
        verbose_name = _l("The theme of the programming language")
        verbose_name_plural = _l("Themes of programming languages")
        title_new = _l("Add a new programming languages theme")
        column_index = ['id', 'string_slug', 'title', 'directory', 'filename', 'is_default']



class UserHasTeam(db.Model):
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
    team_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('team.id', ondelete='CASCADE'), primary_key=True)


def default_user_string_slug(context):
    return unidecode(context.get_current_parameters()["login"])


def default_user_token():
    return secrets.token_urlsafe(45)


class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    created_at: so.Mapped[datetime.datetime] = so.mapped_column(info={'label': _l("Created at")}, default=utcnow)
    string_slug: so.Mapped[int] = so.mapped_column(sa.String(20), unique=True, index=True, default=default_user_string_slug, info={'label': _l("Slug")})
    archived: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l("Archived")})
    login: so.Mapped[str] = so.mapped_column(sa.String(20), index=True, unique=True, info={'label': _l("Login")})
    password_hash: so.Mapped[str] = so.mapped_column(sa.String(170), default='', info={'label': _l("Password hash")})
    email: so.Mapped[Optional[str]] = so.mapped_column(sa.String(30), info={'label': _l("E-Mail")})
    first_name: so.Mapped[str] = so.mapped_column(sa.String(20), default='', info={'label': _l("First Name")})
    last_name: so.Mapped[str] = so.mapped_column(sa.String(30), default='', info={'label': _l("Last Name")})
    middle_name: so.Mapped[str] = so.mapped_column(sa.String(30), default='', info={'label': _l("Patronymic")})
    is_administrator: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l("Is an administrator")})
    avatar_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('file_data.id', ondelete='CASCADE'), info={'label': _l("Avatar")})
    avatar: so.Mapped["FileData"] = so.relationship(lazy='select', foreign_keys=[avatar_id], info={'label': _l("Avatar")})
    manager_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Immediate supervisor")})
    manager: so.Mapped["User"] = so.relationship(backref='subordinates', post_update=True,
                                                 lazy='select', join_depth=2,
                                                 foreign_keys=[manager_id], remote_side=[id], info={'label': _l("Immediate supervisor")})
    position_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user_position.id', ondelete='SET NULL'), info={'label': _l("Position")})
    position: so.Mapped["UserPosition"] = so.relationship(lazy='select', info={'label': _l("Position")})
    programming_language_theme_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(ProgrammingLanguageTheme.id, ondelete='SET NULL'),
                                                                               info={'label': _l("Programming language theme")})
    programming_language_theme: so.Mapped["ProgrammingLanguageTheme"] = so.relationship(foreign_keys=[programming_language_theme_id],
                                                                                        lazy='select', info={'label': _l("Programming language theme")})
    programming_languages: so.Mapped[List["ProgrammingLanguage"]] = so.relationship(secondary=UserHasProgramLanguage.__table__,
                                                                                    primaryjoin="User.id==UserHasProgramLanguage.user_id",
                                                                                    secondaryjoin="UserHasProgramLanguage.programming_language_id==ProgrammingLanguage.id",
                                                                                    info={'label': _l("Programming languages used")})
    theme_style_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user_theme_style.id', ondelete='SET NULL'), info={'label': _l("Interface design theme")})
    theme_style: so.Mapped["UserThemeStyle"] = so.relationship(lazy="select", foreign_keys=[theme_style_id], info={'label': _l("Interface design theme")})
    teams: so.Mapped[List["Team"]] = so.relationship(secondary=UserHasTeam.__table__,
                                                     primaryjoin="User.id==UserHasTeam.user_id",
                                                     secondaryjoin="Team.id==UserHasTeam.team_id",
                                                     back_populates="users",
                                                     info={'label': _l("Member of the team")})
    created_comments: so.Mapped[List["Comment"]] = so.relationship(foreign_keys=[Comment.created_by_id], back_populates="created_by",
                                                                   info={'label': _l("Added comments")})
    reactions: so.Mapped[List["Reaction"]] = so.relationship(foreign_keys=[Reaction.created_by_id], back_populates="created_by", info={'label': _l("Reactions")})
    token: so.Mapped[str] = so.mapped_column(sa.String(60), default=default_user_token, index=True, unique=True, info={'label': _l("Token")})
    token_expiration: so.Mapped[datetime.datetime] = so.mapped_column(default=utcnow, info={'label': _l("Token expiration")})
    environment_setting: so.Mapped["UserEnvironmentSetting"] = so.relationship(back_populates='to_user', lazy='joined', cascade='all, delete-orphan', info={'label': _l("Environment settings")})
    preferred_language_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('application_language.id', ondelete='SET NULL'), info={'label': _l("Preferred language")})
    preferred_language: so.Mapped["ApplicationLanguage"] = so.relationship(lazy='select', info={'label': _l("Preferred language")}) # type: ignore
    project_roles: so.Mapped["UserRoleHasProject"] = so.relationship(lazy='select', info={'label': _l("Roles on project")}, back_populates="user") # type: ignore

    @hybrid_property
    def title(self):
        return self.last_name + " " + self.first_name + " " + self.middle_name

    @hybrid_property
    def treeselecttitle(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_token(self):
        now = utcnow()
        if self.token and self.token_expiration > now + datetime.timedelta(seconds=current_app.config["TOKEN_EXPIRATION"]):
            return self.token
        self.token = default_user_token()
        self.token_expiration = now + datetime.timedelta(seconds=current_app.config["TOKEN_EXPIRATION"])
        db.session.add(self)
        db.session.commit()
        return self.token

    def revoke_token(self):
        self.token = utcnow() - datetime.timedelta(seconds=1)
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def check_token(token):
        user = db.session.scalars(sa.select(User).where(User.token == token)).first()
        if user is None or user.token_expiration < utcnow():
            return None
        return user

    def get_js_list_programming_languages(self):
        ''' Returns a list of programming languages in json format for CKEditor '''
        return json.dumps({'languages': [{'language': i.alias, 'label': i.title} for i in self.programming_languages]})

    def __repr__(self):
        return f"<User '{self.login}' with id={self.id}>"
    
    @staticmethod
    def get_list_mentions():
        return json.dumps({'mentions': ["@" + i for i in db.session.scalars(sa.select(User.login).where(User.archived == False)).all()]})

    class Meta:
        verbose_name = _l("User")
        verbose_name_plural = _l("Users")


class UserThemeStyle(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug)
    title: so.Mapped[str] = so.mapped_column(sa.String(40))
    is_default: so.Mapped[bool] = so.mapped_column(default=False)
    main_color: so.Mapped[str] = so.mapped_column(sa.String(60))
    neightboring_main_color: so.Mapped[str] = so.mapped_column(sa.String(60))
    secondary_main_color: so.Mapped[str] = so.mapped_column(sa.String(60))
    main_text_color: so.Mapped[str] = so.mapped_column(sa.String(60))
    hovering_main_element_color: so.Mapped[str] = so.mapped_column(sa.String(60))
    sidebar_background_color: so.Mapped[str] = so.mapped_column(sa.String(60))
    main_content_background_color: so.Mapped[str] = so.mapped_column(sa.String(60))
    color_card_background_header: so.Mapped[str] = so.mapped_column(sa.String(60))
    color_chats_hour: so.Mapped[str] = so.mapped_column(sa.String(40))
    color_chats_my_message: so.Mapped[str] = so.mapped_column(sa.String(40))
    color_chats_my_message_text: so.Mapped[str] = so.mapped_column(sa.String(40))
    color_chats_other_message: so.Mapped[str] = so.mapped_column(sa.String(40))
    color_chats_other_message_text: so.Mapped[str] = so.mapped_column(sa.String(40))
    bs_card_color: so.Mapped[str] = so.mapped_column(sa.String(40))
    dark_color: so.Mapped[str] = so.mapped_column(sa.String(40))
    timeline_time_color: so.Mapped[str] = so.mapped_column(sa.String(40), server_default="#8796af")
    timeline_line_color: so.Mapped[str] = so.mapped_column(sa.String(40), server_default="#000")
    timeline_red_team_background_color: so.Mapped[str] = so.mapped_column(sa.String(40), server_default="rgb(138, 2, 2)")
    timeline_red_team_text_color: so.Mapped[str] = so.mapped_column(sa.String(40), server_default="#fff")
    timeline_blue_team_background_color: so.Mapped[str] = so.mapped_column(sa.String(40), server_default="rgb(0, 0, 138)")
    timeline_blue_team_text_color: so.Mapped[str] = so.mapped_column(sa.String(40), server_default="#fff")
    fixed_sidebar: so.Mapped[bool] = so.mapped_column(default=False)
    sidebar_position_left: so.Mapped[bool] = so.mapped_column(default=True)
    

    @hybrid_property
    def sidebar_class(self):
        if self.fixed_sidebar:
            return "app-side fixed"
        else:
            return 'app-side'

    class Meta:
        verbose_name = _l("Theme style")
        verbose_name_plural = _l("Theme styles")


class UserEnvironmentSetting(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    to_user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id, ondelete='CASCADE'), unique=True)
    to_user: so.Mapped['User'] = so.relationship(lazy='joined', back_populates='environment_setting')
    sidebar_hide: so.Mapped[bool] = so.mapped_column(default=True, info={'label': _l("The sidebar is in a hidden state")})
    comment_order_asc: so.Mapped[bool] = so.mapped_column(default=True, info={'label': _l("The order of comments"), 'comment': _l("True if direct and False otherwise")})
    comment_reply_padding: so.Mapped[int] = so.mapped_column(default=40, info={'label': _l("The indentation from the previous comment to respond to the message in pixels")})

    @hybrid_property
    def sidebar_class(self):
        if self.sidebar_hide:
            return "is-mini"
        else:
            return ""

    class Meta:
        verbose_name = _l("User's Environment Settings")
        verbose_name_plural = _l("User Environment Settings")


@event.listens_for(SessionBase, 'before_commit')
def update_user_default_value_if_not_exist(session):
    users = [u for u in session.dirty if isinstance(u, User)]
    users += [u for u in session.new if isinstance(u, User)]
    for user in users:
        if user.avatar_id is None or user.avatar is None:
            f = FileData(extension="png", title=f'{user.login}\'s avatar', description=f"Avatar for user «{user.login}»")
            f.data = generate_avatar(480, user.login)
            user.avatar = f

        if (user.position_id is None and user.position is None):
            pos = session.scalars(sa.select(UserPosition).where(UserPosition.is_default==True)).first()
            user.position = pos

        if (user.theme_style_id is None and user.theme_style is None):
            t = session.scalars(sa.select(UserThemeStyle).where(UserThemeStyle.is_default==True)).first()
            user.theme_style = t

        if (user.environment_setting is None):
            es = UserEnvironmentSetting()
            session.add(es)
            user.environment_setting = es
        
        if (user.preferred_language is None):
            try:
                pf = session.scalars(sa.select(ApplicationLanguage).where(ApplicationLanguage.string_slug == 'auto')).one()
                user.preferred_language = pf
            except (exc.MultipleResultsFound, exc.NoResultFound):
                logger.error("Application language with string_slug 'auto' does not exist!")


@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))


@login.request_loader
def request_user_load(request):
    api_key = request.headers.get('Rest-Api-Key')
    if api_key:
        return db.session.scalars(sa.select(User).where(User.tokey==api_key)).first()


class Team(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(30), index=True)
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug)
    description: so.Mapped[str]
    leader_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id, ondelete='SET NULL'))
    leader: so.Mapped["User"] = so.relationship(lazy="joined", foreign_keys=[leader_id])
    users: so.Mapped[List["User"]] = so.relationship(secondary=UserHasTeam.__table__,
                                                     primaryjoin="Team.id==UserHasTeam.team_id",
                                                     secondaryjoin="User.id==UserHasTeam.user_id",
                                                     back_populates="teams")

    class Meta:
        verbose_name = _l("Team")
        verbose_name_plural = _l("Teams")

