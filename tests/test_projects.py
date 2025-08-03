from app import db
import app.models as models
from flask.testing import FlaskClient
import sqlalchemy as sa
from flask import url_for
from urllib.parse import urlparse
import datetime


def test_projects(auth_client: FlaskClient):
    index = auth_client.get(url_for('projects.project_index', _external=False))
    assert index.status_code == 200, f"Project index page status code is {index.status_code}"
    # New project
    new_get = auth_client.get(url_for('projects.project_new', _external=False))
    assert new_get.status_code == 200, f"New project page status code is {new_get.status_code}"
    post_data = {"title": "Test project", "description": "Test description", "start_at": "2025-07-26", "end_at": "2025-07-30", "leader": 1}
    new_post = auth_client.post(url_for('projects.project_new', _external=False), data=post_data, follow_redirects=True)
    assert new_post.status_code == 200, f"New project page status code is {new_post.status_code}"
    assert len(new_post.history) == 1, f"Incorrect count of redirect history after new project page: {len(new_post.history)}"
    project = db.session.scalars(sa.select(models.Project).where(models.Project.title == "Test project")).first()
    assert project is not None, f"Cannot create new project in database"
    assert urlparse(new_post.request.url).path == url_for('projects.project_show', _external=False, project_id=project.id), f"Incorrect redirect after new project page."
    # Edit project
    edit_get = auth_client.get(url_for('projects.project_edit', project_id=project.id, _external=False))
    assert edit_get.status_code == 200, f"Project edit page status code is {edit_get.status_code}"
    post_data = {"title": "Edit project", "description": "Edit description", "start_at": "2025-07-23", "end_at": "2025-08-30", "leader": 1, "teams": ""}
    edit_post = auth_client.post(url_for('projects.project_edit', _external=False, project_id=project.id), data=post_data, follow_redirects=True)
    assert edit_post.status_code == 200, f"Edit project request status code is {edit_post.status_code}"
    assert len(edit_post.history) == 1, f"Incorrect count of redirect history after edit project page: {len(edit_post.history)}"
    assert urlparse(edit_post.request.url).path == url_for('projects.project_show', _external=False, project_id=project.id), f"Incorrect redirect after edit project page."
    # Delete project
    p = models.Project(title="Delete proj", description="Delete description", start_at=datetime.date.fromisoformat("2025-07-26"),
                       end_at=datetime.date.fromisoformat("2025-07-30"), leader_id=1)
    db.session.add(p)
    db.session.commit()
    another_project_show = auth_client.get(url_for('projects.project_show', project_id=p.id, _external=False))
    assert another_project_show.status_code == 200, f"Another project show page status code is {another_project_show.status_code}"
    delete_post = auth_client.post(url_for('projects.project_delete', project_id=p.id, _external=False), follow_redirects=True)
    assert delete_post.status_code == 200, f"Delete project request status code is {delete_post.status_code}"
    assert len(delete_post.history) == 1, f"Incorrect count of redirect history after delete project page: {len(delete_post.history)}"
    assert urlparse(delete_post.request.url).path == url_for('projects.project_index', _external=False), f"Incorrect redirect after delete project page."
    assert db.session.scalars(sa.select(models.Project).where(models.Project.id == p.id)).first() is None, f"Cannot delete project from database"
    # Edit participanbs
    role_data = {"role_1": [1], "role_2": [2]}
    edit_participants = auth_client.post(url_for("projects.edit_project_participants", _external=False, project_id=project.id), data=role_data, follow_redirects=True)
    assert edit_participants.status_code == 200, f"Edit participants request status code is {edit_participants.status_code}"
    assert len(edit_participants.history) == 1, f"Incorrect count of redirect history after edit participants page: {len(edit_participants.history)}"
    assert urlparse(edit_participants.request.url).path == url_for('projects.project_show', _external=False, project_id=project.id), f"Incorrect redirect after edit participants page."
    db.session.refresh(project)
    for pt in project.participants:
        assert pt.user_id == 1 and pt.role_id == 1 or pt.user_id == 2 and pt.role_id == 2, f"Incorrect value of {pt.user_id} user_id and {pt.role_id} role_id attribute in project"
    # Archive project
    archive_post = auth_client.post(url_for('projects.project_archive', project_id=project.id, _external=False), follow_redirects=True)
    assert archive_post.status_code == 200, f"Archive project request status code is {archive_post.status_code}"
    assert len(archive_post.history) == 1, f"Incorrect count of redirect history after archive project page: {len(archive_post.history)}"
    assert urlparse(archive_post.request.url).path == url_for('projects.project_index', _external=False), f"Incorrect redirect after archive project page."
    # Unarchive project
    db.session.refresh(project)
    assert project.archived, f"Cannot archive project"
    project.archived = False
    db.session.add(project)
    db.session.commit()
    # Diagrams
    diagram_get = auth_client.get(url_for('projects.project_diagrams', project_id=project.id, _external=False))
    assert diagram_get.status_code == 200, f"Project diagrams page status code is {diagram_get.status_code}"
    # Project additional parameters index
    additional_parameters = auth_client.get(url_for('projects.project_additional_parameter_index', project_id=project.id, _external=False))
    assert additional_parameters.status_code == 200, f"Project additional parameters page status code is {additional_parameters.status_code}"
    # Project additional parameters edit
    add_param_edit_get = auth_client.get(url_for('projects.project_additional_parameter_edit', project_id=project.id, _external=False))
    assert add_param_edit_get.status_code == 200, f"Project additional parameters edit page status code is {add_param_edit_get.status_code}"


def test_project_tasks(auth_client: FlaskClient):
    project = db.session.scalars(sa.select(models.Project).where(models.Project.title == "Edit project")).first()
    assert project is not None, f"Cannot find project in database"
    # Create task
    new_task_get = auth_client.get(url_for('tasks.projecttask_new', project_id=project.id, _external=False))
    assert new_task_get.status_code == 200, f"New task page status code is {new_task_get.status_code}"
    post_data = {"title": "New task", "description": "New description", "date_start": "2025-07-23", "date_end": "2025-08-30", "priority_id": 1, "tracker_id": 1,
                 "assigned_to_id": 1, "parent_task_id": 0, "observers": [], "estimation_time_cost": "5", "issues": [], "services": [], "related_files": []}
    new_task_post = auth_client.post(url_for('tasks.projecttask_new', project_id=project.id, _external=False), data=post_data, follow_redirects=True)
    assert new_task_post.status_code == 200, f"Create task request status code is {new_task_post.status_code}"
    assert len(new_task_post.history) == 1, f"Incorrect count of redirect history after create task page: {len(new_task_post.history)}"
    new_task = db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.title == "New task")).first()
    assert new_task is not None, f"Cannot find new task in database"
    assert urlparse(new_task_post.request.url).path == url_for('tasks.projecttask_show', _external=False, projecttask_id=new_task.id), f"Incorrect redirect after create task page."
    # index
    index = auth_client.get(url_for('tasks.projecttask_index', project_id=project.id, _external=False))
    assert index.status_code == 200, f"Index page status code is {index.status_code}"
    index_data = auth_client.get(url_for('tasks.projecttask_index_data', project_id=project.id, limit=10, offset=0, search="", _external=False))
    assert index_data.status_code == 200, f"Index data status code is {index_data.status_code}"
    assert "New task" in index_data.text, f"Cannot find new task in index page"
    index_on_me = auth_client.get(url_for('tasks.projecttask_index_on_me', project_id=project.id, _external=False))
    assert index_on_me.status_code == 200, f"Index on me page status code is {index_on_me.status_code}"
    kanban_board = auth_client.get(url_for('tasks.projecttask_kanban_board', project_id=project.id, _external=False))
    assert kanban_board.status_code == 200, f"Kanban board page status code is {kanban_board.status_code}"
    kanban_board_data = auth_client.get(url_for('tasks.projecttask_kanban_board_data', project_id=project.id, _external=False))
    assert kanban_board_data.status_code == 200, f"Kanban board data page status code is {kanban_board_data.status_code}"
    kanban_board_config = auth_client.get(url_for('tasks.projecttask_kanban_board_config', project_id=project.id, _external=False))
    assert kanban_board_config.status_code == 200, f"Kanban board config page status code is {kanban_board_config.status_code}"
    # Edit task
    edit_get = auth_client.get(url_for('tasks.projecttask_edit', projecttask_id=new_task.id, _external=False))
    assert edit_get.status_code == 200, f"Edit task page status code is {edit_get.status_code}"
    post_data = {"title": "Edit task", "description": "Edit description", "date_start": "2025-07-21", "date_end": "2025-08-22", "priority_id": 2, "tracker_id": 2,
                 "assigned_to_id": 2, "parent_task_id": 0, "observers": [], "estimation_time_cost": "4", "issues": [], "services": [], "related_files": [],
                 "readiness": 22, "state_id": 2}
    edit_post = auth_client.post(url_for('tasks.projecttask_edit', projecttask_id=new_task.id, _external=False), data=post_data, follow_redirects=True)
    assert edit_post.status_code == 200, f"Edit task request status code is {edit_post.status_code}"
    assert len(edit_post.history) == 1, f"Incorrect count of redirect history after edit task page: {len(edit_post.history)}"
    assert urlparse(edit_post.request.url).path == url_for('tasks.projecttask_show', _external=False, projecttask_id=new_task.id), f"Incorrect redirect after edit task page."
    # delete task
    delete_post = auth_client.post(url_for('tasks.projecttask_delete', projecttask_id=new_task.id, _external=False), follow_redirects=True)
    assert delete_post.status_code == 200, f"Delete task request status code is {delete_post.status_code}"
    assert len(delete_post.history) == 1, f"Incorrect count of redirect history after delete task page: {len(delete_post.history)}"
    assert urlparse(delete_post.request.url).path == url_for('tasks.projecttask_index', _external=False), f"Incorrect redirect after delete task page."


def test_networks(auth_client: FlaskClient):
    index = auth_client.get(url_for('networks.network_index', project_id=1, _external=False))
    assert index.status_code == 200, f"Index page status code is {index.status_code}"
    # new network
    new_get = auth_client.get(url_for('networks.network_new', project_id=1, _external=False))
    assert new_get.status_code == 200, f"New network page status code is {new_get.status_code}"
    post_data = {"title": "New network", "description": "New description", "ip_address": "10.0.0.0/8", "internal_ip": "10.0.0.0/8", "asn": "10",
                 "connect_cmd": "connect", "vlan_number": "10"}
    new_post = auth_client.post(url_for('networks.network_new', project_id=1, _external=False), data=post_data, follow_redirects=True)
    assert new_post.status_code == 200, f"Create network request status code is {new_post.status_code}"
    assert len(new_post.history) == 1, f"Incorrect count of redirect history after create network page: {len(new_post.history)}"
    network = db.session.scalars(sa.select(models.Network).where(models.Network.title == "New network")).first()
    assert network is not None, f"Cannot find new network in database"
    assert urlparse(new_post.request.url).path == url_for('networks.network_show', network_id=network.id, _external=False), f"Incorrect redirect after create network page."
    # edit network
    edit_get = auth_client.get(url_for('networks.network_edit', network_id=network.id, _external=False))
    assert edit_get.status_code == 200, f"Edit network page status code is {edit_get.status_code}"
    post_data = {"title": "Edit network", "description": "Edit description", "ip_address": "10.0.0.0/8", "internal_ip": "10.0.0.0/8", "asn": "10",
                 "connect_cmd": "connect", "vlan_number": "10"}
    edit_post = auth_client.post(url_for('networks.network_edit', network_id=network.id, _external=False), data=post_data, follow_redirects=True)
    assert edit_post.status_code == 200, f"Edit network request status code is {edit_post.status_code}"
    assert len(edit_post.history) == 1, f"Incorrect count of redirect history after edit network page: {len(edit_post.history)}"
    assert urlparse(edit_post.request.url).path == url_for('networks.network_show', network_id=network.id, _external=False), f"Incorrect redirect after edit network page."
    # index-data
    