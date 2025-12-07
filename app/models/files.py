from app import db
from app.helpers.admin_helpers import project_object_with_permissions
from typing import List, Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_babel import lazy_gettext as _l
from .datatypes import ID, CreatedAt, UpdatedAt


@project_object_with_permissions
class FileDirectory(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(80), info={'label': _l('Title')})
    created_at: so.Mapped[CreatedAt]
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l('Created by')})
    created_by: so.Mapped["User"] = so.relationship(lazy='select', foreign_keys=[created_by_id], info={'label': _l('Created by')}) # type: ignore
    updated_at: so.Mapped[UpdatedAt]
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l('Updated by')})
    updated_by: so.Mapped["User"] = so.relationship(lazy='select', foreign_keys=[updated_by_id], info={'label': _l('Updated by')}) # type: ignore
    files: so.Mapped[List["FileData"]] = so.relationship(lazy='select', back_populates='directory', cascade='all, delete-orphan', info={'label': _l('Files')})
    parent_dir_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('file_directory.id', ondelete='CASCADE'), info={'label': _l('Parent directory')})
    parent_dir: so.Mapped['FileDirectory'] = so.relationship(backref=so.backref('subdirectories', cascade="all, delete-orphan"), post_update=True, # type: ignore
                                                 lazy='select', join_depth=2,
                                                 foreign_keys=[parent_dir_id], remote_side=[id], info={'label': _l('Parent directory')})
    project_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project.id', ondelete='CASCADE'), info={'label': _l('Project')})
    project: so.Mapped["Project"] = so.relationship(lazy='joined', foreign_keys=[project_id], back_populates="file_directories", info={'label': _l('Project')}) # type: ignore

    @property
    def parent(self):
        if self.parent_dir is None:
            return self
        return self.parent_dir

    class Meta:
        verbose_name = _l('Directory')
        verbose_name_plural = _l('Directorys')
        icon = "fa-solid fa-folder-open"
        icon_index = "fa-solid fa-folder-open"
        project_permission_actions = {'index': _l("Show project files and folders"), 'upload': _l("Upload new project file"), 'download': _l("Download files and folders"), 'delete': _l("Delete files and folders")}


class FileData(db.Model):
    id: so.Mapped[ID] = so.mapped_column(primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(80), info={'label': _l('Title')})
    extension: so.Mapped[str] = so.mapped_column(sa.String(4), info={'label': _l('Extension')})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Description")})
    created_at: so.Mapped[CreatedAt]
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL', use_alter=True), info={'label': _l('Added by')})
    created_by: so.Mapped["User"] = so.relationship(lazy='select', foreign_keys=[created_by_id], info={'label': _l('Added by')}) # type: ignore
    directory_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(FileDirectory.id, ondelete='CASCADE', use_alter=True), info={'label': _l('Refers to the directory')})
    directory: so.Mapped["FileDirectory"] = so.relationship(lazy='select', foreign_keys=[directory_id], back_populates='files', info={'label': _l('Refers to the directory')})
    data: so.Mapped[bytes] = so.mapped_column(info={'label': _l('Data')})

    class Meta:
        verbose_name = _l('File')
        verbose_name_plural = _l('Files')
        icon = 'fa-solid fa-laptop-file'
