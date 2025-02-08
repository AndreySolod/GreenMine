from app import socketio, db
from app.helpers.general_helpers import authenticated_only, utcnow
from app.helpers.projects_helpers import get_current_room, gen_new_name_for_file_or_dir, rename_dir, rename_file
from flask_socketio import emit, join_room, send
from flask import url_for, current_app
from flask_login import current_user
import app.models as models
import sqlalchemy as sa
import sqlalchemy.exc as exc
import logging
import datetime
import base64
from flask_babel import lazy_gettext as _l
from app.helpers.roles import project_role_can_make_action
logger = logging.getLogger('webfiles websocket')


@socketio.on("join_room", namespace="/webfiles")
@authenticated_only
def join_webfiles_room(data):
    try:
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == int(data))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError):
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join incorrect webfiles room {data}")
        return None
    if not project_role_can_make_action(current_user, models.FileDirectory(), 'index', project=project):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join webfiles room #{data}, in which he has no rights to")
        return None
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' join webfiles room #{data}")
    join_room(data, namespace="/webfiles")


@socketio.on('new folder', namespace='/webfiles')
@authenticated_only
def add_folder(data):
    ''' Created new folder with given name and parent_dir_id. Returned new diri params or False if error is occured '''
    cr = get_current_room()
    if cr is None:
        return None
    _, current_room_name = cr
    try:
        parent_dir = db.session.scalars(sa.select(models.FileDirectory).where(models.FileDirectory.id == int(data['parent_dir_id'][4::]))).one()
    except (ValueError, TypeError, exc.NoResultFound, exc.MultipleResultsFound, KeyError) as e:
        logger.error(f'Error when handle data on new folder: {e}', exc_info=True)
        return None
    if not project_role_can_make_action(current_user, parent_dir, 'upload'):
        return None
    all_subdirs = map(lambda x: x[0], db.session.execute(sa.select(models.FileDirectory.title).where(models.FileDirectory.parent_dir_id==parent_dir.id)).all())
    title = gen_new_name_for_file_or_dir(data["title"], all_subdirs)
    fd = models.FileDirectory(parent_dir=parent_dir, title=title, project_id=parent_dir.project_id)
    db.session.add(fd)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new folder #{fd.id}")
    return {'dir_id': "dir_" + str(fd.id), 'name': fd.title}


@socketio.on('rename element', namespace='/webfiles')
@authenticated_only
def rename_element(data):
    ''' Rename current element (file/directory). Returned message with True if renamed is successful and message with error otherwise'''
    if 'id' not in data or 'title' not in data:
        return {'message': _l("Something went wrong. Try refresh your page")}
    if data['id'].startswith("dir_"):
        ren = rename_dir(data['id'], data['title'])
        if ren:
            logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' rename directory #{data['id']}")
            return True
        elif ren == False:
            return {'message': _l("A directory with that name already exists")}
        else:
            return {'message': _l("Something went wrong. Try refresh your page")}
    else:
        ren = rename_file(data['id'], data['title'])
        if ren:
            logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' rename file #{data['id']}")
            return True
        elif ren == False:
            return {'message': _l("A file with that name already exists")}
        else:
            return {'message': _l("Something went wrong. Try refresh your page")}


@socketio.on('copy elements', namespace='/webfiles')
@authenticated_only
def copy_element(data):
    def dir_copy(copied_dir, dest):
        ''' Copy of File/Folder structure. Returned False if error is occured, and list of copied object otherwise '''
        nd = models.FileDirectory(title=copied_dir.title, created_at=copied_dir.created_at, created_by_id=copied_dir.created_by_id, updated_at=datetime.datetime.now(datetime.UTC), updated_by_id=current_user.id, parent_dir=dest, project=dest.project)
        db.session.add(nd)
        for f in copied_dir.files:
            nf = models.FileData(title=f.title, extension=f.extension, description=f.description, created_at=f.created_at, created_by_id=f.created_by_id, directory=nd, data=f.data)
            db.session.add(nf)
        for d in copied_dir.subdirectories:
            dir_copy(d, nd)
        return nd
    
    files = []
    dirs = []
    copied_objs = []
    try:
        for e in data['copy_objects'].split(','):
            if e.startswith('dir_'):
                dirs.append(int(e[4::]))
            else:
                files.append(int(e[5::]))
    except (ValueError, TypeError, KeyError) as e:
        logger.error(f'Error when copy file: {e}', exc_info=True)
        return False
    # First, copy a file
    try:
        to_dir = db.session.scalars(sa.select(models.FileDirectory).where(models.FileDirectory.id==int(data['to_dir_id'][4::]))).one()
    except (exc.NoResultFound, exc.MultipleResultsFound):
        return False
    new_files = []
    files_in_target_folder = list(map(lambda x: x[0], db.session.execute(sa.select(models.FileData.title).where(models.FileData.directory_id==to_dir.id)).all()))
    for nf in db.session.scalars(sa.select(models.FileData).where(models.FileData.id.in_(files))).all():
        new_file = models.FileData(title=nf.title, extension=nf.extension, description=nf.description, created_at=nf.created_at, created_by_id=nf.created_by_id, directory=to_dir, data=nf.data)
        new_file.title = gen_new_name_for_file_or_dir(new_file.title, files_in_target_folder)
        db.session.add(new_file)
        new_files.append(new_file)
    # Now copy a directory with all files/catalog structure
    new_dirs = []
    dirs_in_target_folder = list(map(lambda x: x[0], db.session.execute(sa.select(models.FileDirectory.title).where(models.FileDirectory.parent_dir_id==to_dir.id)).all()))
    for nd in db.session.scalars(sa.select(models.FileDirectory).where(models.FileDirectory.id.in_(dirs))).all():
        now_dir = dir_copy(nd, to_dir)
        now_dir.title = gen_new_name_for_file_or_dir(now_dir.title, dirs_in_target_folder)
        new_dirs.append(now_dir)
    db.session.commit()
    # Add now created files to list
    for f in new_files:
        file_data = {'id': "file_" + str(f.id), 'type': 'file', 'name': f.title, 'tooltip': f.description}
        if f.extension in ['png', 'jpg', 'jpeg']:
            file_data['thumb'] = url_for('files.download_file', file_id=f.id)
        copied_objs.append(file_data)
    # Add created dirs to list:
    for d in new_dirs:
        copied_objs.append({'id': 'dir_' + str(d.id), 'type': 'folder', 'name': d.title})
    return {'copied_objects': copied_objs}


@socketio.on('move elements', namespace='/webfiles')
@authenticated_only
def move_elements(data):
    ''' Moved file and directory to dest folder. Returned False if error is occured and list with moved object otherwise '''
    moved_files = []
    moved_folders = []
    moved_objs = []
    try:
        destfolder = db.session.scalars(sa.select(models.FileDirectory).where(models.FileDirectory.id==int(data['dest_folder'][4::]))).one()
        for e in data['moved_objects'].split(','):
            if e.startswith('dir_'):
                moved_folders.append(int(e[4::]))
            else:
                moved_files.append(int(e[5::]))
    except (ValueError, TypeError, exc.NoResultFound, exc.MultipleResultsFound):
        return False
    files_in_destfolder = list(map(lambda x: x[0], db.session.execute(sa.select(models.FileData.title).where(models.FileData.directory_id==destfolder.id)).all()))
    for cf in db.session.scalars(sa.select(models.FileData).where(models.FileData.id.in_(moved_files))).all():
        cf.directory = destfolder
        cf.title = gen_new_name_for_file_or_dir(cf.title, files_in_destfolder)
        file_data = {'id': "file_" + str(cf.id), 'type': 'file', 'name': cf.title, 'tooltip': cf.description}
        if cf.extension in ['png', 'jpg', 'jpeg']:
            file_data['thumb'] = url_for('files.download_file', file_id=cf.id)
        moved_objs.append(file_data)
    folders_in_destfolder = list(map(lambda x: x[0], db.session.execute(sa.select(models.FileDirectory.title).where(models.FileDirectory.parent_dir_id==destfolder.id)).all()))
    for d in db.session.scalars(sa.select(models.FileDirectory).where(models.FileDirectory.id.in_(moved_folders))).all():
        d.parent_dir = destfolder
        d.title = gen_new_name_for_file_or_dir(d.title, folders_in_destfolder)
        moved_objs.append({'id': 'dir_' + str(d.id), 'type': 'folder', 'name': d.title})
    db.session.commit()
    return {'moved_objects': moved_objs}


@socketio.on('delete elements', namespace='/webfiles')
@authenticated_only
def delete_elements(data):
    ''' Trying to delete elements. Returned True if success and False otherwise '''
    deleted_files = []
    deleted_dirs = []
    try:
        for e in data['deleted_objects'].split(','):
            if e.startswith('dir_'):
                deleted_dirs.append(int(e[4::]))
            else:
                deleted_files.append(int(e[5::]))
    except (ValueError, TypeError):
        return None
    
    #check permissions to delete file
    if len(deleted_dirs) != 0:
        try:
            random_file = db.session.scalars(sa.select(models.FileDirectory).where(models.FileDirectory.id == deleted_dirs[0])).one()
        except (exc.MultipleResultsFound, exc.NoResultFound):
            return None
        if not project_role_can_make_action(current_user, random_file, 'delete'):
            return None
    if len(deleted_files) != 0:
        try:
            random_file = db.session.scalars(sa.select(models.FileData).where(models.FileData.id == deleted_dirs[0])).one()
        except (exc.MultipleResultsFound, exc.NoResultFound):
            return None
        if not project_role_can_make_action(current_user, random_file.directory, 'delete'):
            return None
    
    # delete files and dirs
    for f in db.session.scalars(sa.select(models.FileData).where(models.FileData.id.in_(deleted_files))).all():
        db.session.delete(f)
    for d in db.session.scalars(sa.select(models.FileDirectory).where(models.FileDirectory.id.in_(deleted_dirs))).all():
        db.session.delete(d)
    db.session.commit()
    return True


@socketio.on('add file', namespace='/webfiles')
@authenticated_only
def add_file(data):
    ''' Trying to add file in database. Returned True if success and False otherwise '''
    try:
        directory_id = int(data['directory_id'][4::])
        all_files = map(lambda x: x[0], db.session.execute(sa.select(models.FileData.title).where(models.FileData.directory_id==directory_id)).all())
        title = gen_new_name_for_file_or_dir(data['name'], all_files)
        extension = data['name'].split('.')[-1]
        fd = models.FileData(title=title, extension=extension, description='', data=base64.b64decode(data['data']), directory_id=directory_id)
    except KeyError:
        return False
    db.session.add(fd)
    db.session.commit()
    return True