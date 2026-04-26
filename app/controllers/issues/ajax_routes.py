from app.controllers.issues import bp
from flask import jsonify, request, abort
from app import db, logger
from app.helpers.roles import project_role_can_make_action_or_abort
import app.models as models
from flask_login import current_user
import sqlalchemy as sa


@bp.route('/<issue_id>/raise_priority', methods=['POST'])
def increase_order_number(issue_id):
    try:
        issue = db.session.get(models.Issue, int(issue_id))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request raise issue priority with non-integer issue_id {issue_id}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, issue, 'update')
    if issue.order_number is None:
        now_order_number = db.session.scalars(sa.select(models.Issue.order_number).where(models.Issue.project_id == issue.project_id)
                                              .order_by(models.Issue.order_number.desc()).limit(1)).first()
        if now_order_number is None:
            now_order_number = 0
    else:
        now_order_number = issue.order_number
    issue.order_number = now_order_number + 1
    db.session.commit()
    return jsonify({'success': True, 'order_number': issue.order_number})


@bp.route('/<issue_id>/lower_priority', methods=['POST'])
def decrease_order_number(issue_id):
    try:
        issue = db.session.get(models.Issue, int(issue_id))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request lower issue priority with non-integer project_id {issue_id}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, issue, 'update')
    if issue.order_number is None:
        now_order_number = db.session.scalars(sa.select(models.Issue.order_number).where(models.Issue.project_id == issue.project_id)
                                              .order_by(models.Issue.order_number.asc()).limit(1)).first()
        if now_order_number is None:
            now_order_number = 2
    else:
        now_order_number = issue.order_number
    issue.order_number = now_order_number - 1
    db.session.commit()
    return jsonify({'success': True, 'order_number': issue.order_number})