from app.controllers.chats import bp
from app.helpers.projects_helpers import get_default_environment
from flask import render_template, request, abort
from flask_login import login_required, current_user
from app import db, side_libraries, logger
import app.models as models
import sqlalchemy as sa
from app.helpers.roles import project_role_can_make_action_or_abort


@bp.route('/index')
@login_required
def index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        abort(400)
    project = db.get_or_404(models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.ChatMessage(), 'index', project=project)
    chat_messages = db.session.scalars(sa.select(models.ChatMessage).where(models.ChatMessage.project_id == project.id))
    ctx = get_default_environment(models.ChatMessage(project=project), 'index')
    side_libraries.library_required('ckeditor')
    context = {'chat_messages': chat_messages, 'project': project, 'ckeditor_height': '20vh'}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request to get all chat messages on project #{project.id}'")
    return render_template('chats/index.html', **ctx, **context)