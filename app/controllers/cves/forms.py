import wtforms
import wtforms.validators as validators
import datetime
from app import db
from app.controllers.forms import FlaskForm, WysiwygField, TreeSelectSingleField
from app.models import CriticalVulnerability, VulnerableEnvironmentType, ProgrammingLanguage, WikiPage
from flask_babel import lazy_gettext as _l


class CriticalVulnerabilityForm(FlaskForm):
    def __init__(self, session, *args, **kwargs):
        super(CriticalVulnerabilityForm, self).__init__(*args, **kwargs)
        self.vulnerable_environment_type_id.choices = [('0', '')] + [(str(i[0]), i[1]) for i in session.execute(db.select(VulnerableEnvironmentType.id, VulnerableEnvironmentType.title))]
        self.proof_of_concept_language_id.choices = [('0', '')] + [(str(i.id), i) for i in session.scalars(db.select(ProgrammingLanguage))]
        self.wikipage_id.choices = [('0', '')] + [(str(i.id), i) for i in session.scalars(db.select(WikiPage))]
    year = wtforms.IntegerField(_l("%(field_name)s:", field_name=CriticalVulnerability.year.info["label"]), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    identifier = wtforms.StringField(_l("%(field_name)s:", field_name=CriticalVulnerability.identifier.info["label"]),
                                     validators=[validators.InputRequired(message=_l("This field is mandatory!")),
                                                 validators.Length(max=CriticalVulnerability.identifier.type.length, message=_l('This field must not exceed %(length)s characters in length', length=CriticalVulnerability.identifier.type.length))])
    title = wtforms.StringField(_l("%(field_name)s:", field_name=CriticalVulnerability.title.info["label"]),
                                validators=[validators.Optional(),
                                            validators.Length(max=CriticalVulnerability.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=CriticalVulnerability.title.type.length))])
    description = WysiwygField(_l("%(field_name)s:", field_name=CriticalVulnerability.description.info["label"]),
                               validators=[validators.Optional()], description=_l("Detailed description of the vulnerability"), id="CriticalVulnerabilityDescription")
    cvss = wtforms.FloatField(_l("%(field_name)s:", field_name=CriticalVulnerability.cvss.info["label"]),
                              validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    vulnerable_environment_type_id = wtforms.SelectField(_l("%(field_name)s:", field_name=CriticalVulnerability.vulnerable_environment_type_id.info["label"]),
                                                         validators=[validators.Optional()])
    vulnerable_environment = WysiwygField(_l("%(field_name)s:", field_name=CriticalVulnerability.vulnerable_environment.info["label"]),
                                          validators=[validators.Optional()])
    proof_of_concept_language_id = TreeSelectSingleField(_l("%(field_name)s:", field_name=CriticalVulnerability.proof_of_concept_language_id.info["label"]),
                                                         validators=[validators.Optional()])
    proof_of_concept_code = WysiwygField(_l("%(field_name)s:", field_name=CriticalVulnerability.proof_of_concept_code.info["label"]),
                                         validators=[validators.Optional()])
    wikipage_id = TreeSelectSingleField(_l("%(field_name)s:", field_name=CriticalVulnerability.wikipage_id.info["label"]))

    def validate_year(form, field):
        current_year = (datetime.datetime.now(datetime.UTC).year)
        if int(field.data) < 1970 or int(field.data) > current_year:
            raise validators.ValidationError(_l("The year cannot be less than 1970 and more than the current year!"))


class CriticalVulnerabilityCreateForm(CriticalVulnerabilityForm):
    submit = wtforms.SubmitField(_l("Create"))


class CriticalVulnerabilityEditForm(CriticalVulnerabilityForm):
    submit = wtforms.SubmitField(_l("Save"))