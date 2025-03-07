from flask import Blueprint
from flask_login import login_required
from app.helpers.roles import administrator_only


bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.before_request
@login_required
@administrator_only
def check_user_permissions():
    pass


import app.controllers.admin.routes
import app.controllers.admin.routes_file_processing
import app.controllers.admin.routes_background_tasks
import app.controllers.admin.routes_roles
import app.controllers.admin.task_template_routes
import app.controllers.admin.report_template_routes
import app.controllers.admin.credential_template_import
import app.controllers.admin.authentication_routes