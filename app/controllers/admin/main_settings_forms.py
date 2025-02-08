from app.controllers.forms import FlaskForm
from app.models import GlobalSettings
import wtforms
import wtforms.validators as validators
from app.controllers.forms import WysiwygField
from flask_babel import lazy_gettext as _l


class MainPageNameForm(FlaskForm):
    main_page_name = wtforms.StringField(GlobalSettings.main_page_name.info["label"], validators=[validators.DataRequired(message=_l("This field is mandatory!")), validators.Length(max=GlobalSettings.main_page_name.type.length)])

class MainPageTextForm(FlaskForm):
    text_main_page = WysiwygField(GlobalSettings.text_main_page.info["label"], validators=[validators.Optional()])
    submit = wtforms.SubmitField(_l("Save"))
