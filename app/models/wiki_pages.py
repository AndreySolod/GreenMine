from app import db
import sqlalchemy as sa
import sqlalchemy.orm as so
from typing import List, Optional
from flask_babel import lazy_gettext as _l
from .datatypes import ID, CreatedAt, UpdatedAt


class WikiPage(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    created_at: so.Mapped[CreatedAt]
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Created by")})
    created_by: so.Mapped["User"] = so.relationship(lazy='select', foreign_keys="WikiPage.created_by_id", info={'label': _l("Created by")}) # type: ignore
    updated_at: so.Mapped[UpdatedAt]
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete="SET NULL"), info={'label': _l("Updated by")})
    updated_by: so.Mapped['User'] = so.relationship(lazy='select', foreign_keys="WikiPage.updated_by_id", info={'label': _l("Updated by")}) # type: ignore
    title: so.Mapped[str] = so.mapped_column(sa.String(80), info={'label': _l("Title")})
    description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(150), info={'label': _l("Description")})
    text: so.Mapped[str] = so.mapped_column(info={'label': _l("Text")})
    directory_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('wiki_directory.id', ondelete='CASCADE'), info={'label': _l("Directory")})
    directory: so.Mapped["WikiDirectory"] = so.relationship(back_populates="pages", lazy="joined", info={'label': _l("Directory")})

    @property
    def parent(self):
        return self.directory
    
    @property
    def treeselecttitle(self):
        return self.title

    def __repr__(self):
        return f"<WikiPage with id='{self.id}' and title='{self.title}>"

    class Meta:
        verbose_name = _l("Wiki Page")
        verbose_name_plural = _l("Wiki Pages")
        icon = "fa-brands fa-wikipedia-w"
        global_permission_actions = {"show": _l("Show object card"), "update": _l("Update object"), "delete": _l("Delete object"),
                                     "create": _l("Create object")}


class WikiDirectory(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    created_at: so.Mapped[CreatedAt]
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Created by")})
    created_by: so.Mapped["User"] = so.relationship(lazy='select', foreign_keys="WikiDirectory.created_by_id", info={'label': _l("Created by")}) # type: ignore
    updated_at: so.Mapped[UpdatedAt]
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete="SET NULL"), info={'label': _l("Updated by")})
    updated_by: so.Mapped['User'] = so.relationship(lazy='select', foreign_keys="WikiDirectory.updated_by_id", info={'label': _l("Updated by")}) # type: ignore
    title: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l("Title")})
    description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(150), info={'label': _l("Description")})
    pages: so.Mapped[List[WikiPage]] = so.relationship(back_populates="directory", cascade='all, delete-orphan', info={'label': _l("Pages")})
    parent_directory_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('wiki_directory.id', ondelete='CASCADE'), info={'label': _l("Parent directory")})
    parent_directory: so.Mapped["WikiDirectory"] = so.relationship(backref=so.backref('subdirectories', info={'label': _l("Nested directories")}, cascade='all, delete-orphan'), post_update=True,
                                                 lazy='select', join_depth=2,
                                                 foreign_keys=[parent_directory_id], remote_side=[id])

    @property
    def parent(self):
        return self.parent_directory

    @property
    def treeselecttitle(self):
        return self.title

    class Meta:
        verbose_name = _l("Directory of Wiki pages")
        verbose_name_plural = _l("Directories of Wiki pages")
        icon = 'fa-solid fa-folder'
        global_permission_actions = {"show": _l("Show object card"), "update": _l("Update object"), "delete": _l("Delete object"),
                                     "create": _l("Create object"), "index": "Show object list"}

