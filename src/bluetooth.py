from bleak import BleakClient, BleakScanner
from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType
from dbus_fast.service import ServiceInterface, method

from src import tui
from src.config import config
from src.logger import log

AGENT_PATH = "/garmin_bridge/agent"


class _DbusPairingAgent(ServiceInterface):
    def __init__(self):
        super().__init__("org.bluez.Agent1")

    @method()
    def Release(self):
        pass

    @method()
    def RequestPasskey(self, device: 'o') -> 'u':
        pin = input("Enter PIN from watch: ")
        return int(pin)

    @method()
    def RequestConfirmation(self, device: 'o', passkey: 'u'):
        pass

    @method()
    def Cancel(self):
        pass


class Bluetooth:
    def __init__(self, timeout=10.0):
        self.agent = _DbusPairingAgent()
        self.timeout = timeout
        self.devices = []
        self.client = None
        self.bus = None

    async def scan(self):
        with tui.spinner("Scanning for devices..."):
            results = await BleakScanner.discover(timeout=self.timeout, return_adv=True)

        for address in results:
            device = results[address][0]
            if device.name:
                self.devices.append(device)

        if not self.devices:
            log.warning("No Garmin devices found.")
            return

        selected = tui.pick_device(self.devices)
        if selected is None:
            return

        return self.devices[selected]

    async def pair(self, address):
        self.bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        self.bus.export(AGENT_PATH, self.agent)

        introspection = await self.bus.introspect("org.bluez", "/org/bluez")
        bluez = self.bus.get_proxy_object("org.bluez", "/org/bluez", introspection)
        manager = bluez.get_interface("org.bluez.AgentManager1")
        await manager.call_register_agent(AGENT_PATH, "KeyboardDisplay")
        await manager.call_request_default_agent(AGENT_PATH)

        self.client = BleakClient(address)
        await self.client.connect()
        await self.client.pair()

        await manager.call_unregister_agent(AGENT_PATH)
        config.set("watch.address", address)
        log.info("Paired and saved %s", address)

    async def connect(self, address):
        self.client = BleakClient(address)
        await self.client.connect()
        log.info("Connected to %s", address)

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            self.client = None
