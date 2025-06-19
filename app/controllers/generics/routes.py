from app.controllers.generics import bp
from app import db, logger
import sqlalchemy as sa
from flask import request, abort, jsonify, current_app, make_response
from flask_login import current_user, login_required
from app.helpers.admin_helpers import get_enumerated_objects
import importlib


@bp.route('/enumeration_objects/<object_class>/list')
@login_required
def enumeration_object_list(object_class):
    modules = importlib.import_module('app.models')
    try:
        page = int(request.args.get('page'))
    except (TypeError):
        page = 1
    except ValueError:
        abort(400)
    try:
        cls = getattr(modules, object_class)
    except AttributeError:
        abort(404)
    query = request.args.get('term') if request.args.get('term') else ''
    eo = get_enumerated_objects()
    if cls not in eo:
        abort(404)
    data = db.session.execute(sa.select(cls.id, cls.title).where(cls.title.ilike('%' + query + '%')).limit(current_app.config["GlobalSettings"].pagination_element_count_select2 + 1)
                              .offset((page - 1) * current_app.config["GlobalSettings"].pagination_element_count_select2)).all()
    more = len(data) == current_app.config["GlobalSettings"].pagination_element_count_select2 + 1
    if more:
        result = {'results': [{'id': i[0], 'text': i[1]} for i in data[:len(data) - 1:]], 'pagination': {'more': True}}
    else:
        result = {'results': [{'id': i[0], 'text': i[1]} for i in data], 'pagination': {'more': False}}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request to get enumerated object list '{object_class}'")
    return jsonify(result)


@bp.route('/get_current_theme_style')
def get_current_user_theme_style():
    ''' Returned an application style, in which the page been painted '''
    archived = request.args.get('archived')
    if not current_user.is_anonymous and current_user.theme_style is not None:
        css_content = ':root {'
        if archived == '' or archived is None or archived == 'False':
            css_content += f"""--main-color: { current_user.theme_style.main_color };
					--neightboring-main-color: { current_user.theme_style.neightboring_main_color };
					--secondary-main-color: { current_user.theme_style.secondary_main_color };
					--main-text-color: { current_user.theme_style.main_text_color };"""
            
        else:
            css_content += f"""--main-color: { current_user.theme_style.archived_main_color };
					--neightboring-main-color: { current_user.theme_style.archived_neightboring_main_color };
					--secondary-main-color: { current_user.theme_style.archived_secondary_main_color };
					--main-text-color: { current_user.theme_style.archived_main_text_color };"""
        css_content += f"""
                    --hovering-main-element-color: { current_user.theme_style.hovering_main_element_color };
					--sidebar-background-color: { current_user.theme_style.sidebar_background_color };
					--main-content-background-color: { current_user.theme_style.main_content_background_color };
					--color-card-background-header: { current_user.theme_style.color_card_background_header };
					--color-chats-hour: { current_user.theme_style.color_chats_hour };
					--color-chats-my-message: { current_user.theme_style.color_chats_my_message };
					--color-chats-my-message-text: { current_user.theme_style.color_chats_my_message_text };
					--color-chats-other-message: { current_user.theme_style.color_chats_other_message };
					--color-chats-other-message-text: { current_user.theme_style.color_chats_other_message_text };
					--bs-card-color: { current_user.theme_style.bs_card_color };
					--dark-color: { current_user.theme_style.dark_color };
					--timeline-time-color: { current_user.theme_style.timeline_time_color };
					--timeline-line-color: { current_user.theme_style.timeline_line_color };
					--timeline-red-team-background-color: { current_user.theme_style.timeline_red_team_background_color };
					--timeline-red-team-text-color: { current_user.theme_style.timeline_red_team_text_color };
					--timeline-blue-team-background-color: { current_user.theme_style.timeline_blue_team_background_color };
					--timeline-blue-team-text-color: { current_user.theme_style.timeline_blue_team_text_color };"""
        css_content += "}"
    else:
        css_content = ':root {'
        if archived == '' or archived is None or archived == 'False':
            css_content += """--main-color: #0a7700;
					--neightboring-main-color: #167000;
					--secondary-main-color: #7d7d7d;
					--main-text-color: #ffffff;"""
        else:
            css_content += f"""--main-color: #a3a3a3;
					--neightboring-main-color: #ccb6b6;
					--secondary-main-color: #65ab53;
					--main-text-color: #000000;"""
        css_content += """
                    --hovering-main-element-color: #1fb7dd;
					--sidebar-background-color: #2b394c;
					--main-content-background-color: #e6ecf3;
					--color-card-background-header: #f0f4f9;
					--color-chats-hour: #004715;
					--color-chats-my-message: #89ff99;
					--color-chats-my-message-text: #000000;
					--color-chats-other-message: #e6ecf3;
					--color-chats-other-message-text: #000000;
					--bs-card-color: #000000;
					--dark-color: #777;
					--timeline-time-color: #8796af;
					--timeline-line-color: #000;
					--timeline-red-team-background-color: rgb(138, 2, 2);
					--timeline-red-team-text-color: #fff;
					--timeline-blue-team-background-color: rgb(0, 0, 138);
					--timeline-blue-team-text-color: #fff;"""
        css_content += "}"
    response = make_response(css_content)
    response.headers['Content-Type'] = 'text/css'
    return response

@bp.route('/get_ckeditor_styles')
def get_ckeditor_styles():
    ''' Returned an CKEditor5 styles '''
    height = request.args.get('height')
    if height is None or height == '':
        styles = '''.ck-editor__editable_inline {
				min-height: 400px;
			}'''
    else:
        styles = f'''.ck-editor__editable_inline {{
				min-height: { height };
			}}'''
    response = make_response(styles)
    response.headers['Content-Type'] = 'text/css'
    return response