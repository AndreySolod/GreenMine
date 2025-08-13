import datetime
import io
import zipfile
import sqlalchemy as sa
from flask import render_template, url_for, request, abort, jsonify, send_file
from flask_login import current_user
from app.controllers.webfiles import bp
from app import db, logger
from app.models import Project, FileDirectory, FileData
from app.helpers.general_helpers import get_or_404
from app.helpers.projects_helpers import get_default_environment
from app.helpers.webfiles_helpers import gen_new_name_for_file_or_dir
from sqlalchemy import exc
from flask_babel import lazy_gettext as _l
from app.helpers.roles import project_role_can_make_action_or_abort


@bp.route('/index')
def filedirectory_index():
    ''' Returned main page with plugin to show directory '''
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index all files and directories with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, Project, project_id)
    try:
        parent_dir = db.session.scalars(sa.select(FileDirectory).where(sa.and_(FileDirectory.project_id==project_id, FileDirectory.parent_dir_id==None))).one()
    except (exc.NoResultFound):
        parent_dir = FileDirectory(project_id=project_id, title="/", created_by_id=project.created_by_id)
        db.session.add(parent_dir)
        db.session.commit()
    except exc.MultipleResultsFound:
        abort(500)
    project_role_can_make_action_or_abort(current_user, parent_dir, 'index')
    ctx = get_default_environment(FileDirectory(project=project), 'index')
    context = {'parent_dir': parent_dir, 'project': project}
    return render_template('webfiles/index.html', **context, **ctx)


@bp.route('/folder_content/<folder_id>')
def filedirectory_folder_content(folder_id):
    ''' Returned directory listing '''
    try:
        folder_id = int(folder_id[4::])
    except (ValueError, TypeError):
        abort(400)
    try:
        parent_dir = db.session.scalars(sa.select(FileDirectory).where(FileDirectory.id==folder_id)).one()
    except (exc.NoResultFound, exc.MultipleResultsFound):
        abort(500)
    project_role_can_make_action_or_abort(current_user, parent_dir, 'index')
    dirs = db.session.scalars(sa.select(FileDirectory).where(FileDirectory.parent_dir_id==parent_dir.id)).all()
    files = db.session.scalars(sa.select(FileData).where(FileData.directory_id==parent_dir.id)).all()
    dir_ret = [{'id': "dir_" + str(i.id), 'type': 'folder', 'name': i.title} for i in dirs]
    file_ret = []
    for f in files:
        fd = {'id': "file_" + str(f.id), 'type': 'file', 'name': f.title, 'tooltip': f.description}
        if f.extension in ['png', 'jpg', 'jpeg']:
            fd['thumb'] = url_for('files.download_file', file_id=f.id)
        file_ret.append(fd)
    ans = {'success': True, 'entries': file_ret + dir_ret}
    return jsonify(ans)


@bp.route('/filedirectory/new', methods=["POST"])
def filedirectory_new():
    ''' Creates a new directory from the parameters passed in the request body. Returns a response with the id and title of the created directory '''
    form = request.form
    try:
        parent_dir_id = int(form['parent_dir'][4::])
    except (ValueError, TypeError):
        abort(400)
    parent_dir = db.session.scalars(sa.select(FileDirectory).where(FileDirectory.id==parent_dir_id)).one()
    project_role_can_make_action_or_abort(current_user, parent_dir, 'upload')
    all_subdirs = map(lambda x: x[0], db.session.execute(sa.select(FileDirectory.title).where(FileDirectory.parent_dir_id==parent_dir_id)).all())
    title = gen_new_name_for_file_or_dir(form["title"], all_subdirs)
    fd = FileDirectory(parent_dir=parent_dir, title=title, project_id=parent_dir.project_id)
    db.session.add(fd)
    db.session.commit()
    return jsonify({'status': 'success', 'id': "dir_" + str(fd.id), 'name': fd.title})


@bp.route('/elems/<elem_id>/rename', methods=['POST'])
def elem_rename(elem_id):
    ''' Renames an existing directory. Returns a response with the status and error if present '''
    if elem_id.startswith("dir_"):
        return rename_dir(elem_id)
    else:
        return rename_file(elem_id)


def rename_dir(filedirectory_id):
    try:
        filedirectory_id = int(filedirectory_id[4::])
    except (ValueError, TypeError):
        abort(400)
    form = request.form
    fd = db.session.scalars(sa.select(FileDirectory).where(FileDirectory.id==filedirectory_id)).one()
    all_subdirs = map(lambda x: x[0], db.session.execute(sa.select(FileDirectory.title).where(FileDirectory.parent_dir_id==fd.parent_dir_id)).all())
    if form['title'] in all_subdirs:
        return jsonify({'status': 'error', 'message': _l("A directory with that name already exists")})
    fd.title = form['title']
    db.session.add(fd)
    db.session.commit()
    return jsonify({'status': 'success'})


def rename_file(file_id):
    try:
        file_id = int(file_id[5::])
    except (ValueError, TypeError):
        abort(400)
    form = request.form
    fd = db.session.scalars(sa.select(FileData).where(FileData.id==file_id)).one()
    all_subfiles = map(lambda x: x[0], db.session.execute(sa.select(FileData.title).where(FileData.directory_id==fd.directory_id)).all())
    if form['title'] in all_subfiles:
        return jsonify({'status': 'error', 'message': _l("A file with that name already exists")})
    fd.title = form['title']
    db.session.add(fd)
    db.session.commit()
    return jsonify({'status': 'success'})


@bp.route('/copy', methods=["POST"])
def tree_copy():
    def dir_copy(copied_dir, dest, session):
        ''' Copies the structure of files/directories '''
        nd = FileDirectory(title=copied_dir.title, created_at=copied_dir.created_at, created_by_id=copied_dir.created_by_id, updated_at=datetime.datetime.now(datetime.UTC), updated_by_id=current_user.id, parent_dir=dest, project=dest.project)
        session.add(nd)
        for f in copied_dir.files:
            nf = FileData(title=f.title, extension=f.extension, description=f.description, created_at=f.created_at, created_by_id=f.created_by_id, directory=nd, data=f.data)
            session.add(nf)
        for d in copied_dir.subdirectories:
            dir_copy(d, nd, session)
        return nd
    
    f = request.form
    files = []
    dirs = []
    copied_objs = []
    try:
        for e in f['copy_objects'].split(','):
            if e.startswith('dir_'):
                dirs.append(int(e[4::]))
            else:
                files.append(int(e[5::]))
    except (ValueError, TypeError):
        abort(400)
    # First copy the file
    try:
        to_dir = db.session.scalars(sa.select(FileDirectory).where(FileDirectory.id==int(f['to_dir_id'][4::]))).one()
    except (exc.NoResultFound, exc.MultipleResultsFound):
        abort(400)
    new_files = []
    files_in_target_folder = list(map(lambda x: x[0], db.session.execute(sa.select(FileData.title).where(FileData.directory_id==to_dir.id)).all()))
    for nf in db.session.scalars(sa.select(FileData).where(FileData.id.in_(files))).all():
        new_file = FileData(title=nf.title, extension=nf.extension, description=nf.description, created_at=nf.created_at, created_by_id=nf.created_by_id, directory=to_dir, data=nf.data)
        new_file.title = gen_new_name_for_file_or_dir(new_file.title, files_in_target_folder)
        db.session.add(new_file)
        new_files.append(new_file)
    # Now copy directory with file/directory structure
    new_dirs = []
    dirs_in_target_folder = list(map(lambda x: x[0], db.session.execute(sa.select(FileDirectory.title).where(FileDirectory.parent_dir_id==to_dir.id)).all()))
    for nd in db.session.scalars(sa.select(FileDirectory).where(FileDirectory.id.in_(dirs))).all():
        now_dir = dir_copy(nd, to_dir, db.session)
        now_dir.title = gen_new_name_for_file_or_dir(now_dir.title, dirs_in_target_folder)
        new_dirs.append(now_dir)
    db.session.commit()
    # Added new files to list that have been returned
    for f in new_files:
        file_data = {'id': "file_" + str(f.id), 'type': 'file', 'name': f.title, 'tooltip': f.description}
        if f.extension in ['png', 'jpg', 'jpeg']:
            file_data['thumb'] = url_for('files.download_file', file_id=f.id)
        copied_objs.append(file_data)
    # Add created directory
    for d in new_dirs:
        copied_objs.append({'id': 'dir_' + str(d.id), 'type': 'folder', 'name': d.title})
    return jsonify(copied_objs)


@bp.route('/move', methods=['POST'])
def tree_move():
    form = request.form
    moved_files = []
    moved_folders = []
    moved_objs = []
    try:
        destfolder = db.session.scalars(sa.select(FileDirectory).where(FileDirectory.id==int(form['dest_folder'][4::]))).one()
        for e in form['moved_objects'].split(','):
            if e.startswith('dir_'):
                moved_folders.append(int(e[4::]))
            else:
                moved_files.append(int(e[5::]))
    except (ValueError, TypeError, exc.NoResultFound, exc.MultipleResultsFound):
        abort(400)
    files_in_destfolder = list(map(lambda x: x[0], db.session.execute(sa.select(FileData.title).where(FileData.directory_id==destfolder.id)).all()))
    for cf in db.session.scalars(sa.select(FileData).where(FileData.id.in_(moved_files))).all():
        cf.directory = destfolder
        cf.title = gen_new_name_for_file_or_dir(cf.title, files_in_destfolder)
        file_data = {'id': "file_" + str(cf.id), 'type': 'file', 'name': cf.title, 'tooltip': cf.description}
        if cf.extension in ['png', 'jpg', 'jpeg']:
            file_data['thumb'] = url_for('files.download_file', file_id=cf.id)
        moved_objs.append(file_data)
    folders_in_destfolder = list(map(lambda x: x[0], db.session.execute(sa.select(FileDirectory.title).where(FileDirectory.parent_dir_id==destfolder.id)).all()))
    for d in db.session.scalars(sa.select(FileDirectory).where(FileDirectory.id.in_(moved_folders))).all():
        d.parent_dir = destfolder
        d.title = gen_new_name_for_file_or_dir(d.title, folders_in_destfolder)
        moved_objs.append({'id': 'dir_' + str(d.id), 'type': 'folder', 'name': d.title})
    db.session.commit()
    return jsonify(moved_objs)


@bp.route('/delete', methods=['POST'])
def tree_delete():
    form = request.form
    deleted_files = []
    deleted_dirs = []
    try:
        for e in form['deleted_objects'].split(','):
            if e.startswith('dir_'):
                deleted_dirs.append(int(e[4::]))
            else:
                deleted_files.append(int(e[5::]))
    except (ValueError, TypeError):
        abort(400)
    if len(deleted_files != 0):
        # check permissions to delete files and dirs
        try:
            random_file = db.session.scalars(sa.select(FileData).where(FileData.id == deleted_files[0])).one()
        except (exc.MultipleResultsFound, exc.NoResultFound):
            abort(400)
        project_role_can_make_action_or_abort(current_user, random_file.directory, 'delete')
    for f in db.session.scalars(sa.select(FileData).where(FileData.id.in_(deleted_files))).all():
        db.session.delete(f)
    if len(deleted_dirs) != 0:
        # check permissions to delete files and dirs
        try:
            random_file = db.session.scalars(sa.select(FileDirectory).where(FileDirectory.id == deleted_dirs[0])).one()
        except (exc.MultipleResultsFound, exc.NoResultFound):
            abort(400)
        project_role_can_make_action_or_abort(current_user, random_file, 'delete')
    for d in db.session.scalars(sa.select(FileDirectory).where(FileDirectory.id.in_(deleted_dirs))).all():
        db.session.delete(d)
    db.session.commit()
    return jsonify({'status': 'success'})


@bp.route('/download_files', methods=['POST'])
def tree_download():
    def add_dir(now_dir, zip_file, prefix=[]):
        pc = prefix + [now_dir.title]
        for f in now_dir.files:
            np = pc + [f.title]
            zip_file.writestr("/".join(np), f.data)
        for d in now_dir.subdirectories:
            add_dir(d, zip_file, pc)
        if len(now_dir.files) == 0 and len(now_dir.subdirectories) == 0:
            zif = zipfile.ZipInfo("/".join(pc) + "/")
            zip_file.writestr(zif, "")

    if 'files_ids' not in request.form:
        abort(400)
    dls = request.form.get('files_ids').split(',')
    try:
        dl_files = [int(i[5::]) for i in filter(lambda x: x.startswith('file_'), dls)]
        dl_dirs = [int(i[4::]) for i in filter(lambda x: x.startswith('dir_'), dls)]
    except ValueError:
        abort(400)
    
    if len(dl_files) != 0: # check permissions to download files and dirs
        try:
            random_file = db.session.scalars(sa.select(FileData).where(FileData.id == dl_files[0])).one()
        except (exc.MultipleResultsFound, exc.NoResultFound):
            abort(400)
        project_role_can_make_action_or_abort(current_user, random_file, 'download')
    elif len(dl_dirs) != 0:
        try:
            random_file = db.session.scalars(sa.select(FileDirectory).where(FileDirectory.id == dl_dirs[0])).one()
        except (exc.MultipleResultsFound, exc.NoResultFound):
            abort(400)
        project_role_can_make_action_or_abort(current_user, random_file, 'download')
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
        # First added files
        for f in db.session.scalars(sa.select(FileData).where(FileData.id.in_(dl_files))):
            zip_file.writestr(str(f.id) + '_' + f.title, f.data)
        # Now added directory
        for d in db.session.scalars(sa.select(FileDirectory).where(FileDirectory.id.in_(dl_dirs))):
            add_dir(d, zip_file)

    zip_buffer.seek(0)
    return send_file(zip_buffer, as_attachment=True,
                     download_name=f"GreenMine-files-{datetime.datetime.now(datetime.UTC)}.zip",
                     mimetype='application/zip')


@bp.route('/file/new', methods=['POST'])
def webfile_new():
    pass
