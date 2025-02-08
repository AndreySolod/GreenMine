import wtforms
import wtforms.validators as validators
from wtforms import fields
from app.controllers.forms import FlaskForm, WysiwygField
from app.helpers.projects_helpers import load_comment_script
from app.models import Comment
from flask_babel import lazy_gettext as _l


class CommentForm(FlaskForm):
    text = WysiwygField(_l("%(field_name)s:", field_name=Comment.text.info["label"]), validators=[validators.DataRequired()], id="comment-create-text")
    reply_to_id = fields.IntegerField(_l("%(field_name)s:", field_name=Comment.reply_to_id.info["label"]), validators=[validators.Optional()], id="comment-create-reply-to-id")
    submit = wtforms.SubmitField(_l("Create"), id="comment-create-submit")
    load_comment_script = load_comment_script


class CommentEditForm(FlaskForm):
    text = WysiwygField(_l("%(field_name)s:", field_name=Comment.text.info["label"]), validators=[validators.DataRequired()], id="comment-edit-text")
    submit = wtforms.SubmitField(_l("Save"), id="comment-edit-submit")
    load_comment_script = load_comment_script


