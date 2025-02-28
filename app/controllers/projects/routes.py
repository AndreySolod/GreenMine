from app import db, logger, side_libraries
from app.controllers.projects import bp
from flask import request, redirect, url_for, render_template, flash, abort
from flask_login import login_required, current_user
import app.models as models
from app.helpers.general_helpers import CurrentObjectAction, CurrentObjectInfo, SidebarElement, get_or_404
from app.helpers.projects_helpers import get_default_environment
from app.helpers.main_page_helpers import DefaultEnvironment as MainPageEnvironment
from .forms import ProjectForm, EditProjectForm, get_project_role_user_form
from flask_babel import lazy_gettext as _l, pgettext
from app.helpers.roles import project_role_can_make_action_or_abort
import sqlalchemy as sa
import json


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


@bp.route("/<int:project_id>/diagrams")
@login_required
def project_diagrams(project_id: int):
    project = db.get_or_404(models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, project, 'show_charts')
    top_operation_systems = db.session.execute(sa.select(models.OperationSystemFamily.title, sa.func.count())
                                              .select_from(models.OperationSystemFamily).join(models.Host.operation_system_family, isouter=True)
                                              .join(models.Host.from_network, isouter=True)
                                              .where(models.Network.project_id == project_id)
                                              .group_by(models.OperationSystemFamily.id)
                                              .order_by(models.OperationSystemFamily.title)
                                              .limit(10)).all()
    top_ports = db.session.execute(sa.select(sa.cast(models.Service.port, sa.String) + "/" + sa.cast(models.ServiceTransportLevelProtocol.title, sa.String), sa.func.count())
                                   .select_from(models.Service)
                                   .join(models.Service.host, isouter=True)
                                   .join(models.Host.from_network, isouter=True)
                                   .join(models.Service.transport_level_protocol, isouter=True)
                                   .where(models.Network.project_id == project_id)
                                   .group_by(models.Service.port, models.ServiceTransportLevelProtocol.title)
                                   .order_by(sa.func.count().desc())
                                   .limit(10)).all()
    only_clear_password = db.session.scalars(sa.select(sa.func.count())
                                        .select_from(models.Credential)
                                        .where(sa.and_(models.Credential.password != '', models.Credential.password != None,
                                                       sa.or_(models.Credential.password_hash == '', models.Credential.password_hash == None),
                                                       models.Credential.is_pentest_credentials == False,
                                                       models.Credential.project_id == project_id))).one()
    password_and_hash = db.session.scalars(sa.select(sa.func.count())
                                           .select_from(models.Credential)
                                           .where(sa.and_(models.Credential.password != '', models.Credential.password != None,
                                                          models.Credential.password_hash != '', models.Credential.password_hash != None,
                                                          models.Credential.is_pentest_credentials == False,
                                                          models.Credential.project_id == project_id))).one()
    only_clear_hash = db.session.scalars(sa.select(sa.func.count())
                                         .select_from(models.Credential)
                                         .where(sa.and_(sa.or_(models.Credential.password == '', models.Credential.password == None),
                                                        models.Credential.password_hash != '', models.Credential.password_hash != None,
                                                        models.Credential.is_pentest_credentials == False,
                                                        models.Credential.project_id == project_id))).one()
    info_issues = db.session.scalars(sa.select(sa.func.count()).select_from(models.Issue)
                                     .where(sa.and_(models.Issue.cvss < 2.0, models.Issue.project_id == project_id))).one()
    low_issues = db.session.scalars(sa.select(sa.func.count()).select_from(models.Issue)
                                    .where(sa.and_(models.Issue.cvss >= 2.0, models.Issue.cvss < 5.0, models.Issue.project_id == project_id))).one()
    medium_issues = db.session.scalars(sa.select(sa.func.count()).select_from(models.Issue)
                                       .where(sa.and_(models.Issue.cvss >= 5.0, models.Issue.cvss < 8.0, models.Issue.project_id == project_id))).one()
    high_issues = db.session.scalars(sa.select(sa.func.count()).select_from(models.Issue)
                                     .where(sa.and_(models.Issue.cvss >= 8.0, models.Issue.cvss < 9.5, models.Issue.project_id == project_id))).one()
    critical_issues = db.session.scalars(sa.select(sa.func.count()).select_from(models.Issue)
                                         .where(sa.and_(models.Issue.cvss >= 9.5, models.Issue.project_id == project_id))).one()
    tasks_by_status = db.session.execute(sa.select(models.TaskState.title, models.TaskState.color, sa.func.count())
                                         .select_from(models.TaskState)
                                         .join(models.ProjectTask.state, isouter=True)
                                         .where(models.ProjectTask.project_id == project_id)
                                         .group_by(models.TaskState.title, models.TaskState.color)).all()
    otbs = tasks_by_status.copy()
    tasks_by_status = []
    for i in otbs:
        i = list(i)
        if i[1] == '' or i[1] == None:
            i[1] = '#00bfff'
        tasks_by_status.append(i)
    tasks_by_priority = db.session.execute(sa.select(models.ProjectTaskPriority.title, models.ProjectTaskPriority.color, sa.func.count())
                                         .select_from(models.ProjectTaskPriority)
                                         .join(models.ProjectTask.priority, isouter=True)
                                         .where(models.ProjectTask.project_id == project_id)
                                         .group_by(models.ProjectTaskPriority.title, models.ProjectTaskPriority.color)).all()
    otbp = tasks_by_priority.copy()
    tasks_by_priority = []
    for i in otbp:
        i = list(i)
        if i[1] == '' or i[1] == None:
            i[1] = '#00bfff'
        tasks_by_priority.append(i)
    ctx = get_default_environment(project, 'project_diagrams')
    context = {'project': project,
               'top_operation_systems_labels': json.dumps(list(map(lambda x: x[0] if x[0] != None else pgettext("woman", "Missing"), top_operation_systems))),
               'top_operation_systems_dataset': json.dumps(list(map(lambda x: x[1], top_operation_systems))),
               "top_ports_labels": json.dumps(list(map(lambda x: str(x[0]), top_ports))),
               "top_ports_dataset": json.dumps(list(map(lambda x: x[1], top_ports))),
               "issues_dataset": json.dumps([info_issues, low_issues, medium_issues, high_issues, critical_issues]),
               "passwords_dataset": json.dumps([only_clear_password, password_and_hash, only_clear_hash]),
               "tasks_by_priority_labels": json.dumps(list(map(lambda x: x[0] if x[0] is not None else pgettext("man", "Missing"), tasks_by_priority))),
               "tasks_by_priority_colors": json.dumps(list(map(lambda x: x[1], tasks_by_priority))),
               "tasks_by_priority_dataset": json.dumps(list(map(lambda x: x[2], tasks_by_priority))),
               "tasks_by_status_labels": json.dumps(list(map(lambda x: x[0] if x[0] is not None else pgettext("man", "Missing"), tasks_by_status))),
               "tasks_by_status_colors": json.dumps(list(map(lambda x: x[1], tasks_by_status))),
               "tasks_by_status_dataset": json.dumps(list(map(lambda x: x[2], tasks_by_status)))}
    side_libraries.library_required('chartjs')
    return render_template('projects/diagrams.html', **ctx, **context)