# zigpy-zboss

**zigpy-zboss** is a Python library that adds support for common Nordic Semiconductor **[Zigbee](https://www.zigbee.org)** radio modules to **[zigpy](https://github.com/zigpy/)**, a Python Zigbee stack project.

Together with zigpy and compatible home automation software (namely Home Assistant's **[ZHA (Zigbee Home Automation) integration component](https://www.home-assistant.io/integrations/zha/)**), you can directly control Zigbee devices such as Philips Hue, GE, OSRAM LIGHTIFY, Xiaomi/Aqara, IKEA Tradfri, Samsung SmartThings, and many more.

# Hardware requirements
USB-adapters and development-boards based on nRF52840 SoC flashed with the ZBOSS NCP sample.

- **[nRF52840 dongle](https://www.nordicsemi.com/Products/Development-hardware/nrf52840-dongle)**
- **[nRF52840 development kit](https://www.nordicsemi.com/Products/Development-hardware/nrf52840-dk)**

# Firmware
**[nrf-zboss-ncp](https://github.com/kardia-as/nrf-zboss-ncp)** contains required firmware to flash on the device.


# Related projects

### Zigpy
**[zigpy](https://github.com/zigpy/zigpy)** is a **[Zigbee protocol stack](https://en.wikipedia.org/wiki/Zigbee)** integration project to implement the **[Zigbee Home Automation](https://www.zigbee.org/)** standard as a Python library. Zigbee Home Automation integration with zigpy allows you to connect one of many off-the-shelf Zigbee adapters using one of the available Zigbee radio library modules compatible with zigpy to control Zigbee devices. There is currently support for controlling Zigbee device types such as binary sensors (e.g. motion and door sensors), analog sensors (e.g. temperature sensors), lightbulbs, switches, and fans. Zigpy is tightly integrated with **[Home Assistant](https://www.home-assistant.io)**'s **[ZHA component](https://www.home-assistant.io/components/zha/)** and provides a user-friendly interface for working with a Zigbee network.

### Zigpy-znp (reference project)
The development of the zigpy-zboss repository stems from the work done in the **[zigpy-znp](https://github.com/zigpy/zigpy-znp)** repository.