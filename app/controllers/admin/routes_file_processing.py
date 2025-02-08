import app.models as models
from app.controllers.admin import bp
from app import db, side_libraries
from app.helpers.admin_helpers import DefaultEnvironment
from app.helpers.general_helpers import get_bootstrap_table_json_data
import sqlalchemy as sa
import sqlalchemy.exc as exc
import json
from flask import request, render_template, abort, jsonify
from app import logger
from flask_login import current_user


@bp.route('/files/index')
def admin_file_index():
    ctx = DefaultEnvironment('admin_file_index')()
    filters = {}
    users = {i: t for i, t in db.session.execute(sa.select(models.User.id, models.User.title))}
    filters["users"] = json.dumps(users)
    extensions = {i[0]: i[0] for i in db.session.execute(sa.select(models.FileData.extension).distinct())}
    filters["extensions"] = json.dumps(extensions)
    side_libraries.library_required('bootstrap_table')
    context = {'filters': filters}
    side_libraries.library_required('contextmenu')
    return render_template('admin/file_index.html', **ctx, **context)


@bp.route('/files/index-data')
def files_index_data():
    additional_params = {'obj': models.FileData, 'column_index': ['id', 'title', 'extension', 'description', 'created_at', 'created_by_id'],
                         'base_select': lambda x: x}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' get all file list")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/files/<file_id>/delete', methods=["POST", "DELETE"])
def files_delete(file_id):
    try:
        file_id = int(file_id)
    except (ValueError, TypeError):
        abort(404)
    try:
        file_title = db.session.scalars(sa.select(models.FileData.title).where(models.FileData.id == file_id)).one()
        db.session.execute(sa.delete(models.FileData).where(models.FileData.id == file_id))
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete a file '{file_title}'")
    return jsonify({"status": "success"})