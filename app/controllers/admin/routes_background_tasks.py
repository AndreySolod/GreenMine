from app import celery, db, side_libraries
from app import automation_modules
from app.controllers.admin import bp
from app.helpers.admin_helpers import DefaultEnvironment
from flask import render_template
import app.models as models
import sqlalchemy.exc as exc


@bp.route('/background-tasks/index')
def background_tasks_index():
    inspect_tasks = celery.control.inspect()
    all_tasks = {}
    active_tasks = inspect_tasks.active()
    if active_tasks is not None:
        for worker_name, tasks in active_tasks.items():
            if worker_name not in all_tasks:
                all_tasks[worker_name] = []
            for t in tasks:
                task = automation_modules.get(t['name'][:t['name'].index('_exploit'):])
                try:
                    running_user = db.session.execute(db.select(models.User.title).where(models.User.id == t['args'][1])).one()[0]
                except (exc.MultipleResultsFound, exc.NoResultFound):
                    running_user = 'Удалённый пользователь'
                all_tasks[worker_name].append({'id': t['id'],'title': task.title, 'description': task.description, 'status': 'Активная', 'running_user': running_user})
    scheduled_tasks = inspect_tasks.scheduled()
    if scheduled_tasks is not None:
        for worker_name, tasks in scheduled_tasks.items():
            if worker_name not in all_tasks:
                all_tasks[worker_name] = []
            for t in tasks:
                task = automation_modules.get(t['request']['name'][:t['name'].index('_exploit'):])
                try:
                    running_user = db.session.execute(db.select(models.User.title).where(models.User.id == t['args'][1])).one()[0]
                except (exc.MultipleResultsFound, exc.NoResultFound):
                    running_user = 'Удалённый пользователь'
                all_tasks[worker_name].append({'id': t['id'],'title': task.title, 'description': task.description, 'status': 'Запланирована', 'running_user': running_user,
                                            'eta': t['eta']})
    reserved_tasks = inspect_tasks.reserved()
    if reserved_tasks is not None:
        for worker_name, tasks in reserved_tasks.items():
            if worker_name not in all_tasks:
                all_tasks[worker_name] = []
            for t in tasks:
                task = automation_modules.get(t['name'][:t['name'].index('_exploit'):])
                try:
                    running_user = db.session.execute(db.select(models.User.title).where(models.User.id == t['args'][1])).one()[0]
                except (exc.MultipleResultsFound, exc.NoResultFound):
                    running_user = 'Удалённый пользователь'
                all_tasks[worker_name].append({'id': t['id'],'title': task.title, 'description': task.description, 'status': 'Зарезервирована', 'running_user': running_user})
    ctx = DefaultEnvironment('background_tasks_index')()

    side_libraries.library_required('bootstrap_table')
    return render_template('admin/background_tasks_index.html', **ctx, all_tasks=all_tasks)


@bp.route('/background-tasks/options/index')
def background_tasks_options_index():
    all_modules = automation_modules.action_modules
    ctx = DefaultEnvironment('background_tasks_options_index')()
    side_libraries.library_required('bootstrap_table')
    return render_template('admin/background_tasks_options_index.html', **ctx, action_modules=all_modules)