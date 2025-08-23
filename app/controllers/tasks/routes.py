from app import db, side_libraries, logger
from app.controllers.tasks import bp
from flask_login import current_user
from flask import request, render_template, url_for, redirect, flash, abort, jsonify
from app.models import ProjectTask, Project, ProjectTaskTracker, ProjectTaskPriority, User, TaskState, ProjectTaskTemplate
import app.models as models
from app.helpers.general_helpers import get_or_404, get_bootstrap_table_json_data, get_complementary_color, BootstrapTableSearchParams
from app.helpers.projects_helpers import get_default_environment
import app.controllers.tasks.forms as forms
import json
from bs4 import BeautifulSoup
import sqlalchemy as sa
from jinja2.filters import Markup
import textwrap
from flask_babel import lazy_gettext as _l
from app.helpers.roles import project_role_can_make_action_or_abort, project_role_can_make_action


@bp.route('/index-data')
def projecttask_index_data():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index all tasks with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, ProjectTask(), 'index', project_id=project_id)
    additional_params: BootstrapTableSearchParams = {'obj': ProjectTask,
                                                     'column_index': ['id', 'title', 'description', 'tracker', 'priority', 'state', 'readiness', 'assigned_to'],
                                                     'base_select': lambda x: x.where(ProjectTask.project_id==project_id),
                                                     'print_params': [('row_background_color', lambda x: getattr(x.priority, 'color', None)),
                                                                      ('task_background_color', lambda x: getattr(x.state, 'color', None)),
                                                                      ('task_text_color', lambda x: get_complementary_color(getattr(x.state, 'color', None)))]}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request all tasks on project #{project_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/index')
def projecttask_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index all tasks with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, Project, project_id)
    project_role_can_make_action_or_abort(current_user, ProjectTask(), 'index', project_id=project_id)
    filters = {}
    for obj in [ProjectTaskTracker, ProjectTaskPriority, User, TaskState]:
        now_obj = {}
        for i, t in db.session.execute(sa.select(obj.id, obj.title)):
            now_obj[i] = t
        filters[obj.__name__] = json.dumps(now_obj)
    ctx = get_default_environment(ProjectTask(project=project), 'index')
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('contextmenu')
    context = {'project': project, 'filters': filters}
    return render_template('tasks/index.html', **context, **ctx)


@bp.route('/index-on-me-data')
def projecttask_index_on_me_data():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index all tasks on user with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, ProjectTask(), 'index', project_id=project_id)
    additional_params: BootstrapTableSearchParams = {'obj': ProjectTask,
                                                     'column_index': ['id', 'title', 'description', 'tracker', 'priority', 'state', 'readiness', 'assigned_to'],
                                                     'base_select': lambda x: x.where(db.and_(ProjectTask.project_id==project_id, ProjectTask.assigned_to_id==current_user.id)),
                                                     'print_params': [('background_color', lambda x: getattr(x.priority, 'color', None))]}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request all tasks on user on project #{project_id}")
    return get_bootstrap_table_json_data(request, additional_params)


@bp.route('/index-on-me')
def projecttask_index_on_me():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index all tasks with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, Project, project_id)
    project_role_can_make_action_or_abort(current_user, ProjectTask(), 'index', project_id=project_id)
    filters = {}
    for obj in [ProjectTaskTracker, ProjectTaskPriority, User, TaskState]:
        now_obj = {}
        for i, t in db.session.execute(sa.select(obj.id, obj.title)):
            now_obj[i] = t
        filters[obj.__name__] = json.dumps(now_obj)
    ctx = get_default_environment(ProjectTask(project=project), 'index_on_me')
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('contextmenu')
    context = {'project': project, 'filters': filters}
    return render_template('tasks/index-on-me.html', **context, **ctx)


@bp.route('/kanban-board')
def projecttask_kanban_board():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index tasks in kanban board with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, Project, project_id)
    project_role_can_make_action_or_abort(current_user, ProjectTask(), 'kanban', project_id=project_id)
    ctx = get_default_environment(ProjectTask(project=project), 'kanban-board')
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request task kanban board on project #{project_id}")
    return render_template('/tasks/kanban_board.html', project=project, **ctx)


@bp.route('/kanban-board/data')
def projecttask_kanban_board_data():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request index tasks in kanban board with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    conf = {"row": []}
    project = get_or_404(db.session, Project, project_id)
    project_role_can_make_action_or_abort(current_user, ProjectTask(), 'kanban', project_id=project_id)
    tasks = db.session.scalars(sa.select(ProjectTask).where(ProjectTask.project_id==project.id)).all()
    statuses = db.session.execute(sa.select(TaskState.id, TaskState.title, TaskState.color, TaskState.icon)).all()
    priorities = db.session.execute(sa.select(ProjectTaskPriority.id, ProjectTaskPriority.title, ProjectTaskPriority.description, ProjectTaskPriority.color)).all()
    for id, title, color, icon in statuses:
        conf["row"].append({"COLUMN_ID": id,
                            "COLUMN_TITLE": title,
                            "COLUMN_ICON": icon,
                            "COLUMN_COLOR": color,
                            "COLUMN_HEADER_STYLE": f"border-color: {color}"})
    for id, title, description, color in priorities:
        conf["row"].append({"GROUP_ID": id,
                            "GROUP_TITLE": title,
                            "GROUP_ICON": "fa-solid fa-circle-exclamation",
                            "GROUP_HEADER_STYLE": f"background-color:{color}",
                            "GROUP_FOOTER": description})
    for task in tasks:
        conf["row"].append({"COLUMN_ID": task.state_id,
                            "COLUMN_TITLE": task.state.title,
                            "COLUMN_ICON": task.state.icon,
                            "COLUMN_HEADER_STYLE": f"border-color: {task.state.color}",
                            "GROUP_ID": task.priority_id,
                            "GROUP_TITLE": task.priority.title,
                            "GROUP_ICON": "fa-solid fa-circle-exclamation",
                            "GROUP_FOOTER": task.priority.description,
                            "ID": task.id,
                            "TITLE": task.title,
                            "FOOTER":  textwrap.shorten(BeautifulSoup(Markup.unescape(task.description), 'lxml').text, width=50, placeholder='...'),
                            "ICON": "",
                            "LINK": url_for('tasks.projecttask_show', projecttask_id=task.id),
                            "ICON_COLOR": "",
                            "HEADER_STYLE": ""})
    return jsonify(conf)


@bp.route('/kanban-board/config')
def projecttask_kanban_board_config():
    conf = {'refresh': 15 * 60, # Параметр refresh отвечает за обновление страницы и задаётся в секундах
            'dynamicColumns': True,
            'groupExtension': True,
            'groupColWidth': 8,
            'groupCollapsible': True,
            'printDataToConsole': False,
            'allowDragItemsBetweenGroups': True, # Разрешает передавать задачи между группами (приоритетами)
            'staticColumns': []}
    statuses = db.session.execute(sa.select(TaskState.id, TaskState.title, TaskState.color, TaskState.icon))
    for id, title, color, icon in statuses:
        conf['staticColumns'].append({'COLUMN_ID': str(id), 'COLUMN_TITLE': title, 'COLUMN_ICON': icon, "COLUMN_COLOR": color})
    return jsonify(conf)


@bp.route('/new', methods=["GET", "POST"])
def projecttask_new():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request create task with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project = get_or_404(db.session, Project, project_id)
    project_role_can_make_action_or_abort(current_user, ProjectTask(), 'create', project_id=project.id)
    form = forms.ProjectTaskCreateForm(project_id)
    if form.validate_on_submit():
        task = ProjectTask()
        db.session.add(task)
        project.tasks.append(task)
        form.populate_obj(db.session, task, current_user)
        db.session.commit()
        project_parent_dir = db.session.scalars(sa.select(models.FileDirectory).where(sa.and_(models.FileDirectory.project_id==project_id, models.FileDirectory.parent_dir_id==None))).one()
        task_file_directory = db.session.scalars(sa.select(models.FileDirectory).where(sa.and_(models.FileDirectory.parent_dir_id==project_parent_dir.id, models.FileDirectory.title==str(_l("Tasks files"))))).first()
        if task_file_directory is None:
            task_file_directory = models.FileDirectory(title=str(_l("Tasks files")), parent_dir_id=project_parent_dir.id, project_id=project_id)
            db.session.add(task_file_directory)
        for f in form.related_files.data:
            if f.content_length == 0 and f.content_type == 'application/octet-stream' and f.filename == '' and f.mimetype == 'application/octet-stream':
                continue
            fn = f.filename
            nf = models.FileData(title=fn, extension=fn.split('.')[-1], data=f.read(), description=str(_l("File for Project Task #%(task_id)s", task_id=task.id)))
            nf.directory = task_file_directory
            task.related_files.append(nf)
            db.session.add(nf)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new project task #{task.id}")
        flash(_l("Task #%(task_id)s has been successfully added", task_id=task.id), 'success')
        if form.submit_and_add_new.data:
            return redirect(url_for('tasks.projecttask_new', **request.args))
        if project_role_can_make_action(current_user, task, 'show'):
            return redirect(url_for('tasks.projecttask_show', projecttask_id=task.id))
        return redirect(url_for('tasks.projecttask_index', project_id=project_id))
    elif request.method == 'GET':
        form.load_default_data(db.session, ProjectTask)
        form.load_data_from_json(request.args)
    patterns = db.session.scalars(sa.select(ProjectTaskTemplate).where(ProjectTaskTemplate.archived == False)).all()
    ctx = get_default_environment(ProjectTask(project=project), 'new')
    context = {'form': form, 'patterns': patterns}
    return render_template('tasks/new.html', **context, **ctx)


@bp.route('/<projecttask_id>')
@bp.route('/<projecttask_id>/show')
def projecttask_show(projecttask_id):
    try:
        task_id = int(projecttask_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request create task with non-integer projecttask_id {projecttask_id}")
        abort(404)
    task = db.get_or_404(ProjectTask, task_id)
    project_role_can_make_action_or_abort(current_user, task, 'show')
    ctx = get_default_environment(task, 'show')
    fast_edit_form = forms.ProjectTaskEditForm(task.state, task.project_id, task)
    fast_edit_form.load_exist_value(task)
    side_libraries.library_required('ckeditor')
    side_libraries.library_required('bootstrap_table')
    context = {'task': task, 'edit_related_objects': forms.EditRelatedObjectsForm(task),
               'fast_edit_form': fast_edit_form}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request project task #{task.id}")
    side_libraries.library_required('contextmenu')
    return render_template('tasks/show.html', **context, **ctx)


@bp.route('/<projecttask_id>/edit', methods=['GET', 'POST'])
def projecttask_edit(projecttask_id):
    task = get_or_404(db.session, ProjectTask, projecttask_id)
    try:
        projecttask_id = int(projecttask_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request edit task with non-integer projecttask_id {projecttask_id}")
        abort(404)
    project_role_can_make_action_or_abort(current_user, task, 'update')
    form = forms.ProjectTaskEditForm(task.state, task.project_id, task)
    if form.validate_on_submit():
        form.populate_obj(db.session, task)
        task.updated_by_id = current_user.id
        project_parent_dir = db.session.scalars(sa.select(models.FileDirectory).where(sa.and_(models.FileDirectory.project_id==task.project_id, models.FileDirectory.parent_dir_id==None))).one()
        task_file_directory = db.session.scalars(sa.select(models.FileDirectory).where(sa.and_(models.FileDirectory.parent_dir_id==project_parent_dir.id, models.FileDirectory.title==str(_l("Tasks files"))))).first()
        if task_file_directory is None:
            task_file_directory = models.FileDirectory(title=str(_l("Tasks files")), parent_dir_id=project_parent_dir.id, project_id=task.project_id)
            db.session.add(task_file_directory)
        for f in form.related_files.data:
            if f.content_length == 0 and f.content_type == 'application/octet-stream' and f.filename == '' and f.mimetype == 'application/octet-stream':
                continue
            fn = f.filename
            nf = models.FileData(title=fn, extension=fn.split('.')[-1], data=f.read(), description=str(_l("File for Project Task #%(task_id)s", task_id=task.id)))
            nf.directory = task_file_directory
            db.session.add(nf)
            task.related_files.append(nf)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit project task #{task.id}")
        flash(_l("Task #%(task_id)s successfully changed", task_id=projecttask_id), 'success')
        return redirect(url_for('tasks.projecttask_show', projecttask_id=task.id))
    elif request.method == 'GET':
        form.load_exist_value(task)
    ctx = get_default_environment(task, 'edit')
    return render_template('tasks/edit.html', form=form, **ctx)


@bp.route('/<projecttask_id>/delete', methods=["POST"])
def projecttask_delete(projecttask_id: str):
    try:
        projecttask_id = int(projecttask_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request delete task with non-integer projecttask_id {projecttask_id}")
        abort(400)
    task = get_or_404(db.session, ProjectTask, projecttask_id)
    project_role_can_make_action_or_abort(current_user, task, 'delete')
    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete project task #{projecttask_id}")
    flash(_l("Task #%(task_id)s successfully deleted", task_id=projecttask_id), 'success')
    return redirect(url_for('tasks.projecttask_index', project_id=project_id))


@bp.route('/task_data_by_template/<template_id>')
def projecttask_data_by_template(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' request project task template data with non-integer template_id {template_id}")
        abort(400)
    templ = get_or_404(db.session, ProjectTaskTemplate, template_id)
    res = {'title': templ.task_title,
           'description': templ.task_description,
           'tracker': templ.task_tracker_id or 0,
           'priority': templ.task_priority_id or 0}
    if templ.task_estimation_time_cost is None:
        res['eta'] = None
    else:
        res['eta'] = templ.task_estimation_time_cost.seconds // 3600
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request data from project task template #{template_id}")
    return jsonify(res)
