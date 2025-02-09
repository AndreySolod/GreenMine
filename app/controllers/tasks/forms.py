import wtforms
import wtforms.validators as validators
from wtforms import fields
from app import db
from app.controllers.forms import FlaskForm, WysiwygField, TreeSelectMultipleField, Select2MultipleField, ProgressBarField
import app.models as models
from flask import g
import sqlalchemy as sa
from flask_babel import lazy_gettext as _l
from flask import url_for
from app.helpers.projects_helpers import validate_service


class ProjectTaskForm(FlaskForm):
    def __init__(self, project_id, task=None, *args, **kwargs):
        super(ProjectTaskForm, self).__init__(*args, **kwargs)
        self.tracker_id.choices = [(i[0], i[1]) for i in db.session.execute(sa.select(models.ProjectTaskTracker.id, models.ProjectTaskTracker.title))]
        self.priority_id.choices = [(i[0], i[1]) for i in db.session.execute(sa.select(models.ProjectTaskPriority.id, models.ProjectTaskPriority.title))]
        self.assigned_to_id.choices = [('0', '---')] + [(i[0], i[1]) for i in 
                                                        db.session.execute(sa.select(models.User.id, models.User.title).join(models.User.project_roles)
                                                                           .where(models.UserRoleHasProject.project_id == project_id).distinct()
                                                                           .union(sa.select(models.User.id, models.User.title).select_from(models.Project).join(models.Project.leader)
                                                                                  .where(models.Project.id == project_id)))]
        self.parent_task_id.choices = [('0', '---')] + [(i[0], i[1]) for i in db.session.execute(sa.select(models.ProjectTask.id, models.ProjectTask.title)
                                                                                                 .where(models.ProjectTask.project_id==project_id))]
        if task is not None:
            self.parent_task_id.choices.remove((task.id, task.title))
        self.observers.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.User))]
        self.issues.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Issue).where(models.Issue.project_id == project_id))]
        self.services.callback = url_for('networks.get_select2_service_data', project_id=project_id)
        self.services.locale = g.locale
        self.services.validate_funcs = lambda x: validate_service(project_id, x)
    title = wtforms.StringField(_l("%(field_name)s:", field_name=models.ProjectTask.title.info["label"]),
                                validators=[validators.InputRequired(message=_l("This field is mandatory!")),
                                            validators.Length(max=models.ProjectTask.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.ProjectTask.title.type.length))])
    description = WysiwygField(_l("%(field_name)s:", field_name=models.ProjectTask.description.info["label"]),
                               validators=[validators.DataRequired(message=_l("This field is mandatory!"))],
                               description=_l("Detailed description of the task: what exactly is required to be done"))
    tracker_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.ProjectTask.tracker_id.info["label"]),
                                     validators=[validators.DataRequired(message=_l("This field is mandatory!"))], description=_l("A hypothesis about a possible problem"))
    priority_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.ProjectTask.priority_id.info["label"]),
                                      validators=[validators.DataRequired(message=_l("This field is mandatory!"))],
                                      description=_l("The assigned priority of the task. Simplifies filtering by tasks"))
    assigned_to_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.ProjectTask.assigned_to_id.info["label"]),
                                         description=_l("The person who will solve/solves this problem"), validators=[validators.Optional()])
    date_start = wtforms.DateField(_l("%(field_name)s:", field_name=models.ProjectTask.date_start.info["label"]), validators=[validators.Optional()])
    date_end = wtforms.DateField(_l("%(field_name)s:", field_name=models.ProjectTask.date_end.info["label"]),
                                 description=_l("The planned date by which this task will be completed"), validators=[validators.Optional()])
    parent_task_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.ProjectTask.parent_task_id.info["label"]),
                                         description=_l("In case this problem is solved to solve another problem"), validators=[validators.Optional()])
    observers = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.ProjectTask.observers.info["label"]), validators=[validators.Optional()])
    estimation_time_cost = fields.IntegerField(_l("%(field_name)s:", field_name=models.ProjectTask.estimation_time_cost.info["label"]),
                                               description=_l("The estimated time that must be spent to solve this problem"),
                                               validators=[validators.Optional()])
    issues = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.ProjectTask.issues.info["label"]), validators=[validators.Optional()])
    services = Select2MultipleField(models.Service, _l("%(field_name)s:", field_name=models.ProjectTask.services.info["label"]), validators=[validators.Optional()],
                                    attr_title='treeselecttitle')
    related_files = wtforms.MultipleFileField(_l("Upload related files:"), validators=[validators.Optional()])


class ProjectTaskCreateForm(ProjectTaskForm):
    submit = wtforms.SubmitField(_l("Create"))
    submit_and_add_new = wtforms.SubmitField(_l("Create and add another one"))


class ProjectTaskEditForm(ProjectTaskForm):
    def __init__(self, current_state, *args, **kwargs):
        super(ProjectTaskEditForm, self).__init__(*args, **kwargs)
        self.state_id.choices = [(i.id, i.title) for i in current_state.can_switch_to_state] + [(current_state.id, current_state.title)]
    state_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.ProjectTask.state_id.info["label"]))
    readiness = ProgressBarField(label=_l("%(field_name)s:", field_name=models.ProjectTask.readiness.info["label"]),
                                     validators=[validators.NumberRange(min=0, max=100, message=_l("Readiness should be in the range from 0 to 100%"))])
    submit = wtforms.SubmitField(_l("Save"))


class EditRelatedObjectsForm(FlaskForm):
    def __init__(self, task: models.ProjectTask, *args, **kwargs):
        super(EditRelatedObjectsForm, self).__init__(*args, **kwargs)
        self.related_tasks.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.ProjectTask).where(sa.and_(models.ProjectTask.project_id == task.project_id,
                                                                                                                             models.ProjectTask.id != task.id)))]
        self.related_tasks.data = [str(i.id) for i in task.related_tasks]
        self.issues.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Issue).where(models.Issue.project_id == task.project_id))]
        self.issues.data = [str(i.id) for i in task.issues]
        self.services.locale = g.locale
        self.services.callback = url_for('networks.get_select2_service_data', project_id=task.project_id)
        self.services.data = [str(i.id) for i in task.services]
    related_tasks = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.ProjectTask.related_tasks.info["label"]))
    issues = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.ProjectTask.issues.info["label"]), validators=[validators.Optional()], id='EditRelatedIssuesField')
    services = Select2MultipleField(models.Service, label=_l("%(field_name)s:", field_name=models.ProjectTask.services.info["label"]), validators=[validators.Optional()],
                                    attr_title='treeselecttitle', id='editRelatedServicesField')