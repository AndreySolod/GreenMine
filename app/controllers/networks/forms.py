import wtforms
import wtforms.validators as validators
import ipaddress
import flask_wtf.file as wtfile
from app import db
from app.controllers.forms import WysiwygField, FlaskForm, TreeSelectSingleField, Select2Field, TreeSelectMultipleField, Select2MultipleField
from app.controllers.forms import Select2IconMultipleField, Select2IconField
from app.helpers.general_helpers import validates_port, validates_mac
from app.helpers.projects_helpers import load_network_from_csv
import app.models as models
from flask_babel import lazy_gettext as _l
from flask import g, url_for
import sqlalchemy as sa


class NetworkForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        self.project_id = project_id
        super(NetworkForm, self).__init__(*args, **kwargs)
        self.can_see_network.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Network).where(models.Network.project_id == project_id))]
        self.icon_id.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.NetworkIcon))]
    title = wtforms.StringField(_l("%(field_name)s:", field_name=models.Network.title.info["label"]),
                                validators=[validators.DataRequired(message=_l("This field is mandatory!")),
                                            validators.Length(max=models.Network.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Network.title.type.length))])
    description = WysiwygField(_l("%(field_name)s:", field_name=models.Network.description.info["label"]), validators=[validators.Optional()])
    ip_address = wtforms.StringField(_l("%(field_name)s:", field_name=models.Network.ip_address.info["label"]))
    internal_ip = wtforms.StringField(_l("%(field_name)s:", field_name=models.Network.internal_ip.info["label"]), validators=[validators.Optional()])
    asn = wtforms.StringField(_l("%(field_name)s:", field_name=models.Network.asn.info["label"]), validators=[validators.Optional()])
    connect_cmd = wtforms.TextAreaField(_l("%(field_name)s:", field_name=models.Network.connect_cmd.info["label"]),
                                        validators=[validators.Optional(),
                                                    validators.Length(min=0, max=models.Network.connect_cmd.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Network.connect_cmd.type.length))])
    can_see_network = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.Network.can_see_network.info["label"]), description=models.Network.can_see_network.info["description"])
    vlan_number = wtforms.IntegerField(_l("%(field_name)s:", field_name=models.Network.vlan_number.info["label"]), validators=[validators.Optional()])
    icon_id = Select2IconField(models.NetworkIcon, _l("%(field_name)s:", field_name=models.Network.icon_id.info["label"]), validators=[validators.Optional()])

    def validate_ip_address(self, field):
        ns = [str(i) for i in db.session.scalars(sa.select(models.Network.ip_address).where(models.Network.project_id==int(self.project_id)))]
        try:
            nw = ipaddress.IPv4Network(field.data)
        except ValueError:
            raise validators.ValidationError(_l("Specify the correct IP address with a mask"))
        if str(nw) in ns:
            raise validators.ValidationError(_l("Such a network has already been registered"))

    def validate_internal_ip(form, field):
        try:
            ipaddress.IPv4Network(field.data)
        except ValueError:
            raise validators.ValidationError(_l("Specify the correct IP address with a mask"))


class NetworkCreateForm(NetworkForm):
    submit = wtforms.SubmitField(_l("Create"))
    submit_and_add_new = wtforms.SubmitField(_l("Create and add another one"))


class NetworkEditForm(NetworkForm):
    def __init__(self, default_ip, *args, **kwargs):
        super(NetworkEditForm, self).__init__(*args, **kwargs)
        self.default_ip = default_ip
    submit = wtforms.SubmitField(_l("Save"))

    def validate_ip_address(self, field):
        try:
            if str(ipaddress.IPv4Network(field.data)) == str(self.default_ip):
                return None
        except ValueError:
            raise validators.ValidationError(_l("Specify the correct IP address"))
        super(NetworkEditForm, self).validate_ip_address(field)


class HostForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super(HostForm, self).__init__(*args, **kwargs)
        self.operation_system_family_id.choices = [("0", "---")] + db.session.execute(sa.select(models.OperationSystemFamily.id, models.OperationSystemFamily.title)).all()
        self.from_network_id.choices = [(i.id, i.fulltitle) for i in db.session.scalars(sa.select(models.Network).where(models.Network.project_id==project_id))]
        self.device_type_id.choices = [('0', '')] + db.session.execute(sa.select(models.DeviceType.id, models.DeviceType.title)).all()
        self.device_vendor_id.choices = [('0', '')] + db.session.execute(sa.select(models.DeviceVendor.id, models.DeviceVendor.title)).all()
        self.device_model_id.choices = [('0', '')] + db.session.execute(sa.select(models.DeviceModel.id, models.DeviceModel.title)).all()
        self.state_id.choices =[("0", "---")] + db.session.execute(sa.select(models.HostStatus.id, models.HostStatus.title)).all()
        self.labels.choices = [(i.id, i) for i in db.session.scalars(sa.select(models.HostLabel)).all()]
    title = wtforms.StringField(_l("%(field_name)s:", field_name=models.Host.title.info["label"]),
                                validators=[validators.Length(min=0, max=models.Host.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Host.title.type.length)),
                                            validators.Optional()])
    description = WysiwygField(_l("%(field_name)s:", field_name=models.Host.description.info["label"]), validators=[validators.Optional()])
    from_network_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.Host.from_network_id.info["label"]), validators=[validators.DataRequired()])
    ip_address = wtforms.StringField(_l("%(field_name)s:", field_name=models.Host.ip_address.info["label"]), validators=[validators.DataRequired()])
    mac = wtforms.StringField(_l("%(field_name)s:", field_name=models.Host.mac.info["label"]), validators=[validators.Optional()])
    operation_system_family_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.Host.operation_system_family_id.info["label"]),
                                                     validators=[validators.Optional()])
    operation_system_gen = wtforms.StringField(_l("%(field_name)s:", field_name=models.Host.operation_system_gen.info["label"]),
                                               validators=[validators.Length(min=0, max=models.Host.operation_system_gen.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Host.operation_system_gen.type.length)),
                                                           validators.Optional()])
    device_type_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.Host.device_type_id.info["label"]),
                                         validators=[validators.Optional()])
    device_vendor_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.Host.device_vendor_id.info["label"]),
                                           validators=[validators.Optional()])
    device_model_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.Host.device_model_id.info["label"]),
                                          validators=[validators.Optional()])
    compromised = wtforms.BooleanField(_l("%(field_name)s:", field_name=models.Host.compromised.info["label"]), validators=[validators.Optional()], description=models.Host.compromised.info["description"])
    ipidsequence_class = wtforms.StringField(_l("%(field_name)s:", field_name=models.Host.ipidsequence_class.info["label"]),
                                validators=[validators.Length(min=0, max=models.Host.ipidsequence_class.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Host.ipidsequence_class.type.length)),
                                            validators.Optional()])
    ipidsequence_value = wtforms.StringField(_l("%(field_name)s:", field_name=models.Host.ipidsequence_value.info["label"]),
                                validators=[validators.Length(min=0, max=models.Host.ipidsequence_value.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Host.ipidsequence_value.type.length)),
                                            validators.Optional()])
    state_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.Host.state_id.info["label"]), validators=[validators.Optional()])
    state_reason = wtforms.StringField(_l("%(field_name)s:", field_name=models.Host.state_reason.info["label"]), validators=[validators.Optional(),
                                                                                                                             validators.Length(min=0, max=models.Host.state_reason.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Host.state_reason.type.length))])
    labels = Select2IconMultipleField(models.HostLabel, _l("%(field_name)s:", field_name=models.Host.labels.info["label"]), attr_icon="icon_class", attr_color="icon_color", validators=[validators.Optional()])

    def validate_ip_address(form, field):
        netw = int(form.from_network_id.data)
        hosts = [str(i) for i in db.session.scalars(sa.select(models.Host.ip_address).where(models.Host.from_network_id==netw))]
        try:
            h = ipaddress.IPv4Address(field.data)
        except ValueError:
            raise validators.ValidationError(_l("Specify the correct IP address"))
        if str(h) in hosts:
            raise validators.ValidationError(_l("The host with the specified IP address has already been registered"))
        network = db.session.get(models.Network, str(form.from_network_id.data))
        if ipaddress.IPv4Address(field.data) not in network.ip_address:
            raise validators.ValidationError(_l("The host with the specified IP address has already been registered"))
    
    def validate_mac(form, field):
        validates_mac(field.data, error_type=validators.ValidationError)


class HostFormNew(HostForm):
    excluded = wtforms.BooleanField(_l("%(field_name)s:", field_name=models.Host.device_vendor_id.info["label"]))
    submit = wtforms.SubmitField(_l("Create"))
    submit_and_add_new = wtforms.SubmitField(_l("Create and add another one"))


class HostFormEdit(HostForm):
    def __init__(self, default_host, *args, **kwargs):
        super(HostFormEdit, self).__init__(*args, **kwargs)
        self.default_host = default_host
    submit = wtforms.SubmitField(_l("Save"))

    def validate_ip_address(self, field):
        try:
            if str(ipaddress.IPv4Address(field.data)) == str(self.default_host):
                return None
        except ValueError:
            raise validators.ValidationError(_l("Specify the correct IP address"))
        super(HostFormEdit, self).validate_ip_address(field)


class ServiceForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super(ServiceForm, self).__init__(*args, **kwargs)
        #self.access_protocol_id.choices = [("0", "")] + [(str(i.id), i.title) for i in db.session.scalars(sa.select(AccessProtocol))]
        self.port_state_id.choices = [("0", "")] + [(str(i[0]), i[1]) for i in db.session.execute(sa.select(models.ServicePortState.id, models.ServicePortState.title))]
        self.transport_level_protocol_id.choices = [("0", "")] + [(str(i[0]), i[1]) for i in db.session.execute(sa.select(models.ServiceTransportLevelProtocol.id, models.ServiceTransportLevelProtocol.title))]
        self.host_id.choices = [('0', '')] + [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(models.Network.project_id == project_id))]
        self.issues.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Issue).where(models.Issue.project_id == project_id))]
        self.credentials.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Credential).where(models.Credential.project_id == project_id))]
        self.tasks.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.project_id == project_id))]
        self.accessible_from_hosts.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(models.Network.project_id == project_id))]
    title = wtforms.StringField(_l("%(field_name)s:", field_name=models.Service.title.info["label"]),
                                validators=[validators.Length(min=0, max=models.Service.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Service.title.type.length)),
                                            validators.Optional()])
    description = WysiwygField(_l("%(field_name)s:", field_name=models.Service.description.info["label"]),
                                validators=[validators.Optional()])
    port = wtforms.IntegerField(_l("%(field_name)s:", field_name=models.Service.port.info["label"]),
                                validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    access_protocol_id = Select2Field(models.AccessProtocol, label=_l("%(field_name)s:", field_name=models.Service.access_protocol_id.info["label"]), validators=[validators.Optional()])
    port_state_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.Service.port_state_id.info["label"]), validators=[validators.Optional()])
    port_state_reason = wtforms.StringField(_l("%(field_name)s:", field_name=models.Service.port_state_reason.info["label"]),
                                            validators=[validators.Optional()], description=_l("The reason why such a condition is installed on board"))
    transport_level_protocol_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.Service.transport_level_protocol_id.info["label"]),
                                                      validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    host_id = TreeSelectSingleField(_l("%(field_name)s:", field_name=models.Service.host_id.info["label"]))
    issues = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.Service.issues.info["label"]), validators=[validators.Optional()])
    credentials = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.Service.credentials.info["label"]), validators=[validators.Optional()])
    tasks = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.Service.tasks.info["label"]), validators=[validators.Optional()])
    accessible_from_hosts = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.Service.accessible_from_hosts.info["label"]), validators=[validators.Optional()])
    ssl = wtforms.BooleanField(_l("%(field_name)s:", field_name=models.Service.ssl.info["label"]), validators=[validators.Optional()])

    def validate_host_id(form, field):
        if field.data is None or int(field.data) == 0:
            raise validators.ValidationError(_l("Specify the host for this port"))

    def validate_port(form, field):
        validates_port(field.data, error_type=validators.ValidationError)
        if form.host_id.data is None:
            return None
        servs = db.session.scalars(sa.select(models.Service).where(models.Service.host_id==int(form.host_id.data))).all()
        all_ports = [str(i.port) + "/" + str(i.transport_level_protocol_id) for i in servs]
        if str(field.data) + "/" + str(form.transport_level_protocol_id.data) in all_ports:
            raise validators.ValidationError("The service on such a port is already registered")


class ServiceFormNew(ServiceForm):
    submit = wtforms.SubmitField(_l("Create"))


class ServiceFormEdit(ServiceForm):
    def __init__(self, default_port, *args, **kwargs):
        super(ServiceFormEdit, self).__init__(*args, **kwargs)
        self.default_port = default_port
    submit = wtforms.SubmitField(_l("Save"))

    def validate_port(self, field):
        if int(field.data) == self.default_port:
            return None
        super(ServiceFormEdit, self).validate_port(field)


class EditRelatedObjectsForm(FlaskForm):
    def __init__(self, service: models.Service, *args, **kwargs):
        super(EditRelatedObjectsForm, self).__init__(*args, **kwargs)
        self.tasks.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.project_id==service.project_id)).all()]
        self.issues.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Issue).where(models.Issue.project_id==service.project_id)).all()]
        self.credentials.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Credential).where(models.Credential.project_id==service.project_id)).all()]
        self.tasks.data = [(str(i.id)) for i in service.tasks]
        self.issues.data = [str(i.id) for i in service.issues]
        self.credentials.data = [str(i.id) for i in service.credentials]
    tasks = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.Service.tasks.info["label"]), validators=[validators.Optional()], id='EditRelatedTasksField')
    issues = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.Service.issues.info["label"]), validators=[validators.Optional()], id='EditRelatedIssuesField')
    credentials = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.Service.credentials.info["label"]), validators=[validators.Optional()], id='EditRelatedCredentialsField')


class NewHostDNSnameForm(FlaskForm):
    title = wtforms.StringField(_l("%(field_name)s:", field_name=models.HostDnsName.title.info["label"]),
                                id="NewHostDNStitleField", validators=[validators.InputRequired(message=_l("This field is mandatory!")),
                                            validators.Length(min=1, max=models.HostDnsName.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.HostDnsName.title.type.length))])
    dns_type = wtforms.StringField(_l("%(field_name)s:", field_name=models.HostDnsName.dns_type.info["label"]),
                                   id="NewHostDNStypeField", validators=[validators.Optional(),
                                            validators.Length(min=0, max=models.HostDnsName.dns_type.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.HostDnsName.dns_type.type.length))])


class EditRelatedObjectsHostForm(FlaskForm):
    def __init__(self, host: models.Host, *args, **kwargs):
        super(EditRelatedObjectsHostForm, self).__init__(*args, **kwargs)
        self.interfaces.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(sa.and_(models.Host.id != host.id, models.Network.project_id == host.from_network.project_id)))]
        self.interfaces.data = [str(i.id) for i in host.interfaces]
        self.interfaces.locale = g.locale
        self.interfaces.callback = url_for('networks.get_select2_hosts_interfaces_data', host_id=host.id)
    interfaces = Select2MultipleField(models.Host, _l("%(field_name)s:", field_name=models.Host.interfaces.info["label"]), validators=[validators.Optional()],
                                      id="editHostInterfaces", attr_title="treeselecttitle")


class InventoryForm(FlaskForm):
    def __init__(self, service, *args, **kwargs):
        super(InventoryForm, self).__init__(*args, **kwargs)
        self.host_device_type.choices = [('0', '')] + db.session.execute(sa.select(models.DeviceType.id, models.DeviceType.title).order_by(models.DeviceType.title.asc())).all()
        self.host_device_vendor.choices = [('0', '')] + db.session.execute(sa.select(models.DeviceVendor.id, models.DeviceVendor.title).order_by(models.DeviceVendor.title.asc())).all()
        if service is not None:
            self.host_title.data = service.host.title
            self.host_description.data = service.host.description
            self.service_title.data = service.title
            self.service_description.data = service.description
            self.host_device_type.data = str(service.host.device_type_id)
            self.host_device_vendor.data = str(service.host.device_vendor_id)
    host_title = wtforms.StringField(_l("%(field_name)s:", field_name=_l("Host title")),
                                validators=[validators.Length(min=0, max=models.Host.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Host.title.type.length)),
                                            validators.Optional()])
    host_description = WysiwygField(_l("%(field_name)s:", field_name=_l("Host description")),
                                validators=[validators.Optional()])
    host_device_type = wtforms.SelectField(_l("%(field_name)s:", field_name=models.Host.device_type_id.info["label"]),
                                         validators=[validators.Optional()])
    host_device_vendor = wtforms.SelectField(_l("%(field_name)s:", field_name=models.Host.device_vendor_id.info["label"]),
                                           validators=[validators.Optional()])
    service_title = wtforms.StringField(_l("%(field_name)s:", field_name=_l("Service title")),
                                validators=[validators.Length(min=0, max=models.Service.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Service.title.type.length)),
                                            validators.Optional()])
    service_description = WysiwygField(_l("%(field_name)s:", field_name=_l("Service description")),
                                validators=[validators.Optional()])
    submit = wtforms.SubmitField(_l("Update"))


class NetworkMultipleAddForm(FlaskForm):
    title_position = wtforms.IntegerField(_l("Title position:"), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    ip_address_position = wtforms.IntegerField(_l("IP address position:"), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    vlan_number_position = wtforms.IntegerField(_l("VLAN number position:"), validators=[validators.Optional()])
    description_position = wtforms.IntegerField(_l("Description position:"), validators=[validators.Optional()])
    internal_ip_position = wtforms.IntegerField(_l("Internal IP position:"), validators=[validators.Optional()])
    connect_cmd_position = wtforms.IntegerField(_l("Connect command position:"), validators=[validators.Optional()])
    asn_position = wtforms.IntegerField(_l("ASN position:"), validators=[validators.Optional()])
    separator = wtforms.StringField(_l("Separator:"), validators=[validators.InputRequired(message=_l("This field is mandatory!"))], default=",")
    network_data = wtforms.TextAreaField(_l("Data:"), validators=[validators.InputRequired(message=_l("This field is mandatory!"))], render_kw={"rows": "30"})
    submit = wtforms.SubmitField(_l("Add"))

    def validate_network_data(form, field):
        try:
            parsed_network = load_network_from_csv(form)
        except ValueError as e:
            raise validators.ValidationError(_l("Incorrect IP address format: %(error)s", error=e))
        form.parsed_network = parsed_network