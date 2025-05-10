from app import db
from app.helpers.general_helpers import validates_port, default_string_slug, validates_mac, utcnow
from app.helpers.admin_helpers import project_enumerated_object, project_object_with_permissions
from .generic import HasComment, HasHistory
from .datatypes import NetworkAddress, IPAddress, LimitedLengthString
from .issues import Issue
from .tasks import ProjectTask
from .credentials import Credential, DefaultCredential
from typing import List, Optional, Set
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.ext.hybrid import hybrid_property
import sqlalchemy.orm as so
from sqlalchemy.orm import validates
from sqlalchemy.orm.session import Session as SessionBase
from .credentials import CredentialByService
from .issues import IssueHasService
import datetime
import ipaddress
from flask_babel import lazy_gettext as _l


@project_object_with_permissions
class Network(HasComment, db.Model, HasHistory):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    archived: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l("Archived")})
    title: so.Mapped[str] = so.mapped_column(sa.String(40), info={'label': _l("Title")})
    description: so.Mapped[str] = so.mapped_column(info={'label': _l("Description")})
    created_at: so.Mapped[datetime.datetime] = so.mapped_column(default=utcnow, info={'label': _l("Created at")})
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Created by")})
    created_by: so.Mapped['User'] = so.relationship(lazy='select', foreign_keys='Network.created_by_id', info={'label': _l("Created by")}) # type: ignore
    updated_at: so.Mapped[Optional[datetime.datetime]] = so.mapped_column(info={"label": _l("Updated at")})
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Updated by")})
    updated_by: so.Mapped['User'] = so.relationship(lazy='select', foreign_keys="Network.updated_by_id", info={'label': _l("Updated by")}) # type: ignore
    ip_address: so.Mapped[ipaddress.IPv4Network] = so.mapped_column(NetworkAddress, info={'label': _l("IP address of network")})
    internal_ip: so.Mapped[Optional[ipaddress.IPv4Network]] = so.mapped_column(NetworkAddress, info={'label': _l("Inner IP address")})
    asn: so.Mapped[Optional[str]] = so.mapped_column(sa.String(20), info={'label': _l('ASN')})
    connect_cmd: so.Mapped[Optional[str]] = so.mapped_column(sa.String(50), info={'label': _l("The connection command")})
    to_hosts: so.Mapped[List["Host"]] = so.relationship(back_populates="from_network", foreign_keys="Host.from_network_id", cascade="all, delete-orphan", info={'label': _l("Avaliable connection to host"), 'help_text': _l("Connection to the following host is avaliable from this subnet")})
    project_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project.id', ondelete='CASCADE'), info={'label': _l("Project")})
    project: so.Mapped["Project"] = so.relationship(lazy='select', back_populates='networks', info={'label': _l("Project")}) # type: ignore

    @property
    def fulltitle(self):
        return _l("Network «%(ip_address)s»: «%(title)s»", ip_address=str(self.ip_address), title=self.title)

    @property
    def treeselecttitle(self):
        return f"«{self.title}»: {self.ip_address}"
    
    @property
    def issues(self):
        return db.session.scalars(sa.select(Issue).join(Issue.services).join(Service.host).join(Host.from_network).where(Network.id == self.id).distinct()).all()

    @property
    def tasks(self):
        return db.session.scalars(sa.select(ProjectTask).join(ProjectTask.services).join(Service.host).join(Host.from_network).where(Network.id == self.id).distinct()).all()

    @validates("ip_address")
    @validates("internal_ip")
    def validates_ip_address(self, key, ip_address):
        if isinstance(ip_address, ipaddress.IPv4Network):
            return ip_address
        return ipaddress.IPv4Network(ip_address)

    __table_args__ = (sa.UniqueConstraint('project_id', 'ip_address', name='_unique_ip_and_project_together'),)

    class Meta:
        verbose_name = _l("Network")
        verbose_name_plural = _l("Networks")
        icon = 'fa-solid fa-network-wired'
        icon_index = 'fa-solid fa-network-wired'
        project_permission_actions = {'index': _l("Show object list"), 'create': _l("Create new object"), 'show': _l("Show object card"),
                                      'update': _l("Edit and update object"), 'delete': _l("Delete object"), 'add_comment': _l("Add comment to object"),
                                      'show_comments': _l("Show comment list of object"), 'show_history': _l("Show object history")}


@project_enumerated_object
class OperationSystemFamily(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(30), info={'label': _l("Title")})

    def __repr__(self):
        return f"<OperationSystemFamily '{self.title}' with id='{self.id}'>"

    class Meta:
        verbose_name = _l("Family of operating systems")
        verbose_name_plural = _l("Operating system families")
        title_new = _l("Add new family of operation systems")
        column_index = ['id', 'string_slug', 'title']


@project_enumerated_object
class DeviceType(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    string_slug: so.Mapped[int] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(50), info={'label': _l("Title")})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Description")})
    nmap_name: so.Mapped[Optional[str]] = so.mapped_column(sa.String(50), info={'label': _l("Nmap-designation")})
    device_models: so.Mapped[List["DeviceModel"]] = so.relationship(back_populates='device_type', info={'label': _l("Device models")}, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<DeviceType '{self.title}' with id='{self.id}'>"
    
    class Meta:
        verbose_name = _l("Device type")
        verbose_name_plural = _l("Device types")
        title_new = _l("Add new device type")
        column_index = ["id", "string_slug", "title"]


@project_enumerated_object
class DeviceVendor(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    string_slug: so.Mapped[int] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(30), info={'label': _l("Title")})
    device_models: so.Mapped[List["DeviceModel"]] = so.relationship(back_populates='vendor', cascade='all, delete-orphan', info={'label': _l("Released models")})

    def __repr__(self):
        return f"<DeviceVendor '{self.title}' with id='{self.id}'>"
    
    class Meta:
        verbose_name = _l("Device vendor")
        verbose_name_plural = _l("Device vendors")
        title_new = _l("Add new device vendor")
        column_index = ['id', 'string_slug', 'title']


@project_enumerated_object
class DeviceModel(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(30), info={'label': _l("Title")})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Description")})
    device_type_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(DeviceType.id, ondelete='CASCADE'), info={'label': _l("Device type")})
    device_type: so.Mapped[DeviceType] = so.relationship(back_populates='device_models', info={'label': _l("Device type")})
    vendor_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(DeviceVendor.id, ondelete='CASCADE'), info={'label': _l("Device vendor")})
    vendor: so.Mapped[DeviceVendor] = so.relationship(back_populates='device_models', info={'label': _l("Device vendor")})


    def __repr__(self):
        return f"<DeviceModel '{self.title}' with id='{self.id}'>"
    
    class Meta:
        verbose_name = _l("Device model")
        verbose_name_plural = _l("Device models")
        title_new = _l("Add new device models")
        column_index = ['id', 'string_slug', 'title', 'description', 'device_type', 'vendor']


@project_enumerated_object
class MacAddressInfo(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    title: so.Mapped[str] = so.mapped_column(sa.String(120), info={'label': _l("Vendor title")})
    mac_prefix: so.Mapped[str] = so.mapped_column(sa.String(14), unique=True, info={'label': _l("MAC prefix")})
    is_private: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l("Private"), "description": _l("If True, then company name and address will not be displayed in public lists")})
    block_type: so.Mapped[Optional[str]] = so.mapped_column(sa.String(4), info={'label': _l("Block type")})

    class Meta:
        verbose_name = _l("MAC address Manufacturer")
        verbose_name_plural = _l("MAC address Manufacturers")
        title_new = _l("Add new record about the MAC address manufacturer")
        column_index = ['id', 'title', 'mac_prefix', 'is_private', 'block_type']


class HostDnsName(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    title: so.Mapped[str] = so.mapped_column(sa.String(255), info={'label': _l("Title")})
    dns_type: so.Mapped[Optional[str]] = so.mapped_column(sa.String(8), info={'label': _l("Record type")})
    to_host_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('host.id', ondelete='CASCADE'), info={'label': _l("Refers to host")})
    to_host: so.Mapped["Host"] = so.relationship(lazy='joined', back_populates='dnsnames', info={'label': _l("Refers to host")})

    __table_args__ = (sa.UniqueConstraint('to_host_id', 'title', 'dns_type', name='_unique_host_title_and_dns_type_together'),)


@project_enumerated_object
class HostStatus(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(30), info={'label': _l("Title")})

    class Meta:
        verbose_name = _l("Host status")
        verbose_name_plural = _l("Host statuses")
        title_new = _l("Add new host status")
        column_index = ['id', 'string_slug', 'title']


class HostAnotherInterface(db.Model):
    first_interface_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('host.id', ondelete='CASCADE'), primary_key=True)
    second_interface_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('host.id', ondelete='CASCADE'), primary_key=True)


@project_object_with_permissions
class Host(HasComment, db.Model, HasHistory):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': 'ID'})
    archived: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l("Archived")})
    title: so.Mapped[Optional[str]] = so.mapped_column(sa.String(50), info={'label': _l("Title")})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={"label": _l("Description")})
    technical: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Technical information"), 'was_escaped': True})
    state_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(HostStatus.id, ondelete='SET NULL'), info={'label': _l("Status")})
    state: so.Mapped[HostStatus] = so.relationship(lazy='select', info={'label': _l("Status")})
    state_reason: so.Mapped[Optional[str]] = so.mapped_column(sa.String(50), info={'label': _l("The reason for the host status")})
    created_at: so.Mapped[datetime.datetime] = so.mapped_column(default=utcnow, info={"label": _l("Created at")})
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Created by")})
    created_by: so.Mapped['User'] = so.relationship(lazy='joined', foreign_keys='Host.created_by_id', info={'label': _l("Created by")}) # type: ignore
    updated_at: so.Mapped[Optional[datetime.datetime]] = so.mapped_column(info={"label": _l("Updated at")})
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Updated by")})
    updated_by: so.Mapped['User'] = so.relationship(lazy='select', foreign_keys="Host.updated_by_id", info={'label': _l("Updated by")}) # type: ignore
    ip_address: so.Mapped[ipaddress.IPv4Address] = so.mapped_column(IPAddress, info={"label": _l("IP address")})
    dnsnames: so.Mapped[List[HostDnsName]] = so.relationship(lazy='select', back_populates='to_host', cascade="all,delete-orphan", info={'label': _l("DNS-names")})
    mac: so.Mapped[Optional[str]] = so.mapped_column(sa.String(17), info={'label': _l("MAC-address")})
    mac_info_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(MacAddressInfo.id, ondelete='SET NULL'), info={'label': _l("MAC address vendor")})
    mac_info: so.Mapped[MacAddressInfo] = so.relationship(lazy='select', foreign_keys='Host.mac_info_id', info={'label': _l("MAC address vendor")})
    operation_system_family_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(OperationSystemFamily.id, ondelete='SET NULL'), info={'label': _l("Operation system family")})
    operation_system_family: so.Mapped[OperationSystemFamily] = so.relationship(lazy='joined', info={'label': _l("Operation system family")})
    operation_system_gen: so.Mapped[Optional[str]] = so.mapped_column(sa.String(30), info={'label': _l("Operation system generation")})
    from_network_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('network.id', ondelete='CASCADE'), info={"label": _l("Refers to Network")})
    from_network: so.Mapped["Network"] = so.relationship(back_populates='to_hosts', foreign_keys="Host.from_network_id", info={'label': _l("Refers to Network")})
    services: so.Mapped[List["Service"]] = so.relationship(back_populates="host", cascade="all, delete-orphan", info={'label': _l("Related services")})
    device_type_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(DeviceType.id, ondelete='SET NULL'), info={'label': _l("Device type")})
    device_type: so.Mapped[DeviceType] = so.relationship(info={'label': _l("Device type")})
    device_vendor_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(DeviceVendor.id, ondelete='SET NULL'), info={'label': _l("Device vendor")})
    device_vendor: so.Mapped[DeviceVendor] = so.relationship(info={'label': _l("Device vendor")})
    device_model_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(DeviceModel.id, ondelete='SET NULL'), info={'label': _l("Device model")})
    device_model: so.Mapped[DeviceModel] = so.relationship(info={'label': _l("Device model")})
    interfaces: so.Mapped[Set["Host"]] = so.relationship(secondary=HostAnotherInterface.__table__, primaryjoin=id==HostAnotherInterface.first_interface_id,
                                                         secondaryjoin=HostAnotherInterface.second_interface_id==id, lazy='select', info={'label': _l("Another IP addresses")})
    excluded: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l("Excluded from the study")})
    issues: so.Mapped[Set[Issue]] = so.relationship(secondary="issue_has_host",
                                                    primaryjoin="Host.id==IssueHasHost.host_id",
                                                    secondaryjoin="Issue.id==IssueHasHost.host_id",
                                                    back_populates='hosts', info={'label': _l("Related issues")})

    @property
    def fulltitle(self):
        if self.title is None or self.title == '':
            return _l("Host «%(ip_address)s»", ip_address=str(self.ip_address))
        else:
            return _l("Host «%(ip_address)s»: «%(title)s»", ip_address=str(self.ip_address), title=self.title)

    @property
    def treeselecttitle(self):
        if self.title is None or self.title == '':
            return f"{self.ip_address}"
        return f"«{self.title}»: {self.ip_address}"

    @property
    def project_id(self):
        return self.from_network.project_id

    @property
    def project(self):
        return self.from_network.project
    
    @property
    def all_issues(self):
        return db.session.scalars(sa.select(Issue).join(Issue.services).join(Service.host).where(sa.and_(Host.id == self.id))
                                  .union(sa.select(Issue).join(Issue.hosts).where(sa.ans_(Host.id == self.id))).distinct()).all()

    @property
    def tasks(self):
        return db.session.scalars(sa.select(ProjectTask).join(ProjectTask.services).join(Service.host).where(Host.id == self.id).distinct()).all()
    
    @property
    def credentials(self):
        return db.session.scalars(sa.select(Credential).join(Credential.services).join(Service.host).where(Host.id == self.id).distinct()).all()
    
    @property
    def default_credentials(self):
        if not self.device_vendor:
            return []
        return db.session.scalars(sa.select(DefaultCredential).where(DefaultCredential.title.ilike('%' + self.device_vendor.title + '%'))).all()
    
    @validates("mac")
    def validates_mac(self, key, mac):
        if mac == '':
            return mac
        return validates_mac(mac)
    

    @validates("ip_address")
    def validates_ip_address(self, key, ip_address):
        if isinstance(ip_address, ipaddress.IPv4Address):
            return ip_address
        return ipaddress.IPv4Address(ip_address)

    def parent(self):
        return self.from_network

    __table_args__ = (sa.UniqueConstraint('from_network_id', 'ip_address', name='_unique_ip_and_network_together'),)

    def assign_interface(self, interface: "Host"):
        ''' Mark host (interface paramether) as another interface of current host. Also marked interface as another host for all current host interfaces '''
        for i in self.interfaces:
            i.interfaces.add(interface)
        self.interfaces.add(interface)
    
    def drop_interface(self, interface: "Host"):
        ''' Drop host (interface paramether) from interfaces list of current host. Also dropped from another interfaces '''
        for i in self.interfaces:
            if i is interface:
                continue
            i.interfaces.remove(interface)
        self.interfaces.remove(interface)
    
    def flush_interfaces(self):
        self_ifaces = self.interfaces.copy()
        for i in self_ifaces:
            self.drop_interface(i)

    class Meta:
        verbose_name = _l("Host")
        verbose_name_plural = _l("Hosts")
        icon = 'fa-solid fa-server'
        icon_index = 'fa-solid fa-server'
        project_permission_actions = {'index': _l("Show object list"), 'create': _l("Create new object"), 'show': _l("Show object card"),
                                      'update': _l("Edit and update object"), 'delete': _l("Delete object"), 'add_comment': _l("Add comment to object"),
                                      'show_comments': _l("Show comment list of object"), 'show_history': _l("Show object history")}


@event.listens_for(SessionBase, 'before_flush')
def update_host_mac_vendor_info(session, flush_context, instances):
    '''For all changed host if MAC-address is changed also change MAC vendor '''
    hs = [u for u in session.dirty if isinstance(u, Host)]
    hs += [u for u in session.new if isinstance(u, Host)]
    for i in hs:
        if i.mac:
            i.mac = i.mac.lower()
            # Для начала возьмём самый длинный префикс, и по мере уменьшения до 2 символов будем уменьшать значение префикса:
            for mac_prefix_length in range(13, 2, -1):
                mac_vendor = session.scalars(sa.select(MacAddressInfo).where(MacAddressInfo.mac_prefix == i.mac[:mac_prefix_length])).first()
                if mac_vendor:
                    i.mac_info = mac_vendor
                    break


@project_enumerated_object
class ServiceTransportLevelProtocol(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(30), info={'label': _l("Title")})

    def __repr__(self):
        return f"<ServiceTransportLevelProtocol with title='{self.title}', string_slug='{self.string_slug}' and id='{self.id}'>"

    class Meta:
        verbose_name = _l("Transport Layer Protocol")
        verbose_name_plural = _l("Transport Layer Protocols")
        title_new = _l("Add new Transport Layer Protocol")
        column_index = ['id', 'string_slug', 'title']


@project_enumerated_object
class DefaultPortAndTransportProto(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    title: so.Mapped[Optional[str]] = so.mapped_column(sa.String(20), info={'label': _l("Title"), 'on_form': False})
    port: so.Mapped[int] = so.mapped_column(info={'label': _l("Port")})
    transport_level_protocol_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(ServiceTransportLevelProtocol.id, ondelete='CASCADE'), info={'label': _l("Transport layer protocol")})
    transport_level_protocol: so.Mapped["ServiceTransportLevelProtocol"] = so.relationship(lazy='joined', info={'label': _l("Transport Layer Protocol")})
    access_protocol_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('access_protocol.id', ondelete='CASCADE'), info={'label': _l("Application Layer Protocol")})
    access_protocol: so.Mapped["AccessProtocol"] = so.relationship(lazy='select', back_populates='default_port', info={'label': _l("Application Layer Protocol")})

    def __repr__(self):
        return f"<DefaultPortAndTransportProtocol with id={self.id}, port={self.port} and transport_level_protocol={self.transport_level_protocol.title}>"

    @validates("port")
    def validates_default_port(self, key, port):
        return validates_port(port)

    class Meta:
        verbose_name = _l("Port with transport layer protocol")
        verbose_name_plural = _l("Ports with transport layer protocol")
        title_new = 'Добавить порт с протоколом транспортного уровня'
        column_index = ['id', 'title', 'port', 'transport_level_protocol.title-select', 'access_protocol']


@event.listens_for(SessionBase, 'before_commit')
def update_title_port_and_transport_proto(session):
    ''' For all elements of class DefaultPortAndTransportProto added attribute 'title' '''
    ptps = [u for u in session.dirty if isinstance(u, DefaultPortAndTransportProto)]
    ptps += [u for u in session.new if isinstance(u, DefaultPortAndTransportProto)]
    for i in ptps:
        if i.title is None or i.title == '' or i.title == f"{i.port}/None":
            if i.transport_level_protocol is None:
                i.title = f"{i.port}/None"
            else:
                i.title = f"{i.port}/{i.transport_level_protocol.title}"


@project_enumerated_object
class AccessProtocol(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(30), info={'label': _l("Title")})
    default_port: so.Mapped[List["DefaultPortAndTransportProto"]] = so.relationship(lazy='select', back_populates='access_protocol', cascade='all, delete-orphan', info={'label': _l("Default ports")})
    comment: so.Mapped[Optional[str]] = so.mapped_column(LimitedLengthString(60), info={'label': _l("Nmap-comment")})

    @property
    def treeselecttitle(self):
        return self.title

    def __repr__(self):
        return f"<AccessProtocol '{self.title}' with default_port='{self.default_port}' and id='{self.id}'>"

    class Meta:
        verbose_name = _l("Application Layer Protocol")
        verbose_name_plural = _l("Application Layer Protocols")
        title_new = _l("Add new application Layer protocol")
        column_index = ['id', 'string_slug', 'title', 'default_port', 'comment']


@project_enumerated_object
class ServicePortState(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l("ID")})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l("Slug")})
    title: so.Mapped[str] = so.mapped_column(sa.String(30), info={'label': _l("Title")})

    def __repr__(self):
        return f"<ServicePortState with title='{self.title}', string_slug='{self.string_slug}' and id='{self.id}'>"

    class Meta:
        verbose_name = _l("Port status")
        verbose_name_plural = _l("Port statuses")
        title_new = _l("Add new port status")
        column_index = ['id', 'string_slug', 'title']


@project_object_with_permissions
class Service(HasComment, db.Model, HasHistory):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    archived: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l('Archived')})
    title: so.Mapped[Optional[str]] = so.mapped_column(sa.String(60), info={'label': _l("Title")})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Description")})
    technical: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Technical information"), 'was_escaped': True})
    created_at: so.Mapped[datetime.datetime] = so.mapped_column(default=utcnow, info={'label': _l("Created at")})
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Created by")})
    created_by: so.Mapped['User'] = so.relationship(lazy='joined', foreign_keys='Service.created_by_id', info={'label': _l("Created by")}) # type: ignore
    updated_at: so.Mapped[Optional[datetime.datetime]] = so.mapped_column(info={'label': _l("Updated at")})
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Updated by")})
    updated_by: so.Mapped["User"] = so.relationship(lazy='joined', foreign_keys='Service.updated_by_id', info={'label': _l("Updated by")}) # type: ignore
    port: so.Mapped[int] = so.mapped_column(info={'label': _l("Port")})
    access_protocol_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(AccessProtocol.id, ondelete='SET NULL'), info={'label': _l("Application Layer Protocol")})
    access_protocol: so.Mapped["AccessProtocol"] = so.relationship(lazy='joined', info={'label': _l("Application Layer Protocol")})
    port_state_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(ServicePortState.id, ondelete='SET NULL'), info={'label': _l("Port status")})
    port_state: so.Mapped["ServicePortState"] = so.relationship(lazy='joined', info={'label': _l("Port status")})
    port_state_reason: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("The reason for the port status")})
    transport_level_protocol_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(ServiceTransportLevelProtocol.id, ondelete='SET NULL'), info={'label': _l("Transport Layer Protocol")})
    transport_level_protocol: so.Mapped["ServiceTransportLevelProtocol"] = so.relationship(lazy='joined', info={'label': _l("Transport Layer Protocol")})
    host_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Host.id, ondelete='CASCADE'), info={'label': _l("Host")})
    host: so.Mapped["Host"] = so.relationship(lazy='joined', back_populates='services', info={'label': _l("Host")})
    issues: so.Mapped[List["Issue"]] = so.relationship(secondary=IssueHasService.__table__,
                                                       primaryjoin='Service.id==IssueHasService.service_id',
                                                       secondaryjoin='Issue.id==IssueHasService.issue_id',
                                                       back_populates="services",
                                                       info={'label': _l("Issues")})
    credentials: so.Mapped[List["Credential"]] = so.relationship(secondary=CredentialByService.__table__, primaryjoin='Service.id==CredentialByService.service_id', secondaryjoin='CredentialByService.credential_id==Credential.id', back_populates='services', lazy='select', info={'label': _l("Credentials")})
    screenshot_http_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('file_data.id', ondelete='SET NULL'), info={'label': _l('http screenshot of the web interface')})
    screenshot_http: so.Mapped["FileData"] = so.relationship(lazy='select', info={'label': _l("http screenshot of the web interface")}, foreign_keys=[screenshot_http_id]) # type: ignore
    http_title: so.Mapped[Optional[str]] = so.mapped_column(sa.String(80), info={'label': _l("Title of http site")})
    screenshot_https_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('file_data.id', ondelete="SET NULL"), info={'label': _l("https screenshot of the web interface")})
    screenshot_https: so.Mapped["FileData"] = so.relationship(lazy='select', info={'label': _l("https screenshot of the web interface")}, foreign_keys=[screenshot_https_id]) # type: ignore
    https_title: so.Mapped[Optional[str]] = so.mapped_column(sa.String(80), info={'label': _l("Title of https site")})
    tasks: so.Mapped[List["ProjectTask"]] = so.relationship(secondary='service_has_task',
                                                            primaryjoin='Service.id==ServiceHasTask.service_id',
                                                            secondaryjoin='ServiceHasTask.task_id==ProjectTask.id',
                                                            back_populates='services', info={'label': _l("Related tasks")})
    has_been_inventoried: so.Mapped[bool] = so.mapped_column(default=False, server_default=sa.false(), info={'label': _l("Has been inventoried")})

    @property
    def fulltitle(self):
        if self.title is None or self.title == '':
            return _l("Service «%(ip_address)s:%(port)s»", ip_address=str(self.host.ip_address), port=str(self.port))
        return _l("Service «%(ip_address)s:%(port)s»: «%(title)s»", ip_address=str(self.host.ip_address), port=str(self.port), title=self.title)

    @property
    def treeselecttitle(self):
        if self.transport_level_protocol is not None:
            return f"{str(self.host.ip_address)}:{self.port}/{self.transport_level_protocol.title}"
        return f"{str(self.host.ip_address)}:{self.port}"

    @property
    def project_id(self):
        return self.host.from_network.project_id

    @property
    def project(self):
        return self.host.from_network.project

    @validates("port")
    def validates_port(self, key, port):
        validates_port(port)
        return port

    def parent(self):
        return self.host

    __table_args__ = (sa.UniqueConstraint('host_id', 'port', 'transport_level_protocol_id', name='_unique_host_port_and_transport_protocol'),)

    class Meta:
        verbose_name = _l("Service")
        verbose_name_plural = _l("Services")
        icon = 'fa-solid fa-anchor'
        icon_index = 'fa-solid fa-anchor'
        project_permission_actions = {'index': _l("Show object list"), 'create': _l("Create new object"), 'show': _l("Show object card"),
                                      'update': _l("Edit and update object"), 'delete': _l("Delete object"), 'add_comment': _l("Add comment to object"),
                                      'show_comments': _l("Show comment list of object"), 'show_history': _l("Show object history"),
                                      'take_screenshot': _l("Takes services screenshot")}
