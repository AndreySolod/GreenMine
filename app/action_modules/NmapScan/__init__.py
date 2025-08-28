from app import db
from app.controllers.forms import FlaskForm, Select2Field, TreeSelectMultipleField, WysiwygField, Select2IconMultipleField
from app.helpers.projects_helpers import validate_host
from flask import url_for, g
from flask_babel import lazy_gettext as _l
from app.action_modules.classes import ActionModule
from typing import List, Optional
import app.models as models
import sqlalchemy as sa
import sqlalchemy.orm as so
import wtforms
import wtforms.validators as validators
from sqlalchemy.orm.session import Session
from .classes import NmapScanner, PortScannerError
import logging
logger = logging.getLogger("Nmap scanner action module")


def action_run(targets: List[models.Network | models.Host], target_ports: str | None, project_id: int, current_user_id,
               scan_params: dict[str, bool], session: Session, scanning_host_id: Optional[int], locale: str="en",
               ignore_closed_ports: bool=True, ignore_host_without_open_ports_and_arp_response: bool=True,
               add_host_with_only_arp_response: bool=True, add_network_mutial_visibility: bool=True,
               created_host_marks: List[int] | None=None, edited_host_marks: List[int] | None=None, added_comment: str="") -> Optional[bool]:
    try:
        scanner = NmapScanner()
    except (PortScannerError):
        logger.error("Nmap scanner not found!")
        return False
    scan_command = scanner.build_scan_command(scan_params)
    logger.info(f"Run nmap with args: {scan_command}")
    for target in targets:
        logger.info(f"Run nmap by target {target}")
        scan_result, scan_error, _1, _2 = scanner.scan(str(target.ip_address), target_ports, scan_command)
        logger.info("Nmap run completed")
        logger.warning(f"Error when scanning:\n{scan_error}")
        try:
            scan_result = scan_result.decode()
        except Exception as e:
            logger.error(f"Error when decoding nmap result: {e}")
            return False
        scanner.parse_and_update_database(scan_result, project_id=project_id, current_user_id=current_user_id, session=session,
                                        ignore_closed_ports=ignore_closed_ports,
                                        ignore_host_without_open_ports_and_arp_response=ignore_host_without_open_ports_and_arp_response,
                                        add_host_with_only_arp_response=add_host_with_only_arp_response,
                                        process_operation_system=scan_params["process_operation_system"],
                                        scanning_host_id=scanning_host_id,
                                        add_network_mutial_visibility=add_network_mutial_visibility,
                                        new_host_labels=created_host_marks, exist_host_labels=edited_host_marks,
                                        added_comment=added_comment,
                                        locale=locale)
    return None


def exploit(filled_form: dict, running_user: int, default_options: dict, locale: str, project_id: int) -> None:
    with so.sessionmaker(bind=db.engine)() as session:
        filled_form["script"] = filled_form["nmap_scripts"]
        scan_params = filled_form.copy()
        ports = filled_form['ports']
        if filled_form["scan_type"] == "network":
            networks = session.scalars(sa.select(models.Network).where(models.Network.id.in_(map(int, filled_form["target_networks"])))).all()
            for network in networks:
                action_run([network], ports, project_id, running_user, scan_params, session, filled_form["scanning_host"],
                        locale, filled_form["ignore_closed_ports"], filled_form["ignore_host_without_open_ports_and_arp_response"],
                        filled_form["add_host_with_only_arp_response"], filled_form["add_network_accessible"], filled_form["created_host_marks"],
                        filled_form["edited_host_marks"], filled_form["added_comment"])
        elif filled_form["scan_type"] == "host":
            hosts = session.scalars(sa.select(models.Host).where(models.Host.id.in_(map(int, filled_form["target_hosts"])))).all()
            for host in hosts:
                action_run([host], ports, project_id, running_user, scan_params, session, filled_form["scanning_host"],
                        locale, filled_form["ignore_closed_ports"], filled_form["ignore_host_without_open_ports_and_arp_response"],
                        filled_form["add_host_with_only_arp_response"], filled_form["add_network_accessible"], filled_form["created_host_marks"],
                        filled_form["edited_host_marks"], filled_form["added_comment"])


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
        self.target_networks.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Network).where(models.Network.project_id == project_id))]
        self.target_hosts.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(sa.and_(models.Network.project_id==project_id, models.Host.excluded == False)))]
        self.created_host_marks.choices = [(i.id, i) for i in db.session.scalars(sa.select(models.HostLabel))]
        self.edited_host_marks.choices = [(i.id, i) for i in db.session.scalars(sa.select(models.HostLabel))]
    target_networks = TreeSelectMultipleField(_l("Networks to scan:"), validators=[validators.Optional()])
    target_hosts = TreeSelectMultipleField(_l("Hosts to scan:"), validators=[validators.Optional()])
    scan_type = wtforms.SelectField(_l("Scan type:"), choices=[("network", _l("Network only")), ("host", _l("Host only"))], description=_l("Network only scan - scan current subnet to find host and their port. Host only - scan all host in current network on open ports"))
    ports = wtforms.StringField(_l("Ports:"), validators=[validators.DataRequired(_l("This field is mandatory!"))])
    ignore_closed_ports = wtforms.BooleanField(_l("Ignore ports that do not have the status <Open>:"), default=True)
    ignore_host_without_open_ports_and_arp_response = wtforms.BooleanField(_l("Ignore hosts without open ports and ARP response:"), default=True)
    add_host_with_only_arp_response = wtforms.BooleanField(_l("Add hosts for which an ARP response has been received and there are no open ports:"), default=True)
    scanning_host = Select2Field(models.Host, label=_l("%(field_name)s:", field_name=_l("Scanning host")),
                                  description=_l("The host from which or through which the scan was performed. Affects the mutual visibility of hosts/services with the specified one."),
                                  validators=[validators.Optional()],
                                  attr_title="treeselecttitle")
    add_network_accessible = wtforms.BooleanField(_l("Automatically add mutual visibility of networks:"), default=True)
    process_operation_system = wtforms.BooleanField(_l("Process host operating system data:"), default=True)
    created_host_marks = Select2IconMultipleField(models.HostLabel, _l("Labels for new hosts:"), validators=[validators.Optional()], attr_icon="icon_class", attr_color="icon_color")
    edited_host_marks = Select2IconMultipleField(models.HostLabel, _l("Label for edited hosts:"), description=_l("Add labels to hosts that have been changed"), validators=[validators.Optional()], attr_icon="icon_class", attr_color="icon_color")
    added_comment = WysiwygField(_l("Add description for all scanned host:"), validators=[validators.Optional()])
    scan_tcp = wtforms.BooleanField(_l("Scan TCP ports:"), default=True, validators=[validators.Optional()])
    scan_udp = wtforms.BooleanField(_l("Scan UDP ports:"), default=True, validators=[validators.Optional()])
    scan_sctp = wtforms.BooleanField(_l("Scan SCTP ports:"), default=False, validators=[validators.Optional()])
    process_service_version = wtforms.BooleanField(_l("Process service version information:"), default=True, validators=[validators.Optional()])
    min_parallelism = wtforms.IntegerField(_l("Minimal number of probes (min-parallelism):"), description=_l("These options control the total number of probes that may be outstanding for a host group. They are used for port scanning and host discovery"),
                                           default=None, validators=[validators.Optional()])
    min_rate = wtforms.IntegerField(_l("Minimal directly control scanning rate:"), description=_l("Nmap will do its best to send packets as fast as or faster than the given rate"), validators=[validators.Optional()])
    script_timeout = wtforms.StringField(_l("Script timeout:"), description=_l("Option sets a ceiling on script execution time. The special value 0 can be used to mean 'no timeout'."), default="120m", validators=[validators.Optional()])
    host_timeout = wtforms.StringField(_l("Host timeout:"), description=_l("The maximum amount of time you are willing to wait when scanning host. The special value 0 can be used to mean 'no timeout'."),
                                       default="0", validators=[validators.Optional()])
    timing_pattern = wtforms.SelectField(_l("Timing template:"), validators=[validators.Optional()],
                                         choices=[("0", "paranoid (0)"), ("1", "sneaky (1)"), ("2", "polite (2)"), ("3", "normal (3)"), ("4", "aggressive (4)"), ("5", "insane (5)")], default="3")
    resolve_dns = wtforms.BooleanField(_l("Parallel resolve reverse DNS names for host:"), default=True, validators=[validators.Optional()])
    no_ping_host = wtforms.BooleanField(_l("Treat all hosts as online - skip host discovery:"), validators=[validators.Optional()])
    nmap_scripts = wtforms.StringField(_l("Nmap scripts:"), default="")
    project_id = wtforms.HiddenField(_l("Project ID:"), validators=[validators.InputRequired()])
    submit = wtforms.SubmitField(_l("Scan"))


class NmapScan(ActionModule):
    title = _l("Nmap scan")
    description = _l("Scan project network via Nmap scanner")
    admin_form = AdminOptionsForm
    run_form = ModuleInitForm
    exploit_single_target = staticmethod(action_run)
    exploit = staticmethod(exploit)
    default_options = {}