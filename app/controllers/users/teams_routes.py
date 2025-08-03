from app import db, side_libraries, logger
import app.models as models
from app.controllers.users import bp
import app.controllers.users.teams_forms as forms
from flask import url_for, flash, abort, redirect, render_template, request
import sqlalchemy as sa
from app.helpers.main_page_helpers import DefaultEnvironment
from flask_login import current_user, login_required
from flask_babel import lazy_gettext as _l
from app.helpers.roles import user_position_can_make_action_or_abort


@bp.route('/teams/index')
@login_required
def team_index():
    teams = db.session.scalars(sa.select(models.Team)).all()
    env = DefaultEnvironment('Team', 'team_index')()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request teams list")
    return render_template('teams/index.html', teams=teams, **env)


@bp.route('/teams/new', methods=["GET", "POST"])
@login_required
def team_new():
    user_position_can_make_action_or_abort(current_user, models.Team, 'create')
    form = forms.get_team_create_form()()
    if form.validate_on_submit():
        team = models.Team()
        form.populate_obj(db.session, team, current_user)
        form.load_team_members()
        db.session.add(team)
        db.session.commit()
        flash(_l("Team successfully created"), 'success')
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new team #{team.id}")
        return redirect(url_for('users.team_show', team_id=team.id))
    elif request.method == 'GET':
        form.load_default_data(db.session, models.Team)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment('Team', 'team_new')()
    return render_template('teams/new.html', **ctx, form=form)


@bp.route('/teams/<team_id>/show')
@login_required
def team_show(team_id):
    try:
        team = db.get_or_404(models.Team, int(team_id))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' try to get team with non-integer team_id #{team_id}")
        abort(400)
    user_position_can_make_action_or_abort(current_user, team, 'show')
    ctx = DefaultEnvironment('Team', 'team_show', obj_val=team)()
    context = {'team': team}
    return render_template('teams/show.html', **ctx, **context)


@bp.route('/teams/<team_id>edit', methods=["GET", "POST"])
@login_required
def team_edit(team_id):
    try:
        team = db.get_or_404(models.Team, int(team_id))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' try to edit team with non-integer team_id #{team_id}")
        abort(400)
    user_position_can_make_action_or_abort(current_user, team, 'edit')
    form = forms.get_team_edit_form(team)()
    if form.validate_on_submit():
        form.populate_obj(db.session, team, current_user)
        form.load_team_members()
        db.session.commit()
        flash(_l("Team #%(team_id)s successfully edited", team_id=team.id), 'success')
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit team #{team.id}")
        return redirect(url_for('users.team_show', team_id=team.id))
    elif request.method == 'GET':
        form.load_exist_value(team)
        form.load_exist_members()
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment('Team', 'team_edit', obj_val=team)()
    return render_template('teams/edit.html', **ctx, form=form)


@bp.route('/teams/<team_id>/delete', methods=["POST", "DELETE"])
@login_required
def team_delete(team_id):
    try:
        team = db.get_or_404(models.Team, int(team_id))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' try to delete team with non-integer team_id #{team_id}")
        abort(400)
    user_position_can_make_action_or_abort(current_user, team, 'delete')
    db.session.delete(team)
    db.session.commit()
    flash(_l("Team #%(team_id)s successfully deleted", team_id=team.id), 'success')
    return redirect(url_for('users.team_index'))
