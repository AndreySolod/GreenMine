from app.controllers.generics import bp
from app import db, logger
import sqlalchemy as sa
from flask import request, redirect, flash, abort, jsonify, current_app
from flask_login import login_required, current_user
from app.helpers.admin_helpers import get_enumerated_objects
from app.models import Comment
from app.helpers.general_helpers import get_or_404
from flask_babel import lazy_gettext as _l
import importlib


#@bp.route('/comments/<int:comment_id>/delete', methods=["POST"])
#@login_required
#def comment_delete(comment_id):
#    backref = request.args.get('backref', default=None)
#    fast = request.args.get('fast', default=None)
#    if backref is None and fast is None:
#        abort(400)
#    c = get_or_404(db.session, Comment, comment_id)
#    db.session.delete(c)
#    db.session.commit()
#    if backref:
#        flash(_l("Comment deleted"), "success")
#        return redirect(backref)
#    else:
#        return jsonify({'status': 'success'})


@bp.route('/enumeration_objects/<object_class>/list')
@login_required
def enumeration_object_list(object_class):
    modules = importlib.import_module('app.models')
    try:
        page = int(request.args.get('page'))
    except (TypeError):
        page = 1
    except ValueError:
        abort(400)
    try:
        cls = getattr(modules, object_class)
    except AttributeError:
        abort(404)
    query = request.args.get('term') if request.args.get('term') else ''
    eo = get_enumerated_objects()
    if cls not in eo:
        abort(404)
    data = db.session.execute(sa.select(cls.id, cls.title).where(cls.title.ilike('%' + query + '%')).limit(current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"] + 1)
                              .offset((page - 1) * current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"])).all()
    more = len(data) == current_app.config["PAGINATION_ELEMENT_COUNT_SELECT2"] + 1
    if more:
        result = {'results': [{'id': i[0], 'text': i[1]} for i in data[:len(data) - 1:]], 'pagination': {'more': True}}
    else:
        result = {'results': [{'id': i[0], 'text': i[1]} for i in data], 'pagination': {'more': False}}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request to get enumerated object list '{object_class}'")
    return jsonify(result)