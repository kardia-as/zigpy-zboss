"""Shared fixtures and utilities for testing zigpy-zboss."""
import asyncio
import gc
import inspect
import logging
import sys
import typing
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import pytest
import zigpy
from zigpy.zdo import types as zdo_t

import zigpy_zboss.commands as c
import zigpy_zboss.config as conf
import zigpy_zboss.types as t
from zigpy_zboss.api import ZBOSS
from zigpy_zboss.uart import ZbossNcpProtocol
from zigpy_zboss.zigbee.application import ControllerApplication

LOGGER = logging.getLogger(__name__)

FAKE_SERIAL_PORT = "/dev/ttyFAKE0"


# Globally handle async tests and error on unawaited coroutines
def pytest_collection_modifyitems(session, config, items):
    """Modify collection items."""
    for item in items:
        item.add_marker(
            pytest.mark.filterwarnings(
                "error::pytest.PytestUnraisableExceptionWarning"
            )
        )
        item.add_marker(pytest.mark.filterwarnings("error::RuntimeWarning"))


@pytest.hookimpl(trylast=True)
def pytest_fixture_post_finalizer(fixturedef, request) -> None:
    """Post fixture teardown."""
    if fixturedef.argname != "event_loop":
        return

    policy = asyncio.get_event_loop_policy()
    try:
        loop = policy.get_event_loop()
    except RuntimeError:
        loop = None
    if loop is not None:
        # Cleanup code based on the implementation of asyncio.run()
        try:
            if not loop.is_closed():
                asyncio.runners._cancel_all_tasks(loop)
                loop.run_until_complete(loop.shutdown_asyncgens())
                if sys.version_info >= (3, 9):
                    loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            loop.close()
    new_loop = policy.new_event_loop()  # Replace existing event loop
    # Ensure subsequent calls to get_event_loop() succeed
    policy.set_event_loop(new_loop)


@pytest.fixture
def event_loop(
        request: pytest.FixtureRequest,
) -> typing.Iterator[asyncio.AbstractEventLoop]:
    """Create an instance of the default event loop for each test case."""
    yield asyncio.get_event_loop_policy().new_event_loop()
    # Call the garbage collector to trigger ResourceWarning's as soon
    # as possible (these are triggered in various __del__ methods).
    # Without this, resources opened in one test can fail other tests
    # when the warning is generated.
    gc.collect()
    # Event loop cleanup handled by pytest_fixture_post_finalizer


class ForwardingSerialTransport:
    """Serial transport that hooks directly into a protocol."""

    def __init__(self, protocol):
        """Initailize."""
        self.protocol = protocol
        self._is_connected = False
        self.other = None

        self.serial = Mock()
        self.serial.name = FAKE_SERIAL_PORT
        self.serial.baudrate = 45678
        type(self.serial).dtr = self._mock_dtr_prop = PropertyMock(
            return_value=None
        )
        type(self.serial).rts = self._mock_rts_prop = PropertyMock(
            return_value=None
        )

    def _connect(self):
        assert not self._is_connected
        self._is_connected = True
        self.other.protocol.connection_made(self)

    def write(self, data):
        """Write."""
        assert self._is_connected
        self.protocol.data_received(data)

    def close(
            self, *, error=ValueError("Connection was closed")  # noqa: B008
    ):
        """Close."""
        LOGGER.debug("Closing %s", self)

        if not self._is_connected:
            return

        self._is_connected = False

        # Our own protocol gets gracefully closed
        self.other.close(error=None)

        # The protocol we're forwarding to gets the error
        self.protocol.connection_lost(error)

    def __repr__(self):
        """Representation."""
        return f"<{type(self).__name__} to {self.protocol}>"


def config_for_port_path(path, apply_schema: bool = True):
    """Port path configuration."""
    config = {
        conf.CONF_DEVICE: {conf.CONF_DEVICE_PATH: path},
        zigpy.config.CONF_NWK_BACKUP_ENABLED: False,
    }

    if apply_schema:
        return conf.CONFIG_SCHEMA(config)

    return config


@pytest.fixture
def make_zboss_server(mocker):
    """Instantiate a zboss server."""
    transports = []

    def inner(server_cls, config=None, shorten_delays=True):
        if config is None:
            config = config_for_port_path(FAKE_SERIAL_PORT)

        if shorten_delays:
            mocker.patch(
                "zigpy_zboss.api.AFTER_BOOTLOADER_SKIP_BYTE_DELAY", 0.001
            )
            mocker.patch("zigpy_zboss.api.BOOTLOADER_PIN_TOGGLE_DELAY", 0.001)

        server = server_cls(config)
        server._transports = transports

        server.port_path = FAKE_SERIAL_PORT
        server._uart = None

        def passthrough_serial_conn(
                loop, protocol_factory, url, *args, **kwargs
        ):
            LOGGER.info("Intercepting serial connection to %s", url)

            assert url == FAKE_SERIAL_PORT

            # No double connections!
            if any([t._is_connected for t in transports]):
                raise RuntimeError(
                    "Cannot open two connections to the same serial port"
                )
            if server._uart is None:
                server._uart = ZbossNcpProtocol(
                    config[conf.CONF_DEVICE], server
                )
                mocker.spy(server._uart, "data_received")

            client_protocol = protocol_factory()

            # Client writes go to the server
            client_transport = ForwardingSerialTransport(server._uart)
            transports.append(client_transport)

            # Server writes go to the client
            server_transport = ForwardingSerialTransport(client_protocol)

            # Notify them of one another
            server_transport.other = client_transport
            client_transport.other = server_transport

            # And finally connect both simultaneously
            server_transport._connect()
            client_transport._connect()

            fut = loop.create_future()
            fut.set_result((client_transport, client_protocol))

            return fut

        mocker.patch(
            "zigpy.serial.pyserial_asyncio.create_serial_connection",
            new=passthrough_serial_conn
        )

        # So we don't have to import it every time
        server.serial_port = FAKE_SERIAL_PORT

        return server

    yield inner


@pytest.fixture
def make_connected_zboss(make_zboss_server, mocker):
    """Make a connection fixture."""
    async def inner(server_cls):
        config = conf.CONFIG_SCHEMA(
            {
                conf.CONF_DEVICE: {conf.CONF_DEVICE_PATH: FAKE_SERIAL_PORT},
            }
        )

        zboss = ZBOSS(config)
        zboss_server = make_zboss_server(server_cls=server_cls)

        await zboss.connect()

        zboss.nvram.align_structs = server_cls.align_structs
        zboss.version = server_cls.version

        return zboss, zboss_server

    return inner


@pytest.fixture
def connected_zboss(event_loop, make_connected_zboss):
    """Zboss connected fixture."""
    zboss, zboss_server = event_loop.run_until_complete(
        make_connected_zboss(BaseServerZBOSS)
    )
    yield zboss, zboss_server
    zboss.close()


def reply_to(request):
    """Reply to decorator."""
    def inner(function):
        if not hasattr(function, "_reply_to"):
            function._reply_to = []

        function._reply_to.append(request)

        return function

    return inner


def serialize_zdo_command(command_id, **kwargs):
    """ZDO command serialization."""
    field_names, field_types = zdo_t.CLUSTERS[command_id]

    return t.Bytes(zigpy.types.serialize(kwargs.values(), field_types))


def deserialize_zdo_command(command_id, data):
    """ZDO command deserialization."""
    field_names, field_types = zdo_t.CLUSTERS[command_id]
    args, data = zigpy.types.deserialize(data, field_types)

    return dict(zip(field_names, args))


class BaseServerZBOSS(ZBOSS):
    """Base ZBOSS server."""

    align_structs = False
    version = None

    async def _flatten_responses(self, request, responses):
        if responses is None:
            return
        elif isinstance(responses, t.CommandBase):
            yield responses
        elif inspect.iscoroutinefunction(responses):
            async for rsp in responses(request):
                yield rsp
        elif inspect.isasyncgen(responses):
            async for rsp in responses:
                yield rsp
        elif callable(responses):
            async for rsp in self._flatten_responses(
                    request, responses(request)
            ):
                yield rsp
        else:
            for response in responses:
                async for rsp in self._flatten_responses(request, response):
                    yield rsp

    async def _send_responses(self, request, responses):
        async for response in self._flatten_responses(request, responses):
            await asyncio.sleep(0.001)
            LOGGER.debug(
                "Replying to %s with %s", request, response
            )
            await self.send(response)

    def reply_once_to(self, request, responses, *, override=False):
        """Reply once to."""
        if override:
            self._listeners[request.header].clear()

        request_future = self.wait_for_response(request)

        async def replier():
            request = await request_future
            await self._send_responses(request, responses)

            return request

        return asyncio.create_task(replier())

    def reply_to(self, request, responses, *, override=False):
        """Reply to."""
        if override:
            self._listeners[request.header].clear()

        async def callback(request):
            callback.call_count += 1
            await self._send_responses(request, responses)

        callback.call_count = 0

        self.register_indication_listener(
            request, lambda r: asyncio.create_task(callback(r))
        )

        return callback

    async def send(self, response):
        """Send."""
        if response is not None and self._uart is not None:
            await self._uart.send(response.to_frame(align=self.align_structs))

    def close(self):
        """Close."""
        # We don't clear listeners on shutdown
        with patch.object(self, "_listeners", {}):
            return super().close()


def simple_deepcopy(d):
    """Get a deepcopy."""
    if not hasattr(d, "copy"):
        return d

    if isinstance(d, (list, tuple)):
        return type(d)(map(simple_deepcopy, d))
    elif isinstance(d, dict):
        return type(d)(
            {simple_deepcopy(k): simple_deepcopy(v) for k, v in d.items()}
        )
    else:
        return d.copy()


def merge_dicts(a, b):
    """Merge dicts."""
    c = simple_deepcopy(a)

    for key, value in b.items():
        if isinstance(value, dict):
            c[key] = merge_dicts(c.get(key, {}), value)
        else:
            c[key] = value

    return c


@pytest.fixture
def make_application(make_zboss_server):
    """Application fixture."""
    def inner(
            server_cls,
            client_config=None,
            server_config=None,
            active_sequence=False,
            **kwargs,
    ):
        client_config = merge_dicts(
            config_for_port_path(FAKE_SERIAL_PORT, apply_schema=False),
            client_config or {},
        )
        server_config = merge_dicts(
            config_for_port_path(FAKE_SERIAL_PORT),
            server_config or {},
        )

        app = ControllerApplication(client_config)

        def add_initialized_device(self, *args, **kwargs):
            device = self.add_device(*args, **kwargs)
            device.status = zigpy.device.Status.ENDPOINTS_INIT
            device.model = "Model"
            device.manufacturer = "Manufacturer"

            device.node_desc = zdo_t.NodeDescriptor(
                logical_type=zdo_t.LogicalType.Router,
                complex_descriptor_available=0,
                user_descriptor_available=0,
                reserved=0,
                aps_flags=0,
                frequency_band=zdo_t.NodeDescriptor.FrequencyBand.Freq2400MHz,
                mac_capability_flags=142,
                manufacturer_code=4476,
                maximum_buffer_size=82,
                maximum_incoming_transfer_size=82,
                server_mask=11264,
                maximum_outgoing_transfer_size=82,
                descriptor_capability_field=0,
            )

            ep = device.add_endpoint(1)
            ep.status = zigpy.endpoint.Status.ZDO_INIT

            return device

        async def start_network(self):
            dev = self.add_initialized_device(
                ieee=t.EUI64(range(8)), nwk=0xAABB
            )
            dev.model = "Coordinator Model"
            dev.manufacturer = "Coordinator Manufacturer"

            dev.zdo.Mgmt_NWK_Update_req = AsyncMock(
                return_value=[
                    zdo_t.Status.SUCCESS,
                    t.Channels.ALL_CHANNELS,
                    0,
                    0,
                    [80] * 16,
                ]
            )

        async def energy_scan(self, channels, duration_exp, count):
            return {self.state.network_info.channel: 0x1234}

        app.add_initialized_device = add_initialized_device.__get__(app)
        app.start_network = start_network.__get__(app)
        app.energy_scan = energy_scan.__get__(app)

        app.device_initialized = Mock(wraps=app.device_initialized)
        app.listener_event = Mock(wraps=app.listener_event)
        if not active_sequence:
            app.get_sequence = MagicMock(
                wraps=app.get_sequence, return_value=123
            )
        app.send_packet = AsyncMock(wraps=app.send_packet)
        app.write_network_info = AsyncMock(wraps=app.write_network_info)

        server = make_zboss_server(
            server_cls=server_cls, config=server_config, **kwargs
        )

        return app, server

    return inner


def zdo_request_matcher(
        dst_addr, command_id: t.uint16_t, **kwargs):
    """Request matcher."""
    zdo_kwargs = {k: v for k, v in kwargs.items() if k.startswith("zdo_")}

    kwargs = {k: v for k, v in kwargs.items() if not k.startswith("zdo_")}
    kwargs.setdefault("DstEndpoint", 0x00)
    kwargs.setdefault("SrcEndpoint", 0x00)
    kwargs.setdefault("Radius", None)

    return c.APS.DataReq.Req(
        DstAddr=t.EUI64.convert("00124b0001ab89cd"),
        ClusterId=command_id,
        Payload=t.Payload(
            bytes([kwargs["TSN"]]) +
            serialize_zdo_command(command_id, **zdo_kwargs)
        ),
        **kwargs,
        partial=True,
    )


class BaseZbossDevice(BaseServerZBOSS):
    """Base ZBOSS Device."""

    def __init__(self, *args, **kwargs):
        """Initialize."""
        super().__init__(*args, **kwargs)
        self.active_endpoints = []
        self._nvram = {}
        self._orig_nvram = {}
        self.new_channel = 0
        self.device_state = 0x00
        self.zdo_callbacks = set()
        for name in dir(self):
            func = getattr(self, name)
            for req in getattr(func, "_reply_to", []):
                self.reply_to(request=req, responses=[func])

    def connection_lost(self, exc):
        """Lost connection."""
        self.active_endpoints.clear()
        return super().connection_lost(exc)

    @reply_to(c.NcpConfig.GetJoinStatus.Req(partial=True))
    def get_join_status(self, request):
        """Handle get join status."""
        return c.NcpConfig.GetJoinStatus.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            Joined=0x01  # Assume device is joined for this example
        )

    @reply_to(c.NcpConfig.NCPModuleReset.Req(partial=True))
    def get_ncp_reset(self, request):
        """Handle NCP reset."""
        return c.NcpConfig.NCPModuleReset.Rsp(
            TSN=0xFF,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK
        )

    @reply_to(c.NcpConfig.GetShortAddr.Req(partial=True))
    def get_short_addr(self, request):
        """Handle get short address."""
        return c.NcpConfig.GetShortAddr.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            NWKAddr=t.NWK(0x1234)  # Example NWK address
        )

    @reply_to(c.APS.DataReq.Req(partial=True, DstEndpoint=0))
    def on_zdo_request(self, req):
        """Handle APS Data request."""
        return c.APS.DataReq.Rsp(
            TSN=req.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DstAddr=req.DstAddr,
            DstEndpoint=req.DstEndpoint,
            SrcEndpoint=req.SrcEndpoint,
            TxTime=1,
            DstAddrMode=req.DstAddrMode,
        )

    @reply_to(c.NcpConfig.GetLocalIEEE.Req(partial=True))
    def get_local_ieee(self, request):
        """Handle get local IEEE."""
        return c.NcpConfig.GetLocalIEEE.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            MacInterfaceNum=request.MacInterfaceNum,
            IEEE=t.EUI64([0, 1, 2, 3, 4, 5, 6, 7])  # Example IEEE address
        )

    @reply_to(c.NcpConfig.GetZigbeeRole.Req(partial=True))
    def get_zigbee_role(self, request):
        """Handle get zigbee role."""
        return c.NcpConfig.GetZigbeeRole.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            DeviceRole=t.DeviceRole(1)  # Example role
        )

    @reply_to(c.NcpConfig.GetExtendedPANID.Req(partial=True))
    def get_extended_panid(self, request):
        """Handle get extended PANID."""
        return c.NcpConfig.GetExtendedPANID.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            ExtendedPANID=t.EUI64.convert("00124b0001ab89cd")  # Example PAN ID
        )

    @reply_to(c.ZDO.PermitJoin.Req(partial=True))
    def get_permit_join(self, request):
        """Handle get permit join."""
        return c.ZDO.PermitJoin.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
        )

    @reply_to(c.NcpConfig.GetShortPANID.Req(partial=True))
    def get_short_panid(self, request):
        """Handle get short PANID."""
        return c.NcpConfig.GetShortPANID.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            PANID=t.PanId(0x5678)  # Example short PAN ID
        )

    @reply_to(c.NcpConfig.GetCurrentChannel.Req(partial=True))
    def get_current_channel(self, request):
        """Handle get current channel."""
        if self.new_channel != 0:
            channel = self.new_channel
        else:
            channel = 1

        return c.NcpConfig.GetCurrentChannel.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            Page=0,
            Channel=t.Channels(channel)
        )

    @reply_to(c.NcpConfig.GetChannelMask.Req(partial=True))
    def get_channel_mask(self, request):
        """Handle get channel mask."""
        return c.NcpConfig.GetChannelMask.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            ChannelList=t.ChannelEntryList(
                [t.ChannelEntry(page=1, channel_mask=0x07fff800)])
        )  # Example mask

    @reply_to(c.NcpConfig.ReadNVRAM.Req(partial=True))
    def read_nvram(self, request):
        """Handle NVRAM read."""
        status_code = t.StatusCodeGeneric.ERROR
        if request.DatasetId == t.DatasetId.ZB_NVRAM_COMMON_DATA:
            status_code = t.StatusCodeGeneric.OK
            dataset = t.DSCommonData(
                byte_count=100,
                bitfield=1,
                depth=1,
                nwk_manager_addr=0x0000,
                panid=0x1234,
                network_addr=0x5678,
                channel_mask=t.Channels(14),
                aps_extended_panid=t.EUI64.convert("00:11:22:33:44:55:66:77"),
                nwk_extended_panid=t.EUI64.convert("00:11:22:33:44:55:66:77"),
                parent_addr=t.EUI64.convert("00:11:22:33:44:55:66:77"),
                tc_addr=t.EUI64.convert("00:11:22:33:44:55:66:77"),
                nwk_key=t.KeyData(b'\x01' * 16),
                nwk_key_seq=0,
                tc_standard_key=t.KeyData(b'\x02' * 16),
                channel=15,
                page=0,
                mac_interface_table=t.MacInterfaceTable(
                    bitfield_0=0,
                    bitfield_1=1,
                    link_pwr_data_rate=250,
                    channel_in_use=11,
                    supported_channels=t.Channels(15)
                ),
                reserved=0
            )
            nvram_version = 3
            dataset_version = 1
        elif request.DatasetId == t.DatasetId.ZB_IB_COUNTERS:
            status_code = t.StatusCodeGeneric.OK
            dataset = t.DSIbCounters(
                byte_count=8,
                nib_counter=100,  # Example counter value
                aib_counter=50  # Example counter value
            )
            nvram_version = 1
            dataset_version = 1
        elif request.DatasetId == t.DatasetId.ZB_NVRAM_ADDR_MAP:
            status_code = t.StatusCodeGeneric.OK
            dataset = t.DSNwkAddrMap(
                header=t.NwkAddrMapHeader(
                    byte_count=100,
                    entry_count=2,
                    _align=0
                ),
                items=[
                    t.NwkAddrMapRecord(
                        ieee_addr=t.EUI64.convert("00:11:22:33:44:55:66:77"),
                        nwk_addr=0x1234,
                        index=1,
                        redirect_type=0,
                        redirect_ref=0,
                        _align=0
                    ),
                    t.NwkAddrMapRecord(
                        ieee_addr=t.EUI64.convert("00:11:22:33:44:55:66:78"),
                        nwk_addr=0x5678,
                        index=2,
                        redirect_type=0,
                        redirect_ref=0,
                        _align=0
                    )
                ]
            )
            nvram_version = 2
            dataset_version = 1
        elif request.DatasetId == t.DatasetId.ZB_NVRAM_APS_SECURE_DATA:
            status_code = t.StatusCodeGeneric.OK
            dataset = t.DSApsSecureKeys(
                header=10,
                items=[
                    t.ApsSecureEntry(
                        ieee_addr=t.EUI64.convert("00:11:22:33:44:55:66:77"),
                        key=t.KeyData(b'\x03' * 16),
                        _unknown_1=0
                    ),
                    t.ApsSecureEntry(
                        ieee_addr=t.EUI64.convert("00:11:22:33:44:55:66:78"),
                        key=t.KeyData(b'\x04' * 16),
                        _unknown_1=0
                    )
                ]
            )
            nvram_version = 1
            dataset_version = 1
        else:
            dataset = t.NVRAMDataset(b'')
            nvram_version = 1
            dataset_version = 1

        return c.NcpConfig.ReadNVRAM.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=status_code,
            NVRAMVersion=nvram_version,
            DatasetId=t.DatasetId(request.DatasetId),
            DatasetVersion=dataset_version,
            Dataset=t.NVRAMDataset(dataset.serialize())
        )

    @reply_to(c.NcpConfig.GetTrustCenterAddr.Req(partial=True))
    def get_trust_center_addr(self, request):
        """Handle get trust center address."""
        return c.NcpConfig.GetTrustCenterAddr.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            TCIEEE=t.EUI64.convert("00:11:22:33:44:55:66:77")
            # Example Trust Center IEEE address
        )

    @reply_to(c.NcpConfig.GetRxOnWhenIdle.Req(partial=True))
    def get_rx_on_when_idle(self, request):
        """Handle get RX on when idle."""
        return c.NcpConfig.GetRxOnWhenIdle.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            RxOnWhenIdle=1  # Example RxOnWhenIdle value
        )

    @reply_to(c.NWK.StartWithoutFormation.Req(partial=True))
    def start_without_formation(self, request):
        """Handle start without formation."""
        return c.NWK.StartWithoutFormation.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK  # Example status code
        )

    @reply_to(c.NcpConfig.GetModuleVersion.Req(partial=True))
    def get_module_version(self, request):
        """Handle get module version."""
        return c.NcpConfig.GetModuleVersion.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,  # Example status code
            FWVersion=1,  # Example firmware version
            StackVersion=2,  # Example stack version
            ProtocolVersion=3  # Example protocol version
        )

    @reply_to(c.AF.SetSimpleDesc.Req(partial=True))
    def set_simple_desc(self, request):
        """Handle set simple descriptor."""
        return c.AF.SetSimpleDesc.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK  # Example status code
        )

    @reply_to(c.NcpConfig.GetEDTimeout.Req(partial=True))
    def get_ed_timeout(self, request):
        """Handle get EndDevice timeout."""
        return c.NcpConfig.GetEDTimeout.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            Timeout=t.TimeoutIndex(0x01)  # Example timeout value
        )

    @reply_to(c.NcpConfig.GetMaxChildren.Req(partial=True))
    def get_max_children(self, request):
        """Handle get max children."""
        return c.NcpConfig.GetMaxChildren.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            ChildrenNbr=5  # Example max children
        )

    @reply_to(c.NcpConfig.GetAuthenticationStatus.Req(partial=True))
    def get_authentication_status(self, request):
        """Handle get authentication status."""
        return c.NcpConfig.GetAuthenticationStatus.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            Authenticated=1  # Example authenticated value
        )

    @reply_to(c.NcpConfig.GetParentAddr.Req(partial=True))
    def get_parent_addr(self, request):
        """Handle get parent address."""
        return c.NcpConfig.GetParentAddr.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            NWKParentAddr=t.NWK(0x1234)  # Example parent NWK address
        )

    @reply_to(c.NcpConfig.GetCoordinatorVersion.Req(partial=True))
    def get_coordinator_version(self, request):
        """Handle get coordinator version."""
        return c.NcpConfig.GetCoordinatorVersion.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=t.StatusCodeGeneric.OK,
            CoordinatorVersion=1  # Example coordinator version
        )

    def on_zdo_node_desc_req(self, req, NWKAddrOfInterest):
        """Handle node description request."""
        if NWKAddrOfInterest != 0x0000:
            return

        responses = [
            c.ZDO.NodeDescRsp.Callback(
                Src=0x0000,
                Status=t.ZDOStatus.SUCCESS,
                NWK=0x0000,
                NodeDescriptor=c.zdo.NullableNodeDescriptor(
                    byte1=0,
                    byte2=64,
                    mac_capability_flags=143,
                    manufacturer_code=0,
                    maximum_buffer_size=80,
                    maximum_incoming_transfer_size=160,
                    server_mask=1,  # this differs
                    maximum_outgoing_transfer_size=160,
                    descriptor_capability_field=0,
                ),
            ),
        ]

        if zdo_t.ZDOCmd.Node_Desc_rsp in self.zdo_callbacks:
            responses.append(
                c.ZDO.NodeDescReq.Callback(
                    Src=0x0000,
                    IsBroadcast=t.Bool.false,
                    ClusterId=zdo_t.ZDOCmd.Node_Desc_rsp,
                    SecurityUse=0,
                    TSN=req.TSN,
                    MacDst=0x0000,
                    Data=serialize_zdo_command(
                        command_id=zdo_t.ZDOCmd.Node_Desc_rsp,
                        Status=t.ZDOStatus.SUCCESS,
                        NWKAddrOfInterest=0x0000,
                        NodeDescriptor=zdo_t.NodeDescriptor(
                            **responses[0].NodeDescriptor.as_dict()
                        ),
                    ),
                )
            )

        return responses


class BaseZbossGenericDevice(BaseServerZBOSS):
    """Base ZBOSS generic device."""

    def __init__(self, *args, **kwargs):
        """Init method."""
        super().__init__(*args, **kwargs)
        self.active_endpoints = []
        self._nvram = {}
        self._orig_nvram = {}
        self.device_state = 0x00
        self.zdo_callbacks = set()
        for name in dir(self):
            func = getattr(self, name)
            for req in getattr(func, "_reply_to", []):
                self.reply_to(request=req, responses=[func])

    def connection_lost(self, exc):
        """Lost connection."""
        self.active_endpoints.clear()
        return super().connection_lost(exc)

    @reply_to(c.NcpConfig.ReadNVRAM.Req(partial=True))
    def read_nvram(self, request):
        """Handle NVRAM read."""
        status_code = t.StatusCodeGeneric.ERROR
        if request.DatasetId == t.DatasetId.ZB_NVRAM_COMMON_DATA:
            status_code = t.StatusCodeGeneric.OK
            dataset = t.DSCommonData(
                byte_count=100,
                bitfield=1,
                depth=1,
                nwk_manager_addr=0x0000,
                panid=0x1234,
                network_addr=0x5678,
                channel_mask=t.Channels(14),
                aps_extended_panid=t.EUI64.convert("00:11:22:33:44:55:66:77"),
                nwk_extended_panid=t.EUI64.convert("00:11:22:33:44:55:66:77"),
                parent_addr=t.EUI64.convert("00:11:22:33:44:55:66:77"),
                tc_addr=t.EUI64.convert("00:11:22:33:44:55:66:77"),
                nwk_key=t.KeyData(b'\x01' * 16),
                nwk_key_seq=0,
                tc_standard_key=t.KeyData(b'\x02' * 16),
                channel=15,
                page=0,
                mac_interface_table=t.MacInterfaceTable(
                    bitfield_0=0,
                    bitfield_1=1,
                    link_pwr_data_rate=250,
                    channel_in_use=11,
                    supported_channels=t.Channels(15)
                ),
                reserved=0
            )
            nvram_version = 3
            dataset_version = 1
        elif request.DatasetId == t.DatasetId.ZB_IB_COUNTERS:
            status_code = t.StatusCodeGeneric.OK
            dataset = t.DSIbCounters(
                byte_count=8,
                nib_counter=100,  # Example counter value
                aib_counter=50  # Example counter value
            )
            nvram_version = 1
            dataset_version = 1
        elif request.DatasetId == t.DatasetId.ZB_NVRAM_ADDR_MAP:
            status_code = t.StatusCodeGeneric.OK
            dataset = t.DSNwkAddrMap(
                header=t.NwkAddrMapHeader(
                    byte_count=100,
                    entry_count=2,
                    _align=0
                ),
                items=[
                    t.NwkAddrMapRecord(
                        ieee_addr=t.EUI64.convert("00:11:22:33:44:55:66:77"),
                        nwk_addr=0x1234,
                        index=1,
                        redirect_type=0,
                        redirect_ref=0,
                        _align=0
                    ),
                    t.NwkAddrMapRecord(
                        ieee_addr=t.EUI64.convert("00:11:22:33:44:55:66:78"),
                        nwk_addr=0x5678,
                        index=2,
                        redirect_type=0,
                        redirect_ref=0,
                        _align=0
                    )
                ]
            )
            nvram_version = 2
            dataset_version = 1
        elif request.DatasetId == t.DatasetId.ZB_NVRAM_APS_SECURE_DATA:
            status_code = t.StatusCodeGeneric.OK
            dataset = t.DSApsSecureKeys(
                header=10,
                items=[
                    t.ApsSecureEntry(
                        ieee_addr=t.EUI64.convert("00:11:22:33:44:55:66:77"),
                        key=t.KeyData(b'\x03' * 16),
                        _unknown_1=0
                    ),
                    t.ApsSecureEntry(
                        ieee_addr=t.EUI64.convert("00:11:22:33:44:55:66:78"),
                        key=t.KeyData(b'\x04' * 16),
                        _unknown_1=0
                    )
                ]
            )
            nvram_version = 1
            dataset_version = 1
        else:
            dataset = t.NVRAMDataset(b'')
            nvram_version = 1
            dataset_version = 1

        return c.NcpConfig.ReadNVRAM.Rsp(
            TSN=request.TSN,
            StatusCat=t.StatusCategory(1),
            StatusCode=status_code,
            NVRAMVersion=nvram_version,
            DatasetId=t.DatasetId(request.DatasetId),
            DatasetVersion=dataset_version,
            Dataset=t.NVRAMDataset(dataset.serialize())
        )

    def on_zdo_node_desc_req(self, req, NWKAddrOfInterest):
        """Handle node description request."""
        if NWKAddrOfInterest != 0x0000:
            return

        responses = [
            c.ZDO.NodeDescRsp.Callback(
                Src=0x0000,
                Status=t.ZDOStatus.SUCCESS,
                NWK=0x0000,
                NodeDescriptor=c.zdo.NullableNodeDescriptor(
                    byte1=0,
                    byte2=64,
                    mac_capability_flags=143,
                    manufacturer_code=0,
                    maximum_buffer_size=80,
                    maximum_incoming_transfer_size=160,
                    server_mask=1,  # this differs
                    maximum_outgoing_transfer_size=160,
                    descriptor_capability_field=0,
                ),
            ),
        ]

        if zdo_t.ZDOCmd.Node_Desc_rsp in self.zdo_callbacks:
            responses.append(
                c.ZDO.NodeDescReq.Callback(
                    Src=0x0000,
                    IsBroadcast=t.Bool.false,
                    ClusterId=zdo_t.ZDOCmd.Node_Desc_rsp,
                    SecurityUse=0,
                    TSN=req.TSN,
                    MacDst=0x0000,
                    Data=serialize_zdo_command(
                        command_id=zdo_t.ZDOCmd.Node_Desc_rsp,
                        Status=t.ZDOStatus.SUCCESS,
                        NWKAddrOfInterest=0x0000,
                        NodeDescriptor=zdo_t.NodeDescriptor(
                            **responses[0].NodeDescriptor.as_dict()
                        ),
                    ),
                )
            )

        return responses
