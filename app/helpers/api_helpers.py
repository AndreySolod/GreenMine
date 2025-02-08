from app import db
from sqlalchemy import inspect
from sqlalchemy.exc import NoResultFound
import datetime
from werkzeug.http import HTTP_STATUS_CODES
from flask import jsonify, current_app


class ConvertError(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = "Data conversion error"

    def __str__(self):
        return f"ConvertError, {self.message}"


def obj_to_json_dict(obj):
    cols = inspect(obj.__class__).column_attrs.keys()
    res = {}
    for col in cols:
        attr_name = obj.__class__.__name__ + "." + col
        if attr_name in current_app.config['REST_FORBIDDEN_ATTRIBUTES']:
            continue
        val = inspect(obj).attrs[col].value
        if val.__class__.__name__ == 'datetime':
            res[col] = val.timestamp()
        elif val.__class__.__name__ == 'date':
            res[col] = val.isoformat()
        elif val.__class__.__name__ == 'timedelta':
            res[col] = val.days * 24 * 60 * 60 + val.seconds
        else:
            res[col] = val
    rels_r = inspect(obj.__class__).relationships
    rels = rels_r.keys()
    for rel in rels:
        attr_name = obj.__class__.__name__ + "." + rel
        if attr_name in current_app.config['REST_FORBIDDEN_ATTRIBUTES']:
            continue
        if rels_r[rel].uselist:
            res[rel] = list(map(lambda x: x.id if x is not None else None, inspect(obj).attrs[rel].value))
    return res


def load_from_json(obj, json_dict, session):
    column_attrs = inspect(obj.__class__).column_attrs
    rels = inspect(obj.__class__).relationships
    for keys, values in json_dict.items():
        if keys in current_app.config['REST_FORBIDDEN_ATTRIBUTES']:
            continue
        if keys in column_attrs:
            cls_name = column_attrs[keys].columns[0].type.__class__.__name__
            if cls_name == 'Integer' and not keys == "id":
                try:
                    setattr(obj, keys, int(values))
                except ValueError:
                    raise ConvertError(f"The value of the {keys} parameter must be able to be cast to the Integer type")
            elif cls_name == "String":
                setattr(obj, keys, values)
            elif cls_name == "DateTime":
                # In this case, the rule is that the date and time are transmitted in UTC format.
                # The UTC Timestamp format (nt.timestamp()) is used for transmission
                try:
                    setattr(obj, keys, datetime.datetime.fromtimestamp(float(values), datetime.timezone.utc))
                except (ValueError, TypeError):
                    raise ConvertError(f"The value of the {keys} parameter must be a Posix Timestamp")
            elif cls_name == 'Date':
                # In this case, the rule is that the date is transmitted in ISO format:
                try:
                    setattr(obj, keys, datetime.date.fromisoformat(values))
                except TypeError:
                    raise ConvertError(f"The value of the {keys} parameter should be interpreted as ISOformat")
            elif cls_name == "Interval":
                # In this case, the rule is seconds are passed
                try:
                    if values is None:
                        setattr(obj, keys, None)
                    else:
                        setattr(obj, keys, datetime.timedelta(seconds=int(values)))
                except (TypeError, ValueError):
                    raise ConvertError(f"The value of the {keys} parameter should be interpreted as a positive number of seconds")
        elif keys in rels:
            # First, we try to interpret the value as an id:
            try:
                c = rels[keys].entity.class_
                res = session.scalars(db.select(c).where(c.id == int(values))).one()
                setattr(obj, keys + "_id", res.id)
                continue
            except (ValueError, NoResultFound):
                pass
            # Now you need to try to interpret the value as string_slug:
            try:
                c = rels[keys].entity.class_
                res = session.scalars(db.select(c).where(c.string_slug == values)).one()
                setattr(obj, keys + "_id", res.id)
                continue
            except (NoResultFound, AttributeError):
                pass
            # In this case, you need to try to find this object by interpreting the value as title:
            try:
                c = rels[keys].entity.class_
                res = session.scalars(db.select(c).where(c.title == values)).one()
                setattr(obj, keys + "_id", res.id)
                continue
            except NoResultFound: 
                raise ConvertError(f"Parameter <{keys}> cannot be interpreted as an id, string_slug, or title for an object <{rels[keys].entity.class_.Meta.verbose_name}>")
        elif keys.startswith("_function__"):
            # In this case, a method is passed that should be called from this class
            try:
                getattr(obj, keys[11::])(values)
            except AttributeError:
                raise ConvertError(f"The method <{keys[11::]}> for an object <{obj.Meta.verbose_name}> does not exist")
            except Exception as e:
                raise e
        else:
            raise ConvertError(f"Parameter <{keys}> not defined for an object of type <{obj.__class__.Meta.verbose_name}>")


def error_response(status_code, message=None):
    payload = {'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
    if message:
        payload['message'] = message
    response = jsonify(payload)
    response.status_code = status_code
    return response
