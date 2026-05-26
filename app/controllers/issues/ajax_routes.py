from app.controllers.issues import bp
from flask import jsonify, request, abort
from app import db, logger
from app.helpers.roles import project_role_can_make_action_or_abort
from app.helpers.general_helpers import get_complementary_color
import app.models as models
from flask_login import current_user
import sqlalchemy as sa
import sqlalchemy.exc as exc
import json


@bp.route('/<issue_id>/raise_priority', methods=['POST'])
def increase_order_number(issue_id):
    try:
        issue = db.session.get(models.Issue, int(issue_id))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request raise issue priority with non-integer issue_id {issue_id}")
        abort(400)
    f"User '{getattr(current_user, 'login', 'Anonymous')}' request raise issue priority on issue {issue_id}"
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
    f"User '{getattr(current_user, 'login', 'Anonymous')}' request lower issue priority on issue {issue_id}"
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


@bp.route('/<issue_id>/change_status', methods=["POST"])
def change_issue_status(issue_id: str):
    try:
        to_status_id = int(request.get_json()["status_id"])
        to_status = db.session.scalars(sa.select(models.IssueStatus).where(models.IssueStatus.id == to_status_id)).one()
        issue = db.session.scalars(sa.select(models.Issue).where(models.Issue.id == int(issue_id))).one()
    except exc.MultipleResultsFound, exc.NoResultFound, KeyError, ValueError, TypeError:
        f"User '{getattr(current_user, 'login', 'Anonymous')}' request update issue status with wrong parameters on issue {issue_id}"
        abort(400)
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request update issue status {issue_id}")
    project_role_can_make_action_or_abort(current_user, issue, 'update')
    issue.status = to_status
    db.session.commit()
    return jsonify({'success': True, 'status_id': to_status.id, 'status_title': to_status.title,
                    'background-color': to_status.color, 'color': get_complementary_color(to_status.color)})