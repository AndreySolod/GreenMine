import wtforms
import wtforms.validators as validators
from app import db
from app.controllers.forms import FlaskForm, WysiwygField
from app.models import Note, NoteImportance
from flask_babel import lazy_gettext as _l


class NoteNewForm(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(NoteNewForm, self).__init__(*args, **kwargs)
        self.importance_id.choices = [(str(i[0]), str(i[1])) for i in db.session.execute(db.select(NoteImportance.id, NoteImportance.title)).all()]
    title = wtforms.StringField(_l("%(field_name)s:", field_name=Note.title.info["label"]), id='new-title',
                                validators=[validators.InputRequired(message=_l("This field is mandatory!")),
                                            validators.Length(max=Note.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=Note.title.type.length))])
    description = WysiwygField(_l("%(field_name)s:", field_name=Note.description.info["label"]), id='new-description')
    importance_id = wtforms.SelectField(_l("%(field_name)s:", field_name=Note.importance_id.info["label"]), id='new-importance-id')
    submit = wtforms.SubmitField(_l("Create"), id='new-submit')


class NoteEditForm(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(NoteEditForm, self).__init__(*args, **kwargs)
        self.importance_id.choices = [(str(i[0]), str(i[1])) for i in db.session.execute(db.select(NoteImportance.id, NoteImportance.title))]
    id = wtforms.HiddenField(validators=[validators.DataRequired()])
    title = wtforms.StringField(_l("%(field_name)s:", field_name=Note.title.info["label"]), id='edit-title',
                                validators=[validators.InputRequired(message=_l("This field is mandatory!")),
                                            validators.Length(max=Note.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=Note.title.type.length))])
    description = WysiwygField(_l("%(field_name)s:", field_name=Note.description.info["label"]), id='edit-description')
    importance_id = wtforms.SelectField(_l("%(field_name)s:", field_name=Note.importance_id.info["label"]), id='edit-importance')
    submit = wtforms.SubmitField(_l("Save"), id='edit-submit')
