from app import db, side_libraries, sanitizer, logger
from typing import Dict, Any, Tuple, List, Optional
from flask import g
from flask_socketio import rooms
from .general_helpers import utcnow
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.session import Session
import functools
import sqlalchemy as sa
import sqlalchemy.exc as exc
import app.models as models
import wtforms
from flask_babel import lazy_gettext as _l
from flask_login import current_user
from flask_babel import force_locale, gettext, pgettext


class EnvironmentObjectAttrs:
    def __init__(self, name: str, sidebar_function, environment_function):
        self.name = name
        self.sidebar_function = sidebar_function
        self.environment_function = environment_function
    
    def sidebar(self, current_object: Any, action: str, **kwargs):
        return self.sidebar_function(current_object, action, **kwargs)
    
    def environment(self, current_object: Any, action: str, **kwargs) -> Dict[str, Any]:
        return self.environment_function(current_object, action, **kwargs)
    
    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        elif not isinstance(other, EnvironmentObjectAttrs):
            return False
        return self.name == other.name
    
    def __repr__(self):
        return f"EnvironmentObjectAttrs for <{self.name}>"


environment_elements = []
environment_elements_register = []

def register_environment(element: EnvironmentObjectAttrs, after: str | None):
    global environment_elements, environment_elements_register
    environment_elements_register.append((element, after))
    if after is None:
        environment_elements.insert(0, element)
    changed = True
    while changed:
        changed = False
        for e in environment_elements_register:
            if e[1] in environment_elements and e[0] not in environment_elements:
                environment_elements.insert(environment_elements.index(e[1]) + 1, e[0])
                changed = True


def check_if_same_type(object_class):
    # A decorator for environmental objects is needed to simplify writing code
    def decorated(func):
        @functools.wraps(func)
        def wrapped(current_object, action, **kwargs):
            if isinstance(current_object, object_class):
                return func(current_object, action, **kwargs)
            return {}
        return wrapped
    return decorated


def get_default_environment(current_object, action: str, **kwargs):
    global environment_elements
    context = {"sidebar_data": []}
    for i in environment_elements:
        s = i.sidebar(current_object, action, **kwargs)
        if isinstance(s, list):
            context["sidebar_data"].extend(s)
        elif s is not None:
            context["sidebar_data"].append(s)
        context.update(i.environment(current_object, action, **kwargs))
    return context


def get_current_room() -> Optional[Tuple[int, str]]:
    ''' Try to get current room, to which connect client (default room number is object id) and returned it (as int(current_room), current_room)
     Otherwise returned None '''
    try:
        # Trying to get current_room (object_id)
        current_room = int(rooms()[0])
        current_room_name = rooms()[0]
    except (ValueError, TypeError): # it means that this is a room, assigned by SocketIO-server
        try:
            current_room = int(rooms()[1])
            current_room_name = rooms()[1]
        except (ValueError, TypeError, IndexError): # We don't know what a room is it. Exit
            logger.error(f"Something went wrong. All clients room: {rooms()}")
            return None
    return (current_room, current_room_name)


def create_history(session: Session, object_elements: List[Any]) -> None:
    ''' Created history element for all objects in input that has attribute 'history' (gain all changes for object from session and create element).
     Also filled field 'updated_at' if it exist '''
    for obj in object_elements:
        if obj.id is None:
            continue
        object_class = obj.__class__
        history_class = inspect(obj.__class__).relationships['history'].entity.class_
        columns = [(i.columns[0].name, i.columns[0].info['label']) for i in inspect(object_class).column_attrs]
        relationships = [(i.key, i.info['label']) for i in inspect(object_class).relationships if not i.uselist]
        list_m2m_relationships = [i for i in inspect(object_class).relationships if i.uselist and i.key not in ['comments', 'history']]
        attrs = inspect(obj).attrs
        changes = {"changes": []} # {"action": "action_type: add_paramether, modify_paramether, delete_paramether", "attrs": {**kwargs("lazy_name": "paramether_name", "old_value": old_value, "new_value": new_value)}}
        changed = False
        relationships_already_added = []
        with force_locale('en'): # all param names only in default locale
            for attr_name, attr_label in columns: # added simple_attrs to history
                if len(attrs[attr_name].history.added) != 0 and not attr_name.startswith("updated_by"):
                    changed = True
                    if not attr_name.endswith("_id"):
                        if len(attrs[attr_name].history.deleted) == 0:
                            old_value = ''
                        else:
                            old_value = attrs[attr_name].history.deleted[0]
                        if isinstance(old_value, str):
                            old_value = sanitizer.sanitize(old_value)
                        new_value = attrs[attr_name].history.added[0]
                        if isinstance(new_value, str):
                            new_value = sanitizer.sanitize(new_value)
                        changes["changes"].append({"action": "modify_paramether", "attrs": {'lazy_name': str(attr_label), "old_value": str(old_value),
                                                                                            "new_value": str(new_value)}})
                    else:
                        an = attr_name[:len(attr_name) - 3:]
                        attr_cls = inspect(obj.__class__).relationships[an].entity.class_
                        old_id = attrs[attr_name].history.deleted[0]
                        if old_id is None:
                            old_id = 0
                        old_val = db.session.get(attr_cls, old_id)
                        new_id = attrs[attr_name].history.added[0]
                        if new_id is None:
                            new_id = 0
                        new_val = db.session.get(attr_cls, new_id)
                        if old_val and new_val:
                            changes['changes'].append({"action": "modify_paramether", "attrs": {'lazy_name': str(attr_label), "old_value": old_val.title, "new_value": new_val.title}})
                        elif old_val:
                            changes['changes'].append({"action": "delete_paramether", "attrs": {'lazy_name': str(attr_label), 'old_value': old_val.title}})
                        elif new_val:
                            changes['changes'].append({"action": 'add_paramether', "attrs": {'lazy_name': str(attr_label), 'new_value': new_val.title}})
                        relationships_already_added.append(an)
            # Added simple elements relationships (no uselist) to history:
            for attr_name, attr_label in relationships: 
                if attr_name in relationships_already_added:
                    # they was being added in simple_attrs via '_id' syntax
                    continue
                old_val = attrs[attr_name].history.deleted
                new_val = attrs[attr_name].history.added
                if old_val and new_val:
                    changes['changes'].append({"action": "modify_paramether", "attrs": {'lazy_name': str(attr_label), "old_value": old_val[0].title, "new_value": new_val[0].title}})
                    changed = True
                elif old_val:
                    changes['changes'].append({"action": "delete_paramether", "attrs": {'lazy_name': str(attr_label), 'old_value': old_val[0].title}})
                    changed = True
                elif new_val:
                    changes['changes'].append({"action": 'add_paramether', "attrs": {'lazy_name': str(attr_label), 'new_value': new_val[0].title}})
                    changed = True
            # Updating Many-To-Many Relationships:
            for rel_obj_class in list_m2m_relationships:
                getattr(obj, rel_obj_class.key)
                for related_obj in list(attrs[rel_obj_class.key].history.added) + list(attrs[rel_obj_class.key].history.deleted):
                    # touch related objects to update him
                    if hasattr(related_obj, 'history'):
                        if rel_obj_class.back_populates != '' and rel_obj_class.back_populates is not None:
                            getattr(related_obj, rel_obj_class.back_populates)
                        elif isinstance(rel_obj_class.backref, str):
                            # if backref is setted as string
                            getattr(related_obj, related_obj.backref)
                        else:
                            # Now I don't know what hapenned if backref is setted as so.backref. Doing it later
                            pass
                        if related_obj not in object_elements and related_obj.id is not None: # add related objects to check if they have a changes, and if they have - add to list
                            object_elements.append(related_obj) # None - if it is not a currently created object
                # Setting title of object for history:
                if hasattr(rel_obj_class.entity.class_, 'fulltitle'):
                    title_attr_name = 'fulltitle'
                else:
                    title_attr_name = 'title'
                # values for added params
                new_values = [x.id for x in attrs[rel_obj_class.key].history.added]
                if len(new_values) != 0:
                    changed = True
                    changes['changes'].append({"action": 'add_m2m_paramether',
                                               "attrs": {'lazy_name': str(rel_obj_class.info['label']), 'title_attr': title_attr_name,
                                                         'new_value': new_values, 'values_class': attrs[rel_obj_class.key].history.added[0].__class__.__name__}})
                removed_values = [x.id for x in attrs[rel_obj_class.key].history.deleted]
                # values for removed params
                if len(removed_values) != 0:
                    changed = True
                    changes['changes'].append({"action": 'delete_m2m_paramether',
                                               "attrs": {'lazy_name': str(rel_obj_class.info['label']), 'title_attr': title_attr_name,
                                                         'old_value': removed_values, 'values_class': attrs[rel_obj_class.key].history.deleted[0].__class__.__name__}})
        if changed:
            # Check if changed is exist
            if current_user != None and not current_user.is_anonymous:
                created_by_id = current_user.id
            elif len(attrs["updated_by_id"].history.added) != 0:
                created_by_id = attrs["updated_by_id"].history.added[0]
            elif len(attrs["updated_by"].history.added) != 0:
                created_by_id = attrs["updated_by"].history.added[0].id
            elif len(attrs["updated_by_id"].history.unchanged) != 0:
                created_by_id = attrs["updated_by_id"].history.unchanged[0]
            else:
                created_by_id = created_by_id=attrs["updated_by"].history.unchanged[0].id
            pts = history_class(changes=changes, created_by_id=created_by_id)
            obj.history.append(pts)
            session.add(pts)
            if hasattr(obj, 'updated_at'):
                obj.update_at = utcnow()


def validate_service(project_id, field) -> None:
    try:
        if not db.session.scalars(sa.select(sa.func.count(models.Service.id)).join(models.Service.host).join(models.Host.from_network)
                           .where(sa.and_(models.Network.project_id == project_id, models.Service.id.in_([field.coerce(i) for i in field.data])))).one() == len(field.data):
            raise wtforms.ValidationError(_l("Not a valid choice."))
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        raise wtforms.ValidationError(_l("Not a valid choice."))


def validate_host(project_id, field) -> None:
    try:
        if not db.session.scalars(sa.select(sa.func.count(models.Host.id)).join(models.Host.from_network)
                           .where(sa.and_(models.Network.project_id == project_id, models.Host.id.in_([field.coerce(i) for i in field.data])))).one() == len(field.data):
            raise wtforms.ValidationError(_l("Not a valid choice."))
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        raise wtforms.ValidationError(_l("Not a valid choice."))


def load_comment_script(comment_form, object_with_comments) -> str:
    ''' Added a script to edit coments via websocket to side_libraries scripts '''
    script = '''
    const addCommentModal = document.getElementById('addCommentModal')
      if (addCommentModal) {
        addCommentModal.addEventListener('show.bs.modal', event => {
        const recipient = event.relatedTarget.getAttribute('data-comment-id')
        if (recipient !== null) {
          const modalTitle = addCommentModal.querySelector('.modal-title')
          const modalBodyInput = document.getElementById("''' + str(comment_form.reply_to_id.id) + '''")
              
          modalTitle.textContent = `''' + gettext("Reply to comment") + '''`
          modalBodyInput.value = recipient
        }
      })
    }
    let generic_websocket_defined = typeof(generic_websocket) === 'undefined';
    var generic_websocket = generic_websocket || io('/generic');
    if(generic_websocket_defined) {
      generic_websocket.on('connect', function() {
        generic_websocket.emit('join_room', "''' + object_with_comments.__class__.__name__  + ':' + str(object_with_comments.id)  + '''");
      });
    };
    document.getElementById("''' + str(comment_form.submit.id) + '''").addEventListener('click', function(event) {
      let reply_to_id = document.getElementById("''' + str(comment_form.reply_to_id.id) + '''").value;
      let text = CKEDITOR_LIST["''' + str(comment_form.text.id) + '''"].getData();
      generic_websocket.emit('add comment', {'reply_to_id': reply_to_id, 'text': text});
      CKEDITOR_LIST["''' + str(comment_form.text.id) + '''"].setData('');
      document.getElementById("''' + str(comment_form.reply_to_id.id)  + '''").value = '';
      // close modal window
      let modal_add_note = bootstrap.Modal.getInstance(document.getElementById('addCommentModal'))
      modal_add_note.hide()
      
    })
    function reaction_high_event_listener(event) {
      event.preventDefault();
      let comment_id = event.target.parentElement.getAttribute('data-comment-id');
      generic_websocket.emit('add reaction', {'comment_id': comment_id, 'is_positive': 1});
    }
    function reaction_low_event_listener(event) {
      event.preventDefault();
      let comment_id = event.target.parentElement.getAttribute('data-comment-id');
      generic_websocket.emit('add reaction', {'comment_id': comment_id, 'is_positive': 0});
    }
    // Event listeners for reactions
    for(const el of document.getElementsByClassName('comment-reaction-high')) {
      el.addEventListener('click', reaction_high_event_listener);
    }
    for(const el of document.getElementsByClassName('comment-reaction-low')) {
      el.addEventListener('click', reaction_low_event_listener);
    }
    // Action when comment added
    generic_websocket.on('comment added', data => {
      let comment_div = document.createElement('div');
      comment_div.setAttribute('class', 'comment')
      comment_div.setAttribute('id', 'comment-' + data.comment_id)
      let inner_div_1 = document.createElement('div');
      comment_div.appendChild(inner_div_1);
      inner_div_1.setAttribute('class', 'd-flex flex-start align-items-center')
      let img_ava = document.createElement('img');
      setMultipleAttributes(img_ava, {'class': 'rounded-circle shadow-1-strong me-3', 'src': data.created_by_ava, 'alt': 'Avatar', 'width': '60', 'height': '60'});
      inner_div_1.appendChild(img_ava);
      let div_media_body = document.createElement('div');
      div_media_body.setAttribute('class', 'media-body');
      inner_div_1.appendChild(div_media_body);
      let h5_user = document.createElement('h5');
      div_media_body.appendChild(h5_user);
      h5_user.setAttribute('class', 'mt-0 media-heading')
      h5_user.innerHTML = data.created_by;
      let p_user = document.createElement('p');
      div_media_body.appendChild(p_user);
      p_user.setAttribute('class', 'text-muted small mb-0');
      p_user.innerHTML = data.created_by_position;
      let text_div = document.createElement('div')
      comment_div.appendChild(text_div);
      text_div.setAttribute('class', 'mt-3 mb-4 pb-2');
      text_div.innerHTML = data.text;
      let comment_footer_div = document.createElement('div');
      comment_div.appendChild(comment_footer_div);
      comment_footer_div.setAttribute('class', 'comments-footer clearfix');
      let inner_ul = document.createElement('ul');
      inner_ul.classList.add('main-list-ul');
      comment_footer_div.appendChild(inner_ul);
      let li_1 = document.createElement('li');
      inner_ul.appendChild(li_1);
      li_1.innerHTML = `<a href="#" class="comment-reaction-high high" data-comment-id="${data.comment_id}" id="positive-reaction-for-comment-${data.comment_id}"><span class="count">0</span><i class="fa-regular fa-thumbs-up"></i></a>`;
      li_1.addEventListener('click', reaction_high_event_listener);
      let li_2 = document.createElement('li');
      inner_ul.appendChild(li_2);
      li_2.innerHTML = `<a href="#" class="comment-reaction-low low" data-comment-id="${data.comment_id}" id="negative-reaction-for-comment-${data.comment_id}"><span class="count">0</span><i class="fa-regular fa-thumbs-down"></i></a>`;
      li_2.addEventListener('click', reaction_low_event_listener);
      let li_3 = document.createElement('li');
      inner_ul.appendChild(li_3);
      li_3.innerHTML = `<a href="#addCommentModal" data-bs-toggle="modal" data-comment-id="${data.comment_id}">Ответить</a>`;
      let media_div = document.createElement('div');
      media_div.appendChild(comment_div);
      media_div.setAttribute('class', 'media created');
      let comment_list = document.getElementById('comment-list');
      if(comment_list.innerHTML.trim() === '<p class="text-center text-muted">''' +  pgettext("they", "(Missing)") + '''</p>') {
        comment_list.innerHTML = '';
      };
      if(data.reply_to_id !== null) {
        let comment_media_div = document.getElementById('comment-media-' + data.reply_to_id)
        if(comment_media_div !== null) {
          if("''' + str(current_user.environment_setting.comment_order_asc) + '''" === 'True') {
            comment_media_div.appendChild(media_div);
            let hr = document.createElement('hr');
            media_div.insertAdjacentElement('afterend', hr);
          }
          else {
            comment_media_div.insertAdjacentElement('afterbegin', media_div);
            let hr = document.createElement('hr');
            comment_media_div.insertAdjacentElement('beforebegin', hr);
          }
        }
        else {
          let outer_media_div = document.createElement('div')
          setMultipleAttributes(outer_media_div, {'class': 'media', 'style': 'padding-left:''' + str(current_user.environment_setting.comment_reply_padding) + '''px;', 'id': 'comment-media-' + data.reply_to_id})
          outer_media_div.appendChild(media_div);
          let comment_to_reply = document.getElementById('comment-' + data.reply_to_id);
          comment_to_reply.insertAdjacentElement('afterend', outer_media_div);
          let hr = document.createElement('hr');
          outer_media_div.insertAdjacentElement('beforebegin', hr);
        }
      }
      else {
        if("''' + str(current_user.environment_setting.comment_order_asc) + '''" === 'True') {
          comment_list.appendChild(media_div);
          let hr = document.createElement('hr');
          comment_list.appendChild(hr);
        }
        else {
          comment_list.insertAdjacentElement('afterbegin', media_div);
          let hr = document.createElement('hr');
          media_div.insertAdjacentElement('afterend', hr);
        }
      }

      // render all moment units
      flask_moment_render_all();
    });
    generic_websocket.on('reaction added', data => {
      var current_user_id = Number("''' + str(current_user.id) + '''");
      var positive_reaction = document.getElementById('positive-reaction-for-comment-' + data.to_comment);
      var negative_reaction = document.getElementById('negative-reaction-for-comment-' + data.to_comment);
      if(data.added_by_id != current_user_id) {
        positive_reaction.children[0].innerHTML = data.positive_count;
        negative_reaction.children[0].innerHTML = data.negative_count;
      }
      else {
        if(data.is_positive === true) {
          positive_reaction.innerHTML = `<span class="count">${data.positive_count}</span><i class="fa-solid fa-thumbs-up"></i>`;
          negative_reaction.innerHTML = `<span class="count">${data.negative_count}</span><i class="fa-regular fa-thumbs-down"></i>`;
        }
        else if(data.is_positive === false) {
          positive_reaction.innerHTML = `<span class="count">${data.positive_count}</span><i class="fa-regular fa-thumbs-up"></i>`;
          negative_reaction.innerHTML = `<span class="count">${data.negative_count}</span><i class="fa-solid fa-thumbs-down"></i>`;
        }
        else {
          positive_reaction.innerHTML = `<span class="count">${data.positive_count}</span><i class="fa-regular fa-thumbs-up"></i>`;
          negative_reaction.innerHTML = `<span class="count">${data.negative_count}</span><i class="fa-regular fa-thumbs-down"></i>`;
        }
      }
    })
    '''
    side_libraries.require_script(script)
    return ''


def load_history_script(object_with_history) -> str:
    ''' load history websocket script to side_libraries '''
    script = '''
    let generic_ws_defined = typeof(generic_websocket) === 'undefined';
      var generic_websocket = generic_websocket || io('/generic');
      if(generic_ws_defined) {
        generic_websocket.on('connect', function() {
          generic_websocket.emit('join_room', "''' + object_with_history.__class__.__name__ + ':' + str(object_with_history.id) + '''");
        });
      };
      generic_websocket.on('history element added', function(data){
        generic_websocket.emit('get history', {'id': data.id, 'locale': "''' + str(g.locale) + '''"}, function(data) {
          let p_history_missing = document.getElementById('p-history-missing');
          if(p_history_missing !== null) {
            p_history_missing.remove()
          }
          let history_list = document.getElementById('div-history-list');
          let media = document.createElement('div');
          media.classList.add('media');
          media.classList.add('created');
          let div_header = document.createElement('div');
          media.appendChild(div_header);
          div_header.setAttribute('class', 'd-flex flex-start align-items-center');
          let img = document.createElement('img');
          setMultipleAttributes(img, {src: data.created_by_avatar, class: 'rounded-circle shadow-1-strong me-3', alt: 'avatar', width: 60, height: 60});
          div_header.appendChild(img);
          let div_media_body = document.createElement('div');
          div_header.appendChild(div_media_body);
          div_media_body.classList.add('media-body');
          let h5_media_body = document.createElement('h5');
          div_media_body.appendChild(h5_media_body);
          h5_media_body.setAttribute('class', 'mt-0 media-heading');
          let a_user = document.createElement('a');
          h5_media_body.appendChild(a_user);
          a_user.setAttribute('href', data.created_by_href);
          a_user.innerHTML = data.created_by_title;
          let created_date = document.createElement('span');
          h5_media_body.appendChild(created_date);
          created_date.classList.add('date');
          created_date.innerHTML = data.created_at;
          let p_position = document.createElement('p');
          div_media_body.appendChild(p_position);
          p_position.setAttribute('class', 'text-muted small mb-0');
          p_position.innerHTML = data.created_by_position;
          let div_body = document.createElement('div');
          div_body.setAttribute('class', 'mt-3 mb-4 pb-2');
          media.appendChild(div_body);
          div_body.innerHTML = data.history_text;
          if("''' + str(current_user.environment_setting.comment_order_asc) + '''" === 'True') {
            history_list.appendChild(media);
            let hr = document.createElement('hr');
            history_list.appendChild(hr);
          }
          else {
            history_list.insertAdjacentElement('afterbegin', media);
            let hr = document.createElement('hr');
            history_list.insertAdjacentElement('afterend', hr);
          };
          flask_moment_render_all();
        });
      });
    '''
    side_libraries.require_script(script)
    return ''