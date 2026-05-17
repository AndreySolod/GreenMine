from app.controllers.forms import FlaskForm, PickrColorField
from flask_babel import lazy_gettext as _l
import wtforms
import wtforms.validators as validators
import app.models as models


class ThemeStyleForm(FlaskForm):
    string_slug = wtforms.StringField(_l("%(field_name)s:", field_name=models.UserThemeStyle.string_slug.info["label"]),
                                      validators=[validators.InputRequired(message=_l("This field is mandatory!")),
                                            validators.Length(max=models.UserThemeStyle.string_slug.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.UserThemeStyle.string_slug.type.length))])
    title = wtforms.StringField(_l("%(field_name)s:", field_name=models.UserThemeStyle.title.info["label"]),
                                validators=[validators.InputRequired(message=_l("This field is mandatory!")),
                                            validators.Length(max=models.UserThemeStyle.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.UserThemeStyle.title.type.length))])
    is_default = wtforms.BooleanField(_l("%(field_name)s:", field_name=models.UserThemeStyle.is_default.info["label"]),
                                      validators=[validators.Optional()])
    main_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.main_color.info["label"]),
                                  validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    neightboring_main_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.neightboring_main_color.info["label"]),
                                              validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    secondary_main_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.secondary_main_color.info["label"]),
                                            validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    main_text_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.main_text_color.info["label"]),
                                      validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    hovering_main_element_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.hovering_main_element_color.info["label"]),
                                                  validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    sidebar_background_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.sidebar_background_color.info["label"]),
                                                  validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    main_content_background_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.main_content_background_color.info["label"]),
                                                    validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    color_card_background_header = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.color_card_background_header.info["label"]),
                                                  validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    color_chats_hour = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.color_chats_hour.info["label"]),
                                      validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    color_chats_my_message = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.color_chats_my_message.info["label"]),
                                            validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    color_chats_my_message_text = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.color_chats_my_message_text.info["label"]),
                                                  validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    color_chats_other_message = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.color_chats_other_message.info["label"]),
                                              validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    color_chats_other_message_text = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.color_chats_other_message_text.info["label"]),
                                                    validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    bs_card_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.bs_card_color.info["label"]),
                                    validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    dark_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.dark_color.info["label"]),
                                  validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    timeline_time_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.timeline_time_color.info["label"]),
                                          validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    timeline_line_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.timeline_line_color.info["label"]),
                                          validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    timeline_red_team_background_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.timeline_red_team_background_color.info["label"]),
                                                          validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    timeline_red_team_text_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.timeline_red_team_text_color.info["label"]),
                                                    validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    timeline_blue_team_background_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.timeline_blue_team_background_color.info["label"]),
                                                          validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    timeline_blue_team_text_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.timeline_blue_team_text_color.info["label"]),
                                                      validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    fixed_sidebar = wtforms.BooleanField(_l("%(field_name)s:", field_name=models.UserThemeStyle.fixed_sidebar.info["label"]),
                                  validators=[validators.Optional()])
    sidebar_position_left = wtforms.BooleanField(_l("%(field_name)s:", field_name=models.UserThemeStyle.sidebar_position_left.info["label"]),
                                                  validators=[validators.Optional()])
    archived_main_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.archived_main_color.info["label"]),
                                          validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    archived_main_text_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.archived_main_text_color.info["label"]),
                                              validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    archived_secondary_main_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.archived_secondary_main_color.info["label"]),
                                                  validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    archived_neightboring_main_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.archived_neightboring_main_color.info["label"]),
                                                      validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    network_on_graph_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.network_on_graph_color.info["label"]),
                                              validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    normal_host_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.normal_host_color.info["label"]),
                                          validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    compromised_host_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.compromised_host_color.info["label"]),
                                             validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    service_on_graph_color = PickrColorField(_l("%(field_name)s:", field_name=models.UserThemeStyle.service_on_graph_color.info["label"]),
                                              validators=[validators.InputRequired(message=_l("This field is mandatory!"))])


class ThemeStyleCreateForm(ThemeStyleForm):
    submit = wtforms.SubmitField(_l("Create"))


class ThemeStyleEditForm(ThemeStyleForm):
    submit = wtforms.SubmitField(_l("Save"))