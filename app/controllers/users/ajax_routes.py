from app.controllers.users import bp
from flask import request, abort, current_app, jsonify
from app import db, logger
import app.models as models
import sqlalchemy as sa
from flask_login import login_required, current_user


@bp.route('/select2-data')
@login_required
def user_select2_data():
    try:
        page = int(request.args.get('page'))
    except TypeError:
        page = 1
    except ValueError:
        abort(400)
    query = request.args.get('term') if request.args.get('term') else ''
    data = db.session.scalars(sa.select(models.User).where(models.User.title.ilike('%' + query + "%"))
                              .limit(current_app.config["GlobalSettings"].pagination_element_count_select2 + 1)
                              .offset((page - 1) * current_app.config["GlobalSettings"].pagination_element_count_select2)).all()
    more = len(data) == current_app.config["GlobalSettings"].pagination_element_count_select2 + 1
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request user list via select2-data")
    result = {'results': [{'id': i.id, 'text': i.title} for i in data[:min(len(data), current_app.config["GlobalSettings"].pagination_element_count_select2):]], 'pagination': {'more': more}}
    return jsonify(result)