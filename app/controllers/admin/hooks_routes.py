from app.controllers.admin import bp
from flask import render_template, abort, redirect, url_for, request, flash, jsonify, current_app
from app import db, side_libraries, logger
from app.helpers.admin_helpers import DefaultEnvironment
import app.models as models
import sqlalchemy as sa
import app.controllers.admin.hooks_forms as forms
from flask_babel import lazy_gettext as _l
from flask_login import current_user


@bp.route('/hooks/index')
def hook_index():
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('contextmenu')
    objs = db.session.scalars(sa.select(models.Hook).order_by(models.Hook.priority.asc()))
    ctx = DefaultEnvironment()()
    return render_template('hooks/index.html', **ctx, objs=objs)


@bp.route('/hooks/new', methods=['GET', 'POST'])
def hook_new():
    side_libraries.library_required('ace')
    form = forms.HookCreateForm()
    if form.validate_on_submit():
        try:
            _ = compile(form.code.data, 'input code', 'exec')
        except Exception as e:
            logger.info(f"User {getattr(current_user, 'login', 'Anonymous')} try to save hook with invalid code block: {e.with_traceback()}")
            flash(_l("Invalid code block: %(error)", error=e.with_traceback()))
            return redirect(url_for('admin.hook_new'))
        hook = models.Hook()
        form.populate_obj(db.session, hook, current_user)
        db.session.add(hook)
        db.session.commit()
        models.Hook.load_hooks(current_app)
        flash(_l("New hook was sucessfully added"), 'success')
        return redirect(url_for('admin.hook_index'))
    if request.method == 'GET':
        form.load_default_data(db.session, models.Hook)
    ctx = DefaultEnvironment()()
    return render_template('hooks/new.html', **ctx, form=form)


@bp.route('/hooks/<hook_id>/edit', methods=["GET", "POST"])
def hook_edit(hook_id: str):
    try:
        hook = db.get_or_404(models.Hook, int(hook_id))
    except (ValueError, TypeError):
        abort(400)
    form = forms.HookEditForm()
    if form.validate_on_submit():
        try:
            _ = compile(form.code.data, 'input code', 'exec')
        except Exception as e:
            logger.info(f"User {getattr(current_user, 'login', 'Anonymous')} try to save hook with invalid code block: {e.with_traceback()}")
            flash(_l("Invalid code block: %(error)", error=e.with_traceback()))
            return redirect(url_for('admin.hook_edit', hook_id=hook_id))
        form.populate_obj(db.session, hook, current_user)
        db.session.commit()
        models.Hook.load_hooks(current_app)
        flash(_l("Hook was sucessfully updated"), 'success')
        return redirect(url_for('admin.hook_index'))
    elif request.method == 'GET':
        form.load_exist_value(hook)
    ctx = DefaultEnvironment(hook)()
    side_libraries.library_required('ace')
    return render_template('hooks/edit.html', **ctx, form=form)


@bp.route('/hooks/<hook_id>/delete', methods=['POST'])
def hook_delete(hook_id: str):
    try:
        hook = db.get_or_404(models.Hook, int(hook_id))
    except (ValueError, TypeError):
        abort(400)
    db.session.delete(hook)
    db.session.commit()
    models.Hook.load_hooks(current_app)
    flash(_l("Hook #%(hook_id)s was successfully deleted", hook_id = hook_id), 'success')
    return jsonify({'status': 'success'})