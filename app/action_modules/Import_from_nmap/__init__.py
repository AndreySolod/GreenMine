from app import db
from app.action_modules.classes import ActionModule
import app.models as models
import sqlalchemy as sa
import sqlalchemy.orm as so
from typing import Optional, List
from app.controllers.forms import FlaskForm, Select2Field, Select2IconMultipleField, WysiwygField
import wtforms
import wtforms.validators as validators
import flask_wtf.file as wtfile
from flask_babel import lazy_gettext as _l
from flask import url_for, g
from app.helpers.projects_helpers import validate_host
import logging
from app.action_modules.NmapScan.classes import NmapScanner
logger = logging.getLogger("Import from nmap")


def action_run(nmap_file_data: str, project_id: int, current_user_id: int,
               ignore_closed_ports: bool=True, ignore_host_without_open_ports_and_arp_response: bool=True,
               add_host_with_only_arp_response: bool=True, process_operation_system: bool=True,
               scanning_host_id: Optional[int]=None, add_network_mutial_visibility: bool=True,
               add_host_and_service_mutual_visibility: bool=False, created_host_mark: Optional[List[int]]=None,
               edited_host_mark: Optional[List[int]]=None, added_comment: str="",
               session=db.session, locale: str='en'):
    scanner = NmapScanner(init_scanner=False)
    scanner.parse_and_update_database(nmap_file_data, project_id, current_user_id, session, ignore_closed_ports,
                                      ignore_host_without_open_ports_and_arp_response, add_host_with_only_arp_response, process_operation_system,
                                      scanning_host_id, add_network_mutial_visibility, add_host_and_service_mutual_visibility,
                                      created_host_mark, edited_host_mark, added_comment, locale)
    return None


def exploit(filled_form: dict, running_user: int, default_options: dict, locale: str, project_id: int) -> None:
    with so.sessionmaker(bind=db.engine)() as session:
        action_run(filled_form['nmap_file'], int(filled_form["project_id"]), running_user, filled_form["ignore_closed_ports"],
                   filled_form["ignore_host_without_open_ports_and_arp_response"],
                   filled_form["add_host_with_only_arp_response"], filled_form["process_operation_system"],
                   filled_form["scanning_host"], filled_form["add_network_accessible"], filled_form["add_host_to_service_accessible"],
                   filled_form["created_host_marks"], filled_form["edited_host_marks"], filled_form["added_comment"],
                   session=session, locale=locale)


class AdminOptionsForm(FlaskForm):
    pass


class ModuleInitForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_id.data = project_id
        self.scanning_host.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(sa.and_(models.Network.project_id==project_id, models.Host.excluded == False)))]
        self.scanning_host.callback = url_for('networks.get_select2_host_data', project_id=project_id, with_excluded='1')
        self.scanning_host.locale = g.locale
        self.scanning_host.validate_funcs = lambda x: validate_host(project_id, x)
        self.created_host_marks.choices = [(i.id, i) for i in db.session.scalars(sa.select(models.HostLabel))]
        self.edited_host_marks.choices = [(i.id, i) for i in db.session.scalars(sa.select(models.HostLabel))]
    nmap_file = wtforms.FileField(_l("Nmap scan result file:"), validators=[wtfile.FileAllowed(['xml'], _l("Only an xml file!")), wtfile.FileRequired(message=_l("This field is mandatory!"))])
    ignore_closed_ports = wtforms.BooleanField(_l("Ignore ports that do not have the status <Open>:"), default=True)
    ignore_host_without_open_ports_and_arp_response = wtforms.BooleanField(_l("Ignore hosts without open ports and ARP response:"), default=True)
    add_host_with_only_arp_response = wtforms.BooleanField(_l("Add hosts for which an ARP response has been received and there are no open ports:"), default=True)
    process_operation_system = wtforms.BooleanField(_l("Process host operating system data:"), default=True)
    scanning_host = Select2Field(models.Host, label=_l("%(field_name)s:", field_name=_l("Scanning host")),
                                  description=_l("The host from which or through which the scan was performed. Affects the mutual visibility of hosts/services with the specified one."),
                                  validators=[validators.Optional()],
                                  attr_title="treeselecttitle")
    add_network_accessible = wtforms.BooleanField(_l("Automatically add mutual visibility of networks:"), default=True)
    add_host_to_service_accessible = wtforms.BooleanField(_l("Automatically add mutual visibility of hosts and service:"), default=False)
    created_host_marks = Select2IconMultipleField(models.HostLabel, _l("Labels for new hosts:"), validators=[validators.Optional()], attr_icon="icon_class", attr_color="icon_color")
    edited_host_marks = Select2IconMultipleField(models.HostLabel, _l("Label for edited hosts:"), description=_l("Add labels to hosts that have been changed"), validators=[validators.Optional()], attr_icon="icon_class", attr_color="icon_color")
    added_comment = WysiwygField(_l("Add description for all scanned host:"), validators=[validators.Optional()])
    project_id = wtforms.HiddenField(_l("Project ID:"), validators=[validators.InputRequired()])
    submit = wtforms.SubmitField(_l("Import"))


class ImportFromNmap(ActionModule):
    title = _l("Import from Nmap")
    description = _l("Imports the data of the scan results with the Nmap scanner")
    admin_form = AdminOptionsForm
    run_form = ModuleInitForm
    exploit_single_target = staticmethod(action_run)
    exploit = staticmethod(exploit)
    default_options = {}
