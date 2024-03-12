# zigpy-zboss

**zigpy-zboss** is a Python library project that adds support for common Nordic Semiconductor nRF modules to **[zigpy (a open source Python Zigbee stack project)](https://github.com/zigpy/)** and other Network Co-Processor radios that uses firmware based on **[ZOI (ZBOSS Open Initiative) by DSR](https://dsr-zoi.com/)**.

Together with the zigpy library and a home automation software application with compatible Zigbee gateway implementation, (such as for example the **[Home Assistant's ZHA integration component](https://www.home-assistant.io/integrations/zha/)**), you can directly control Zigbee devices from most product manufacturers, like; IKEA, Philips Hue, Inovelli, LEDVANCE/OSRAM, SmartThings/Samsung, SALUS/Computime, SONOFF/ITEAD, Xiaomi/Aqara, and many more.

# Back-story and use cases

This is currently an 'as-is' independent and unofficial implementation radio library for zigpy, as such should be considered experimental and you should only expect best-effort support from volunteers in the open-source community!

Zigbee NCP support for ZOI (ZBOSS Open Initiative) based Zigbee radios compatible with ZBOSS NCP firmware for zigpy based Zigbee gateway implementation is still in very early development. 

Development is initially focused on Zigbee Coordinator functionality Nordic Semiconductor's development kit hardware which has been tested to be compatible. Those also officially recognized as Zigbee-Compliant platforms by the CSA (Connectivity Standards Alliance, formerly the Zigbee Alliance), of which both [DSR Cooperation](https://pt.dsr-corporation.com/news/zboss-open-initiative-in-2021/) and [Nordic Semiconductor](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/zboss/) are board and promoter members of.

# Hardware requirements

Nordic Semi USB adapters and development kits/boards based on nRF52840 SoC are used as reference hardware in the zigpy-zboss project:

- **[nRF52840 dongle](https://www.nordicsemi.com/Products/Development-hardware/nrf52840-dongle)**
- **[nRF52840 development kit](https://www.nordicsemi.com/Products/Development-hardware/nrf52840-dk)**

# Firmware

Development and testing in zigpy-zboss project is done with a firmware image built using the [ZBOSS NCP Host sample](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/samples/zigbee/ncp/README.html) from Nordic Semi:

-  **[nrf-zboss-ncp](https://github.com/kardia-as/nrf-zboss-ncp)** - Compiled ZBOSS NCP Host firmware image required to be flash on the nRF52840 device.

# Releases via PyPI

Tagged versions will also be released via PyPI

 - https://pypi.org/project/zigpy-zboss/
 - https://pypi.org/project/zigpy-zboss/#history
 - https://pypi.org/project/zigpy-zboss/#files

# External links, documentation, and other development references

- [ZBOSS NCP Serial Protocol (v1.5) prepared by DSR Corporation for ZOI](https://cloud.dsr-corporation.com/index.php/s/BAn4LtRWbJjFiAm)
- https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/index.html - Specifically see the ZBOSS NCP sample, Zigbee CLI examples, and the ZBOSS NCP Host user guide.
  - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/samples/zigbee/ncp/README.html
  - https://infocenter.nordicsemi.com/index.jsp?topic=%2Fsdk_tz_v4.1.0%2Fzigbee_only_examples.html
  - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/zboss/3.6.0.0/zboss_ncp_host_intro.html
    - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/protocols/zigbee/architectures.html#ug-zigbee-platform-design-ncp-details
    - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/samples/zigbee/ncp/README.html#zigbee-ncp-sample
    - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/protocols/zigbee/tools.html#ug-zigbee-tools-ncp-host
    - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/zboss/3.6.0.0/zboss_ncp_host.html
    - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/zboss/3.11.2.1/zboss_ncp_host_intro.html
    - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/protocols/zigbee/tools.html
      - https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/protocols/zigbee/tools.html#ug-zigbee-tools-ncp-host
        - [ZBOSS NCP Host (v2.2.1) source code](https://developer.nordicsemi.com/Zigbee/ncp_sdk_for_host/ncp_host_v2.2.1.zip)
- https://github.com/zigpy/zigpy/issues/394 - Previous development discussion about ZBOSS radio library for zigpy.
- https://github.com/zigpy/zigpy/discussions/595 - Reference collections for Zigbee Stack and related dev docks
- https://github.com/MeisterBob/zigpy_nrf52 - Other attemt at making a zigpy library for nFR52
- https://gist.github.com/tomchy/04ac4ff78d6e117d33ab92d9cc1de779 - Another attemt at making a zigpy controller for nFR

## Other radio libraries for zigpy to use as reference projects

Note! The initial development of the zigpy-zboss radio library for zigpy stems from information learned from the work in the **[zigpy-znp](https://github.com/zigpy/zigpy-znp)** project.

### zigpy-znp
The **[zigpy-znp](https://github.com/zigpy/zigpy-znp)** zigpy radio library for Texas Instruments Z-Stack ZNP interface and has been the primary reference to base the zigpy-zboss radio library on. zigpy-znp is very stable with TI Z-Stack 3.x.x, ([zigpy-znp also offers some stand-alone CLI tools](https://github.com/zigpy/zigpy-znp/blob/dev/TOOLS.md) that are unique for Texas Instruments hardware and Zigbee stack).

### zigpy-deconz
The **[zigpy-deconz](https://github.com/zigpy/zigpy-deconz)** is another mature radio library for Dresden Elektronik's [deCONZ Serial Protocol interface](https://github.com/dresden-elektronik/deconz-serial-protocol) that is used by the deconz firmware for their ConBee and RaspBee seriies of Zigbee Coordinator adapters. Existing zigpy developers previous advice has been to also look at zigpy-deconz since it is somewhat similar to the ZBOSS serial protocol implementation.

##### zigpy deconz parser
[zigpy-deconz-parser](https://github.com/zha-ng/zigpy-deconz-parser) allow developers to parse Home Assistant's ZHA component debug logs using the zigpy-deconz radio library if you are using a deCONZ based adapter like ConBee or RaspBee.

### bellows
The **[bellows](https://github.com/zigpy/bellows)** is made Silicon Labs [EZSP (EmberZNet Serial Protocol)](https://www.silabs.com/documents/public/user-guides/ug100-ezsp-reference-guide.pdf) interface and is another mature zigpy radio library project worth taking a look at as a reference, (as both it and some other zigpy radio libraires have some unique features and functions that others do not).

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

### zigpy-cli (zigpy command line interface)
[zigpy-cli](https://github.com/zigpy/zigpy-cli) is a unified command line interface for zigpy radios. The goal of this project is to allow low-level network management from an intuitive command line interface and to group useful Zigbee tools into a single binary.

### ZHA Device Handlers
ZHA deviation handling in Home Assistant relies on the third-party [ZHA Device Handlers](https://github.com/zigpy/zha-device-handlers) project (also known unders zha-quirks package name on PyPI). Zigbee devices that deviate from or do not fully conform to the standard specifications set by the [Zigbee Alliance](https://www.zigbee.org) may require the development of custom [ZHA Device Handlers](https://github.com/zigpy/zha-device-handlers) (ZHA custom quirks handler implementation) to for all their functions to work properly with the ZHA component in Home Assistant. These ZHA Device Handlers for Home Assistant can thus be used to parse custom messages to and from non-compliant Zigbee devices. The custom quirks implementations for zigpy implemented as ZHA Device Handlers for Home Assistant are a similar concept to that of [Hub-connected Device Handlers for the SmartThings platform](https://docs.smartthings.com/en/latest/device-type-developers-guide/) as well as that of [zigbee-herdsman converters as used by Zigbee2mqtt](https://www.zigbee2mqtt.io/how_tos/how_to_support_new_devices.html), meaning they are each virtual representations of a physical device that expose additional functionality that is not provided out-of-the-box by the existing integration between these platforms.

### ZHA integration component for Home Assistant
[ZHA integration component for Home Assistant](https://www.home-assistant.io/integrations/zha/) is a reference implementation of the zigpy library as integrated into the core of **[Home Assistant](https://www.home-assistant.io)** (a Python based open source home automation software). There are also other GUI and non-GUI projects for Home Assistant's ZHA components which builds on or depends on its features and functions to enhance or improve its user-experience, some of those are listed and linked below.

#### ZHA Toolkit
[ZHA Toolkit](https://github.com/mdeweerd/zha-toolkit) is a custom service for "rare" Zigbee operations using the [ZHA integration component](https://www.home-assistant.io/integrations/zha) in [Home Assistant](https://www.home-assistant.io/). The purpose of ZHA Toolkit and its Home Assistant 'Services' feature, is to provide direct control over low level zigbee commands provided in ZHA or zigpy that are not otherwise available or too limited for some use cases. ZHA Toolkit can also; serve as a framework to do local low level coding (the modules are reloaded on each call), provide access to some higher level commands such as ZNP backup (and restore), make it easier to perform one-time operations where (some) Zigbee knowledge is sufficient and avoiding the need to understand the inner workings of ZHA or Zigpy (methods, quirks, etc).

#### ZHA Device Exporter
[zha-device-exporter](https://github.com/dmulcahey/zha-device-exporter) is a custom component for Home Assistant to allow the ZHA component to export lists of Zigbee devices.

#### ZHA Network Visualization Card
[zha-network-visualization-card](https://github.com/dmulcahey/zha-network-visualization-card) was a custom Lovelace element for Home Assistant which visualize the Zigbee network for the ZHA component.

#### ZHA Network Card
[zha-network-card](https://github.com/dmulcahey/zha-network-card) was a custom Lovelace card for Home Assistant that displays ZHA component Zigbee network and device information in Home Assistant
