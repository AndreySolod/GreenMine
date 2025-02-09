from typing import Optional, List
import app.models as models
from app import db, sanitizer
import sqlalchemy as sa
import sqlalchemy.exc as exc


def rename_dir(filedirectory_id: str, title: str) -> Optional[bool]:
    ''' Trying to rename exist directory. Check if the directory title is exist and return False if is exist. Else rename current directory and return True.
     Return None if any error is occursed (id is not interpreded as int or filedirectory is not exist) '''
    try:
        filedirectory_id = int(filedirectory_id[4::])
    except (ValueError, TypeError):
        return None
    try:
        fd = db.session.scalars(sa.select(models.FileDirectory).where(models.FileDirectory.id == filedirectory_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        return None
    all_subdirs = map(lambda x: x[0], db.session.execute(sa.select(models.FileDirectory.title).where(models.FileDirectory.parent_dir_id == fd.parent_dir_id)).all())
    if sanitizer.escape(title, models.FileDirectory.title.type.length) in all_subdirs:
        return False
    fd.title = sanitizer.escape(title, models.FileDirectory.title.type.length)
    db.session.add(fd)
    db.session.commit()
    return True


def rename_file(file_id: str, title: str) -> Optional[bool]:
    ''' Trying to rename exist file. Check if file title is exist and return False if exist. Else rename current file and return True.
     Return None if any error is occursed (id is not interpreted as int or file is not exist) '''
    try:
        file_id = int(file_id[5::])
    except (ValueError, TypeError):
        return None
    try:
        fd = db.session.scalars(sa.select(models.FileData).where(models.FileData.id == file_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        return None
    all_subfiles = map(lambda x: x[0], db.session.execute(sa.select(models.FileData.title).where(models.FileData.directory_id==fd.directory_id)).all())
    if sanitizer.escape(title, models.FileData.title.type.length) in all_subfiles:
        return False
    fd.title = sanitizer.escape(title, models.FileData.title.type.length)
    db.session.add(fd)
    db.session.commit()
    return True


def gen_new_name_for_file_or_dir(title: str, all_titles: List[str], pos: Optional[int]=None) -> str:
    if title not in all_titles:
        return sanitizer.escape(title, models.FileData.title.type.length)
    elif pos == None:
        return gen_new_name_for_file_or_dir(sanitizer.escape(title, models.FileData.title.type.length - 4) + ' (1)', all_titles, 1)
    return gen_new_name_for_file_or_dir(sanitizer.escape(title[:len(title) - 3:], models.FileData.title.type.length - 3) + f"({pos + 1})", all_titles, pos + 1)
