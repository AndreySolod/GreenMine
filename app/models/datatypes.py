import sqlalchemy as sa
import sqlalchemy.types as types
from sqlalchemy.dialects.postgresql.base import ischema_names
from sqlalchemy.ext.mutable import MutableDict
import ipaddress
import json

try:
    from sqlalchemy.dialects.postgresql import JSON
    has_postgres_json = True
except ImportError:
    class PostgresJSONType(sa.types.UserDefinedType):
        """
        Text search vector type for postgresql.
        """
        def get_col_spec(self):
            return 'json'

    ischema_names['json'] = PostgresJSONType
    has_postgres_json = False


class NetworkAddress(types.TypeDecorator):
    impl = types.String(50)
    cache_ok = True
    python_type = ipaddress.IPv4Network

    def __init__(self, max_length=50, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.impl = types.String(max_length)

    def process_bind_param(self, value, dialect):
        return str(value) if value else None

    def process_result_value(self, value, dialect):
        if value is None or value == '':
            return None
        return ipaddress.IPv4Network(value)

    def _coerce(self, value):
        return ipaddress.IPv4Network(value) if value else None

    def coercion_listener(self, target, value, oldvalue, initiator):
        return self._coerce(value)


class IPAddress(types.TypeDecorator):
    impl = types.String(20)
    cache_ok = True
    python_type = ipaddress.IPv4Address

    def __init__(self, max_length=20, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.impl = types.String(max_length)

    def process_bind_param(self, value, dialect):
        return str(value) if value else None

    def process_result_value(self, value, dialect):
        return ipaddress.IPv4Address(value) if value else None

    def _coerce(self, value):
        return ipaddress.IPv4Address(value) if value else None

    def coercion_listener(self, target, value, oldvalue, initiator):
        return self._coerce(value)


class ImmutableJSONType(types.TypeDecorator):
    """
    JSONType offers way of saving JSON data structures to database. On
    PostgreSQL the underlying implementation of this data type is 'json' while
    on other databases its simply 'text'.

    ::


        from sqlalchemy_utils import JSONType


        class Product(Base):
            __tablename__ = 'product'
            id = sa.Column(sa.Integer, autoincrement=True)
            name = sa.Column(sa.Unicode(50))
            details = sa.Column(JSONType)


        product = Product()
        product.details = {
            'color': 'red',
            'type': 'car',
            'max-speed': '400 mph'
        }
        session.commit()
    """
    impl = sa.UnicodeText
    hashable = False
    cache_ok = True
    python_type = dict

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            # Use the native JSON type.
            if has_postgres_json:
                return dialect.type_descriptor(JSON())
            else:
                return dialect.type_descriptor(PostgresJSONType())
        else:
            return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value, dialect):
        if dialect.name == 'postgresql' and has_postgres_json:
            return value
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if dialect.name == 'postgresql':
            return value
        if value is not None:
            value = json.loads(value)
        return value


def JSONType():
    return MutableDict.as_mutable(ImmutableJSONType) # https://docs.sqlalchemy.org/en/20/core/custom_types.html#marshal-json-strings


class LimitedLengthString(types.TypeDecorator):
    impl = types.String
    python_type = str
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return value[:self.impl.length]

    def copy(self, **kwargs):
        return LimitedLengthString(self.impl.length)