import sqlalchemy as sa
from app import db, logger
import app.models as models
from app.controllers.credentials import bp
from flask import abort, request, jsonify, current_app
from flask_login import current_user
from app.helpers.roles import project_role_can_make_action_or_abort
import sqlalchemy.exc as exc

@bp.route('/get-select2-data')
def get_select2_credentials_data():
    try:
        page = int(request.args.get('page'))
    except TypeError:
        page = 1
    except ValueError:
        abort(400)
    try:
        project_id = int(request.args.get('project_id'))
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == project_id)).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        abort(400)
    project_role_can_make_action_or_abort(current_user, models.Credential(), 'index', project=project)
    query = request.args.get('term') if request.args.get('term') else ''
    data = db.session.scalars(sa.select(models.Credential).where(sa.and_((sa.cast(models.Credential.login, sa.String) + ":" + sa.cast(models.Credential.password, sa.String)).ilike('%' + query + '%'),
                                                                         models.Credential.project_id == project_id,
                                                                         models.Credential.is_pentest_credentials == False))
                                                                         .limit(current_app.config["GlobalSettings"].pagination_element_count_select2 + 1)
                                                                         .offset((page - 1) * current_app.config["GlobalSettings"].pagination_element_count_select2)).all()
    more = len(data) == current_app.config["GlobalSettings"].pagination_element_count_select2 + 1
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request credentials on project #{project_id} via select2-data")
    result = {'results': [{'id': i.id, 'text': i.treeselecttitle} for i in data[:min(len(data), current_app.config["GlobalSettings"].pagination_element_count_select2):]], 'pagination': {'more': more}}
    return jsonify(result)