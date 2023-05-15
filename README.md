# zigpy-zboss

**zigpy-zboss** is a Python library that adds support for common Nordic Semiconductor **[Zigbee](https://www.zigbee.org)** radio modules to **[zigpy](https://github.com/zigpy/)**, a Python Zigbee stack project.

Together with zigpy and compatible home automation software (namely Home Assistant's **[ZHA (Zigbee Home Automation) integration component](https://www.home-assistant.io/integrations/zha/)**), you can directly control Zigbee devices such as Philips Hue, GE, OSRAM LIGHTIFY, Xiaomi/Aqara, IKEA Tradfri, Samsung SmartThings, and many more.

# Hardware requirements
USB-adapters and development-boards based on nRF52840 SoC flashed with the ZBOSS NCP sample.

- **[nRF52840 dongle](https://www.nordicsemi.com/Products/Development-hardware/nrf52840-dongle)**
- **[nRF52840 development kit](https://www.nordicsemi.com/Products/Development-hardware/nrf52840-dk)**

# Firmware
**[nrf-zboss-ncp](https://github.com/kardia-as/nrf-zboss-ncp)** contains required firmware to flash on the device.

# External links, documentation, and other development references

- https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/index.html - Specifically see the ZBOSS NCP sample, Zigbee CLI examples, and the ZBOSS NCP Host user guide.
  - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/samples/zigbee/ncp/README.html
  - https://infocenter.nordicsemi.com/index.jsp?topic=%2Fsdk_tz_v4.1.0%2Fzigbee_only_examples.html
  - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/zboss/3.6.0.0/zboss_ncp_host_intro.html
    - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/protocols/zigbee/architectures.html#ug-zigbee-platform-design-ncp-details
    - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/samples/zigbee/ncp/README.html#zigbee-ncp-sample
    - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/protocols/zigbee/tools.html#ug-zigbee-tools-ncp-host
    - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/zboss/3.6.0.0/zboss_ncp_host.html
    - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/zboss/3.11.2.1/zboss_ncp_host_intro.html
    - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/protocols/zigbee/tools.html#id9
- https://github.com/zigpy/zigpy/issues/394 - Previous development discussion about ZBOSS radio library for zigpy.
- https://github.com/zigpy/zigpy/discussions/595 - Reference collections for Zigbee Stack and related dev docks
- https://github.com/MeisterBob/zigpy_nrf52 - Other attemt at making a zigpy library for nFR52
- https://gist.github.com/tomchy/04ac4ff78d6e117d33ab92d9cc1de779 - Another attemt at making a zigpy controller for nFR

### zigpy-znp (reference project)
The development of the zigpy-zboss repository stems from the work done in the **[zigpy-znp](https://github.com/zigpy/zigpy-znp)** project. zigpy-znp is a zigpy radio library for Texas Instruments Z-Stack ZNP interface.

### bellows (another reference project)
The **[bellows](https://github.com/zigpy/bellows)** is made for the Silicon Labs EmberZNet Zigbee Stack's EZSP interface and is another mature zigpy radio library project worth taking a look at as a reference, (as both it and other zigpy radio libraires have some unique features and functions that others do not).

# How to contribute

If you are looking to make a code or documentation contribution to this project suggest that you try to follow the steps in the contributions guide documentation from the zigpy project and its wiki:

- https://github.com/zigpy/zigpy/blob/dev/Contributors.md
- https://github.com/zigpy/zigpy/wiki

Also see:
- https://github.com/firstcontributions/first-contributions/blob/master/README.md
- https://github.com/firstcontributions/first-contributions/blob/master/github-desktop-tutorial.md

# Related projects

### zigpy
**[zigpy](https://github.com/zigpy/zigpy)** is a **[Zigbee protocol stack](https://en.wikipedia.org/wiki/Zigbee)** integration project to implement the **[Zigbee Home Automation](https://www.zigbee.org/)** standard as a Python library. Zigbee Home Automation integration with zigpy allows you to connect one of many off-the-shelf Zigbee adapters using one of the available Zigbee radio library modules compatible with zigpy to control Zigbee devices. There is currently support for controlling Zigbee device types such as binary sensors (e.g. motion and door sensors), analog sensors (e.g. temperature sensors), lightbulbs, switches, and fans. Zigpy is tightly integrated with **[Home Assistant](https://www.home-assistant.io)**'s **[ZHA component](https://www.home-assistant.io/components/zha/)** and provides a user-friendly interface for working with a Zigbee network.
