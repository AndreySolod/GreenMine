import wtforms
import wtforms.validators as validators
from app import db
from app.controllers.forms import FlaskForm, WysiwygField, TreeSelectSingleField
from app.models import WikiDirectory, WikiPage
from flask_babel import lazy_gettext as _l


class WikiDirectoryForm(FlaskForm):
    def __init__(self, session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        query_1 = db.select(WikiDirectory).where(WikiDirectory.id.not_in(
            db.select(WikiDirectory.parent_directory_id)
            .distinct().where(WikiDirectory.parent_directory_id != None)))
        self.parent_directory_id.choices = [('0', '')] + [(str(i.id), i) for i in session.scalars(query_1)]
        self.parent_directory_id.disabledBranchNode = False
        self.parent_directory_id.is_same_type = True
    title = wtforms.StringField(_l("%(field_name)s:", field_name=WikiDirectory.title.info["label"]),
                                validators=[validators.InputRequired(message = _l("This field is mandatory!")),
                                            validators.Length(max=WikiDirectory.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=WikiDirectory.title.type.length))])
    description = wtforms.StringField(_l("%(field_name)s:", field_name=WikiDirectory.description.info["label"]),
                                      validators=[validators.Optional(),
                                                  validators.Length(max=WikiDirectory.description.type.length, message=_l('This field must not exceed %(length)s characters in length', length=WikiDirectory.description.type.length))])
    parent_directory_id = TreeSelectSingleField(_l("%(field_name)s:", field_name=WikiDirectory.parent_directory_id.info["label"]),
                                                validators=[validators.Optional()])


class WikiDirectoryNewForm(WikiDirectoryForm):
    submit = wtforms.SubmitField(_l("Create"))


class WikiDirectoryEditForm(WikiDirectoryForm):
    submit = wtforms.SubmitField(_l("Save"))


class WikiPageForm(FlaskForm):
    def __init__(self, session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.directory_id.choices = [('0', '')] + [(str(i.id), i) for i in session.scalars(db.select(WikiDirectory))]
    
    title = wtforms.StringField(_l("%(field_name)s:", field_name=WikiPage.title.info["label"]),
                                validators=[validators.InputRequired(message = _l("This field is mandatory!")),
                                            validators.Length(max=WikiPage.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=WikiPage.title.type.length))])
    description = wtforms.StringField(_l("%(field_name)s:", field_name=WikiPage.description.info["label"]), validators=[validators.Optional()])
    text = WysiwygField(_l("%(field_name)s:", field_name=WikiPage.text.info["label"]), validators=[validators.Optional()])
    directory_id = TreeSelectSingleField(_l("%(field_name)s:", field_name=WikiPage.directory_id.info["label"]), validators=[validators.Optional()])


class WikiPageNewForm(WikiPageForm):
    submit = wtforms.SubmitField(_l("Create"))


class WikiPageEditForm(WikiPageForm):
    submit = wtforms.SubmitField(_l("Save"))