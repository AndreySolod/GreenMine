from app.controllers.admin import bp
from app import db, logger, side_libraries
import app.models as models
from flask import render_template, redirect, flash, url_for, request, abort
from flask_babel import lazy_gettext as _l
import sqlalchemy as sa
import app.controllers.admin.forms_global_permission_actions as forms
from app.helpers.admin_helpers import DefaultEnvironment
from app.helpers.general_helpers import get_global_objects_with_permissions
from flask_login import current_user


@bp.route('/user-positions/index')
def user_positions_index():
    all_positions = db.session.scalars(sa.select(models.UserPosition)).all()
    ctx = DefaultEnvironment()()
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('contextmenu')
    return render_template('admin/user_positions_index.html', **ctx, positions=all_positions)


@bp.route('/user-positions/new', methods=["GET", "POST"])
def user_positions_new():
    form = forms.UserPositionFormCreate()
    if form.validate_on_submit():
        position = models.UserPosition()
        form.populate_obj(db.session, position, current_user)
        db.session.add(position)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' created new user position #{position.id}: '{position.title}'")
        flash(_l("User position created successfully"), "success")
        return redirect(url_for("admin.user_positions_index"))
    elif request.method == "GET":
        form.load_default_data(db.session, models.UserPosition)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment()()
    return render_template("admin/user_positions_new.html", form=form, **ctx)


@bp.route('/user-positions/<position_id>/edit', methods=["GET", "POST"])
def user_positions_edit(position_id):
    try:
        position_id = int(position_id)
    except (ValueError, TypeError):
        abort(404)
    position = db.get_or_404(models.UserPosition, position_id)
    form = forms.UserPositionFormEdit(position)
    if form.validate_on_submit():
        form.populate_obj(db.session, position, current_user)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edited user position #{position.id}: '{position.title}'")
        flash(_l("User position edited successfully"), "success")
        return redirect(url_for("admin.user_positions_index"))
    elif request.method == "GET":
        form.load_exist_value(position)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment(position)()
    return render_template("admin/user_positions_edit.html", form=form, **ctx)


@bp.route('/user-positions/<position_id>/delete', methods=["POST"])
def user_positions_delete(position_id):
    try:
        position_id = int(position_id)
    except (ValueError, TypeError):
        abort(404)
    position = db.get_or_404(models.UserPosition, position_id)
    db.session.delete(position)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' deleted user position #{position.id}: '{position.title}'")
    flash(_l("User position deleted successfully"), "success")
    return redirect(url_for("admin.user_positions_index"))


@bp.route('/user-positions/permissions', methods=["GET", "POST"])
def user_positions_permissions():
    all_positions = db.session.scalars(sa.select(models.UserPosition).where(models.UserPosition.is_administrator == False)).all()
    form = forms.get_project_role_permission_form(all_positions)()
    if form.validate_on_submit():
        form.populate_permissions()
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edited user position permissions")
        flash(_l("User position permissions edited successfully"), "success")
        return redirect(url_for("admin.user_positions_index"))
    position_permissions = {}
    for o in get_global_objects_with_permissions():
        position_permissions[o] = {}
        for a in o.Meta.global_permission_actions.keys():
            position_permissions[o][a] = {}
            for r in all_positions:
                position_permissions[o][a][r] = getattr(form, 'position_' + str(r.id) + '____' + o.__name__ + '____' + a)
    ctx = DefaultEnvironment()()
    context = {'positions': all_positions, 'form': form, 'objs': get_global_objects_with_permissions(), 'position_permissions': position_permissions}
    return render_template("admin/user_positions_permissions.html", **ctx, **context)