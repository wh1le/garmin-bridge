from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bluetooth import Bluetooth

garmin_name = "Garmin Fenix 6"
garmin_mac = "AA:BB:CC:DD:EE:FF"

garmin_device = (garmin_name, garmin_mac)


# helpers

def mock_client(mocker):
    client = AsyncMock()
    mocker.patch("src.bluetooth.BleakClient", return_value=client)
    return client


def fake_device(name, address):
    device = MagicMock()
    device.name = name
    device.address = address
    return device


def fake_results(names):
    """Simulates BleakScanner.discover(return_adv=True) output."""
    results = {}
    for name, address in names:
        results[address] = (fake_device(name, address), MagicMock())
    return results


def mock_scanner(mocker, devices):
    return mocker.patch(
        "src.bluetooth.BleakScanner.discover",
        new_callable=AsyncMock,
        return_value=fake_results(devices)
    )


@pytest.mark.asyncio
async def test_scan_populates_devices(mocker):
    mock_scanner(mocker, [garmin_device])
    mocker.patch("src.bluetooth.tui.pick_device", return_value=0)
    mocker.patch("src.bluetooth.tui.spinner")

    bt = Bluetooth()
    await bt.scan()

    assert len(bt.devices) == 1
    assert bt.devices[0].name == garmin_name


@pytest.mark.asyncio
async def test_scan_skips_nameless_devices(mocker):
    mock_scanner(mocker, [(None, garmin_mac)])
    mocker.patch("src.bluetooth.tui.spinner")

    bt = Bluetooth()
    await bt.scan()

    assert bt.devices == []


@pytest.mark.asyncio
async def test_scan_empty(mocker):
    mock_scanner(mocker, [])
    mocker.patch("src.bluetooth.tui.spinner")

    bt = Bluetooth()
    await bt.scan()

    assert bt.devices == []


@pytest.mark.asyncio
async def test_scan_completes_and_stops(mocker):
    discover = mock_scanner(mocker, [garmin_device])
    mocker.patch("src.bluetooth.tui.pick_device", return_value=0)
    mocker.patch("src.bluetooth.tui.spinner")

    bt = Bluetooth()
    await bt.scan()

    discover.assert_awaited_once()


# pair

def mock_dbus(mocker):
    """Mock D-Bus so pair tests work without BlueZ."""
    mock_manager = AsyncMock()

    mock_proxy = MagicMock()
    mock_proxy.get_interface.return_value = mock_manager

    mock_bus = MagicMock()
    mock_bus.export = MagicMock()
    mock_bus.introspect = AsyncMock(return_value=MagicMock())
    mock_bus.get_proxy_object.return_value = mock_proxy

    mock_bus_constructor = MagicMock()
    mock_bus_constructor.connect = AsyncMock(return_value=mock_bus)

    mocker.patch("src.bluetooth.MessageBus", return_value=mock_bus_constructor)
    return mock_bus


@pytest.mark.asyncio
async def test_pair_saves_address(mocker):
    mock_client(mocker)
    mock_dbus(mocker)
    config_set = mocker.patch("src.bluetooth.config.set")

    bt = Bluetooth()
    await bt.pair(garmin_mac)

    config_set.assert_called_once_with("watch.address", garmin_mac)


@pytest.mark.asyncio
async def test_pair_connects_and_pairs(mocker):
    client = mock_client(mocker)
    mock_dbus(mocker)
    mocker.patch("src.bluetooth.config.set")

    bt = Bluetooth()
    await bt.pair(garmin_mac)

    client.connect.assert_awaited_once()
    client.pair.assert_awaited_once()


# connect

@pytest.mark.asyncio
async def test_connect(mocker):
    client = mock_client(mocker)

    bt = Bluetooth()
    await bt.connect(garmin_mac)

    client.connect.assert_awaited_once()
    assert bt.client is not None


# disconnect

@pytest.mark.asyncio
async def test_disconnect(mocker):
    client = mock_client(mocker)

    bt = Bluetooth()
    await bt.connect(garmin_mac)
    await bt.disconnect()

    client.disconnect.assert_awaited_once()
    assert bt.client is None


@pytest.mark.asyncio
async def test_disconnect_when_not_connected():
    bt = Bluetooth()
    await bt.disconnect()
    assert bt.client is None
