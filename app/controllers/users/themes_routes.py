from app.controllers.users import bp
import app.controllers.users.themes_forms as forms
from app import db, side_libraries
from flask import request, redirect, url_for, render_template, abort, jsonify
from flask_login import current_user, login_required
import app.models as models
from app.helpers.main_page_helpers import DefaultEnvironment as MainPageEnvironment
from app.helpers.roles import user_position_can_make_action_or_abort
from flask_babel import lazy_gettext as _l
import sqlalchemy as sa


@bp.route('/themes/index')
@login_required
def user_themes_index():
    themes = db.session.scalars(sa.select(models.UserThemeStyle)).all()
    ctx = MainPageEnvironment('UserThemeStyle', 'index')()
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('contextmenu')
    return render_template('themes/index.html', themes=themes, **ctx)

@bp.route('/themes/new', methods=['GET', 'POST'])
@login_required
def user_themes_new():
    user_position_can_make_action_or_abort(current_user, models.UserThemeStyle, 'create')
    form = forms.ThemeStyleCreateForm()
    if form.validate_on_submit():
        theme = models.UserThemeStyle()
        form.populate_obj(db.session, theme, current_user)
        db.session.add(theme)
        db.session.commit()
        return redirect(url_for('users.user_themes_index'))
    elif request.method == 'GET':
        form.load_default_data(db.session, models.UserThemeStyle)
    ctx = MainPageEnvironment('UserThemeStyle', 'new')()
    return render_template('themes/new.html', form=form, **ctx)


@bp.route('/themes/<theme_id>/edit', methods=['GET', 'POST'])
@login_required
def user_themes_edit(theme_id):
    user_position_can_make_action_or_abort(current_user, models.UserThemeStyle, 'update')
    try:
        theme = db.session.get(models.UserThemeStyle, int(theme_id))
    except (ValueError, TypeError):
        abort(400)
    if theme is None:
        return redirect(url_for('users.user_themes_index'))
    form = forms.ThemeStyleEditForm()
    if form.validate_on_submit():
        form.populate_obj(db.session, theme, current_user)
        db.session.commit()
        return redirect(url_for('users.user_themes_index'))
    elif request.method == 'GET':
        form.load_exist_value(theme)
    ctx = MainPageEnvironment('UserThemeStyle', 'edit', obj_val=theme)()
    return render_template('themes/edit.html', form=form, **ctx)


@bp.route('/themes/<theme_id>/delete', methods=["POST"])
@login_required
def user_themes_delete(theme_id):
    user_position_can_make_action_or_abort(current_user, models.UserThemeStyle, 'delete')
    try:
        theme = db.session.get(models.UserThemeStyle, int(theme_id))
    except (ValueError, TypeError):
        abort(400)
    if theme is None:
        abort(404)
    db.session.delete(theme)
    db.session.commit()
    return jsonify({'status': "success"})