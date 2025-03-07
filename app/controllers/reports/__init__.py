from flask import Blueprint, url_for
from flask_login import current_user, login_required
from app.models import ProjectReportTemplate
from app.helpers.projects_helpers import EnvironmentObjectAttrs, register_environment, check_if_same_type
from app.helpers.general_helpers import CurrentObjectInfo, SidebarElement, SidebarElementSublink
from flask_babel import lazy_gettext as _l
from app.helpers.roles import project_role_can_make_action
from typing import Optional


bp = Blueprint('report_templates', __name__, url_prefix='/report_templates')


@bp.before_request
@login_required
def check_login_required():
    pass


import app.controllers.reports.routes


def sidebar(current_object, act: str, **kwargs) -> Optional[SidebarElement]:
    con = current_object.__class__.__name__
    if con == 'Project':
        proj = current_object
    elif "proj" in kwargs:
        proj = kwargs["proj"]
    else:
        proj = current_object.project
    sels = []
    if project_role_can_make_action(current_user, ProjectReportTemplate(), 'index', project=proj):
        sel1 = SidebarElementSublink(_l("All report templates"), url_for('report_templates.report_template_index', project_id=proj.id), con=='ProjectReportTemplate' and act=='index')
        sels.append(sel1)
    if len(sels) == 0:
        return None
    return SidebarElement(_l("Report templates"), url_for('report_templates.report_template_index', project_id=proj.id), ProjectReportTemplate.Meta.icon, con=='ProjectReportTemplate', sels)


@check_if_same_type(ProjectReportTemplate)
def environment(obj, action, **kwargs) -> dict:
    acts = []
    if action == 'index':
        title = _l("All report templates")
        current_object = CurrentObjectInfo(title, obj.Meta.icon, subtitle=kwargs['proj'].fulltitle, actions=acts)
    return {'title': title, 'current_object': current_object}


register_environment(EnvironmentObjectAttrs('ProjectReportTemplate', sidebar, environment), after='ChatMessage')