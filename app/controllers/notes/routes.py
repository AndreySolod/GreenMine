from app import db, logger
from app.controllers.notes import bp
from flask_login import current_user
from flask import request, render_template, url_for, redirect, flash, abort
from app.models import Note, Project
from app.helpers.general_helpers import get_or_404
from app.helpers.projects_helpers import get_default_environment
from .forms import NoteNewForm, NoteEditForm
import sqlalchemy as sa
import sqlalchemy.exc as exc
from flask_babel import lazy_gettext as _l
from app.helpers.roles import project_role_can_make_action_or_abort


@bp.route('/index')
def note_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to get list notes with non-integer project_id {request.args.get('project_id')}")
        abort(404)
    project = get_or_404(db.session, Project, project_id)
    project_role_can_make_action_or_abort(current_user, Note(), 'index', project=project)
    notes = db.session.scalars(sa.select(Note).where(Note.project_id == project_id)).all()
    ctx = get_default_environment(Note(project=project), 'index')
    context = {'notes': notes, 'note_new_form': NoteNewForm(),
               'note_edit_form': NoteEditForm(), 'project': project}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index note on project #{project_id}")
    return render_template('notes/index.html', **ctx, **context)


@bp.route('/delete', methods=["POST"])
def note_delete():
    try:
        note_id = int(request.form.get('id'))
    except (TypeError, ValueError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to delete note with non-integer note_id {request.form.get('id')}")
        abort(400)
    try:
        note = db.session.scalars(sa.select(Note).where(Note.id == note_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    project_role_can_make_action_or_abort(current_user, note, 'delete')
    project_id = note.project_id
    db.session.delete(note)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete note #{note_id}")
    flash(_l("Note was successfully deleted"), 'success')
    return redirect(url_for('notes.note_index', project_id=project_id))
