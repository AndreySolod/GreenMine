from app import db
from app.controllers.forms import FlaskForm
from app.models import GlobalSettings, ApplicationLanguage
import wtforms
import wtforms.validators as validators
from app.controllers.forms import WysiwygField
from flask_babel import lazy_gettext as _l
import sqlalchemy as sa


class MainPageNameForm(FlaskForm):
    main_page_name = wtforms.StringField(GlobalSettings.main_page_name.info["label"], validators=[validators.DataRequired(message=_l("This field is mandatory!")), validators.Length(max=GlobalSettings.main_page_name.type.length)])

class MainPageTextForm(FlaskForm):
    text_main_page = WysiwygField(GlobalSettings.text_main_page.info["label"], validators=[validators.Optional()])
    submit = wtforms.SubmitField(_l("Save"))


class MainParameterForm(FlaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_language.choices = [(str(i[0]), str(i[1])) for i in db.session.execute(sa.select(ApplicationLanguage.id, ApplicationLanguage.title)).all()]
    default_language = wtforms.SelectField(_l("%(field_name)s:", field_name=GlobalSettings.default_language.info['label']), validators=[validators.InputRequired()])
    m2m_join_symbol = wtforms.StringField(_l("%(field_name)s:", field_name=GlobalSettings.m2m_join_symbol.info['label']), validators=[validators.InputRequired(message=_l("This field is mandatory!")),
                                                                                                                                      validators.Length(min=0, max=GlobalSettings.m2m_join_symbol.type.length, message=_l('This field must not exceed %(length)s characters in length', length=GlobalSettings.m2m_join_symbol.type.length))])
    m2m_max_items = wtforms.IntegerField(_l("%(field_name)s:", field_name=GlobalSettings.m2m_max_items.info['label']), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    pagination_element_count_select2 = wtforms.IntegerField(_l("%(field_name)s:", field_name=GlobalSettings.pagination_element_count_select2.info['label']), description=GlobalSettings.pagination_element_count_select2.info["help_text"], validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    submit = wtforms.SubmitField(_l("Save"))