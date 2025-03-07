from app import db, logger
from app.controllers.reports import bp
from flask_login import current_user
from flask import request, render_template, abort, send_file
import app.models as models
from app.helpers.general_helpers import get_or_404
from app.helpers.projects_helpers import get_default_environment
import docxtpl
import sqlalchemy as sa
from flask_babel import lazy_gettext as _l
from app.helpers.roles import project_role_can_make_action_or_abort
import jinja2
from io import BytesIO


@bp.route('/index')
def report_template_index():
    try:
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to get list report templates with non-integer project_id {request.args.get('project_id')}")
        abort(400)
    project_role_can_make_action_or_abort(current_user, models.ProjectReportTemplate(), 'index', project_id=project_id)
    project = get_or_404(db.session, models.Project, project_id)
    ctx = get_default_environment(models.ProjectReportTemplate(), 'index', proj=project)
    report_templates = db.session.scalars(sa.select(models.ProjectReportTemplate)).all()
    context = {'report_templates': report_templates, 'project': project}
    return render_template('report_templates/index.html', **ctx, **context)


@bp.route('/<template_id>/generate_template', methods=['GET'])
def generate_report_from_template(template_id):
    try:
        template_id = int(template_id)
        project_id = int(request.args.get('project_id'))
    except (ValueError, TypeError):
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' generate new report from template #{template_id} on project #{project_id}")
        abort(404)
    report_template = db.get_or_404(models.ProjectReportTemplate, template_id)
    project = db.get_or_404(models.Project, project_id)
    project_role_can_make_action_or_abort(current_user, models.ProjectReportTemplate(), 'create', project=project)
    try:
        if report_template.template.extension == 'docx': # https://docxtpl.readthedocs.io/en/latest/
            template_data = BytesIO()
            template_data.write(report_template.template.data)
            template_data.seek(0)
            env = docxtpl.DocxTemplate(template_file=template_data)
            env.render({'project': project, 'user': current_user})
            result = BytesIO()
            env.save(result)
        else:
            env = jinja2.Environment(loader=jinja2.BaseLoader).from_string(report_template.template.data.decode())
            result = BytesIO()
            result.write(env.render(project=project, user=current_user).encode())
        title = report_template.template.title
    except Exception as e:
        result = BytesIO()
        result.write(f"Error when parsing a template: {e}")
        title = "ERROR Report.txt"
    result.seek(0)
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' generate new report from template #{template_id} on project #{project_id}")
    params = {'as_attachment': True, 'download_name': title}
    return send_file(result, **params)