from app.controllers.files import bp
from app import db, logger, sanitizer
from flask import request, send_file, url_for, abort, jsonify
from flask_login import login_required, current_user
from app.models import FileData, FileDirectory
from app.helpers.webfiles_helpers import gen_new_name_for_file_or_dir
from werkzeug.utils import secure_filename
from io import BytesIO
import sqlalchemy as sa
import sqlalchemy.exc as exc
from app.helpers.roles import project_role_can_make_action_or_abort


@bp.route("/upload", methods=["POST"])
@login_required
def upload_file():
    item = request.files.get('upload')
    title = sanitizer.escape(secure_filename(item.filename), FileData.title.type.length)
    extension = item.filename.split('.')[-1]
    uploaded_file = item.read()
    try:
        directory_id = int(request.form['directory_id']) if ('directory_id' in request.form) else None
    except (ValueError, TypeError):
        abort(400)
    if directory_id:
        try:
            fd = db.session.scalars(sa.select(FileDirectory).where(FileDirectory.id == directory_id)).one()
        except (exc.MultipleResultsFound, exc.NoResultFound):
            abort(404)
        project_role_can_make_action_or_abort(current_user, fd, 'upload')
        all_files = map(lambda x: x[0], db.session.execute(sa.select(FileData.title).where(FileData.directory_id==directory_id)).all())
        title = gen_new_name_for_file_or_dir(title, all_files)
    description = request.form['description'] if ('description' in request.form) else ''
    filedata = FileData(extension=extension, description=description, data=uploaded_file, title=title, directory_id=directory_id)
    db.session.add(filedata)
    db.session.commit()
    file_id = filedata.id
    if "client" in request.args and request.args.get("client") == 'filemanager':
        return jsonify({'success': True})
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' upload new file #{filedata.id}")
    return jsonify({'url': url_for('files.download_file', file_id=file_id)})


@bp.route("/download/<file_id>")
@login_required
def download_file(file_id):
    try:
        file_id = int(file_id)
    except (ValueError, TypeError):
        abort(400)
    f = db.get_or_404(FileData, file_id)
    if f.directory is not None:
        project_role_can_make_action_or_abort(current_user, f.directory, 'download')
    buf = BytesIO()
    buf.write(f.data)
    buf.seek(0)
    if f.title.endswith('.' + f.extension):
        params = {'as_attachment': True, 'download_name': f.title }
    else:
        params = {'as_attachment': True, 'download_name': f.title + '.' + f.extension }
    if f.extension in ('png', 'jpg', 'jpeg'):
        params['mimetype'] = 'image/' + f.extension
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request to download file #{file_id}")
    return send_file(buf, **params)
