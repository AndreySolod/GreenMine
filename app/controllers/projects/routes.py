from app import db, logger
from app.controllers.projects import bp
from flask import request, redirect, url_for, render_template, flash, abort
from flask_login import login_required, current_user
import app.models as models
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo, SidebarElement, get_or_404
from app.helpers.projects_helpers import get_default_environment
from app.helpers.main_page_helpers import DefaultEnvironment as MainPageEnvironment
from .forms import ProjectForm, EditProjectForm, get_project_role_user_form
from flask_babel import lazy_gettext as _l
from app.helpers.roles import project_role_can_make_action_or_abort
import sqlalchemy as sa


@bp.route("/index")
@login_required
def project_index():
    p = db.session.scalars(sa.select(models.Project).where(models.Project.archived == False).order_by(models.Project.created_at.desc())).all()
    archived = db.session.scalars(sa.select(models.Project).where(models.Project.archived == True).order_by(models.Project.created_at.desc())).all()
    ctx = MainPageEnvironment('Project', 'index')()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index all projects")
    context = {'projects': p, "archived": archived}
    return render_template('projects/index.html', **context, **ctx)


@bp.route("/<int:project_id>")
@bp.route("/<int:project_id>/show")
@login_required
def project_show(project_id):
    project = db.get_or_404(models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, project, 'show')
    project_role_user_form = get_project_role_user_form(project)(db.session)
    project_role_user_form.load_exist_value()
    ctx = get_default_environment(project, 'show')
    context = {'project': project, 'project_role_user_form': project_role_user_form}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request project #{project_id}")
    return render_template('projects/show.html', **ctx, **context)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def project_new():
    form = ProjectForm()
    ctx = MainPageEnvironment("Project", 'new')()
    if form.validate_on_submit():
        p = models.Project()
        form.populate_obj(db.session, p, current_user)
        db.session.add(p)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new project #{p.id}")
        flash(_l("Project #%(project_id)s has been successfully created", project_id=p.id), 'success')
        return redirect(url_for('projects.project_show', project_id=p.id))
    elif request.method == 'GET':
        form.load_data_from_json(request.args)
        form.leader.data = current_user.id
    return render_template('projects/new.html', form=form, **ctx)


@bp.route("/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def project_edit(project_id):
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, project, 'update')
    form = EditProjectForm()
    if form.validate_on_submit():
        form.populate_obj(db.session, project)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit project #{project.id}")
        flash(_l("Project #%(project_id)s successfully changed", project_id=project_id), 'success')
        return redirect(url_for('projects.project_show', project_id=project.id))
    elif request.method == "GET":
        form.load_exist_value(project)
        form.load_data_from_json(request.args)
    ctx = get_default_environment(project, 'edit')
    return render_template('projects/edit.html', form=form, **ctx)


@bp.route('/<int:project_id>/delete', methods=["POST"])
@login_required
def project_delete(project_id: int):
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, project, 'delete')
    db.session.delete(project)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete project #{project_id}")
    flash(_l("Project #%(project_id)s successfully deleted", project_id=project_id), 'success')
    return redirect(url_for('projects.project_index'))


@bp.route('/<int:project_id>/edit_participants', methods=['POST'])
@login_required
def edit_project_participants(project_id: int):
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, project, 'edit_participants')
    form = get_project_role_user_form(project)(db.session)
    if form.validate_on_submit():
        # firstly, drop old participants:
        for p in project.participants:
            db.session.delete(p)
        db.session.commit()
        # now load new participants
        form.load_project_role_participants()
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit roles on project #{project.id}")
        flash(_l("Roles on project #%(project_id)s successfully updated", project_id=project.id), 'success')
        return redirect(url_for('projects.project_show', project_id=project.id))
    abort(400)


@bp.route("/<int:project_id>/archive", methods=["POST"])
@login_required
def project_archive(project_id: int):
    project = get_or_404(db.session, models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, project, 'archive')
    project.archived = True
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' archive project #{project_id}")
    flash(_l("Project #%(project_id)s successfully archived", project_id=project_id), 'success')
    return redirect(url_for('projects.project_index'))