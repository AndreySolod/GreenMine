from app import db, sanitizer
import app.models as models
from app.action_modules.classes import ActionModule
from typing import Dict, Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from app.controllers.forms import FlaskForm
import wtforms
import wtforms.validators as validators
from flask_wtf.file import FileAllowed
from flask_babel import lazy_gettext as _l
from flask import request
import ipaddress


def set_host_data(host: models.Host, element: Dict[str, str], session: so.Session) -> None:
    if 'title' in element:
        host.title = sanitizer.escape(element['title'])
    if 'description' in element:
        host.description += sanitizer.sanitize(element['description'])
    if 'mac' in element:
        host.mac = element['mac']
    session.add(host)


def create_host_if_not_exist(ipaddr: ipaddress.IPv4Address, project_id: int, session: so.Session, user_id: int) -> models.Host:
    host = session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(sa.and_(models.Host.ip_address == str(ipaddr), models.Network.project_id == project_id))).first()
    if host:
        return host
    network = get_network_by_host(ipaddr, project_id, session)
    if network is None:
        return None
    host_status_up = session.scalars(sa.select(models.HostStatus).where(models.HostStatus.string_slug == 'up')).first()
    host = models.Host(ip_address=ipaddr, state=host_status_up, from_network=network, created_by_id=user_id)
    session.add(host)
    session.commit()
    return host

def get_network_by_host(host_ip: ipaddress.IPv4Address, project_id: int, session: so.Session) -> Optional[models.Network]:
    ''' returns the network that the host belongs to '''
    project = session.get(models.Project, project_id)
    for network in project.networks:
        if host_ip in network.ip_address:
            return network
    return None


def exploit(filled_form: dict, running_user_id: int, default_options: dict, locale: str, project_id: int):
    with so.sessionmaker(db.engine)() as session:
        for e in filled_form['processed_host_data']:
            host = create_host_if_not_exist(ipaddress.IPv4Address(e['ip_address']), project_id, session, running_user_id)
            if host is None:
                continue
            set_host_data(host, e, session)
        session.commit()


class MassImportHostResultForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super(MassImportHostResultForm, self).__init__(*args, **kwargs)
    ip_position = wtforms.IntegerField(_l("IP address position:"), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    title_position = wtforms.IntegerField(_l("Title position:"), validators=[validators.Optional()])
    description_position = wtforms.IntegerField(_l("Description position:"), description=_l("Will be added to the end of the existing element"), validators=[validators.Optional()])
    mac_position = wtforms.IntegerField(_l("MAC address position:"), validators=[validators.Optional()])
    delimiter = wtforms.StringField(_l("Column delimither:"), default=",", validators=[validators.Optional()], description=_l("The symbol by which the rows will be divided into columns"))
    content_data = wtforms.TextAreaField(_l("Content:"), description=_l("Input content to add here (one host per line with attribute, separated by column delimither)"))
    file_data = wtforms.FileField(_l("File:"), description=_l("A file with host to add (one hostf per line, separated by column delimither)"), validators=[FileAllowed(set(["csv"]), message=_l("Only .csv file are allowed!")), validators.Optional()])
    submit = wtforms.SubmitField(_l("Add"))

    def validate_content_data(form, field):
        if not form.file_data.data.filename and not field.data:
            raise validators.ValidationError(_l("At least one of the two fields is required: 'Content' or 'File'!"))
    
    def validate_file_data(form, field):
        if not form.content_data.data and not field.data.filename:
            raise validators.ValidationError(_l("At least one of the two fields is required: 'Content' or 'File'!"))
        
    def validate_delimiter(form, field):
        if (form.file_data.data.filename != '' or form.content_data.data.strip() != ''):
            if not form.parse_result(field.data):
                raise validators.ValidationError(_l("Incorrect input delimiter - not enough columns to parse"))
        else:
            raise validators.ValidationError(_l("Incorrect input delimiter - not enough columns to parse"))
    
    def parse_result(self, delimiter: str) -> bool:
        if self.content_data.data:
            parse_data = self.content_data.data
        elif self.file_data.data:
            try:
                parse_data = request.files.get(self.file_data.name).read().decode('utf8')
            except Exception as e:
                return False
        parsed_attrs = []
        for line in parse_data.strip().split("\n"):
            try:
                line_data = line.split(self.delimiter.data)
                current_attr = {'ip_address': line_data[self.ip_position.data].strip()}
                if self.title_position.data != None:
                    current_attr['title'] = line_data[self.title_position.data].strip()
                if self.description_position.data != None:
                    current_attr['description'] = line_data[self.description_position.data].strip()
                if self.mac_position.data != None:
                    current_attr['mac'] = line_data[self.mac_position.data].strip()
            except (IndexError):
                return False
            parsed_attrs.append(current_attr)
        self.additional_form_attrs = {'processed_host_data': parsed_attrs}
        return True


class MultipleImportHosts(ActionModule):
    title = _l("Mass import a host data")
    description = _l("Creates or updates host from the transferred file, split according to the specified separator")
    admin_form = None
    run_form = MassImportHostResultForm
    exploit_single_target = None
    exploit = staticmethod(exploit)
    default_options = {}
    show_on_exploit_list = False