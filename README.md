# hass-pvs

Home Assistant SunStrong Management (former Sunpower) PVS Integration.

<img width="1597" height="1610" alt="localhost_8123_lovelace_0" src="https://github.com/user-attachments/assets/f305506b-15f4-43cd-905b-6e3eadf5a43b" />

## Overview

This integration allows you to monitor a PVS system via a companion Python library `pypvs`. The latter accesses
an instance of `varserver` running on the PVS via the recently made available PVS FCGI API. The user has access to a list
of publicly available varserver variables for telemetry and basic information about the PVS.

More information about the varserver platform is available at https://github.com/tjmonk/varserver.
The `pypvs` library is available at https://github.com/SunStrong-Management/pypvs.

## Prerequisites

- PVS firmware version 61839 or above

- A recent installation of Home Assistant
- HACS (Home Assistant Community Store) installed
- The PVS connected to your network via Wi-Fi or Ethernet

Please note that previous workarounds using an intermediate device connected to the LAN port of the PVS are not needed,
and probably should be removed altogether.

## Installation

1. Install Home Assistant on your target system https://www.home-assistant.io/installation/
2. Install HACS https://www.hacs.xyz/docs/use/download/download/
3. Add this Repo to HACS by going to the 3 dots on the right ...-> Custom repositories ->
 Repository: `SunStrong-Management/pvs-hass` Category: `Integration`
4. Install this integration in HACS searching for `PVS` (using the latest release is recommended)
5. Restart Home Assistant
6. In the Home Assistant UI go to "Configuration" -> "Integrations" click "+" and search for "PVS".
   * The main configuration is `<IP/Hostname>[:port]`. Check your router configuration for the IP of your PVS


## Options (available from 'configure' once integration is setup)

### Data update interval (seconds)

This sets how fast the integration will try to get updated info from the PVS.


## Devices

### Gateway

This is the data from the PVS Gateway device. These sensors provide diagnostic and usage information about the gateway itself.

| Entity           | Units   | Description                                 |
| ---------------- | ------- | ------------------------------------------- |
| `Uptime`         | Seconds | Time since the gateway was last restarted   |
| `RAM Usage`      | %       | Percentage of RAM currently in use          |
| `Flash Usage`    | %       | Percentage of flash storage currently used  |
| `CPU Usage`      | %       | Percentage of CPU currently in use          |

### Inverter

This is the data from each Micro Inverter.  Each inverter optimizes the power generation
using [MPPT][mppt] all of the panel side power data is reported from each inverter.
You should see one of these for every panel you have, they are listed by serial number.

| Entity            | Units  | Description                                                                  |
| ----------------- | ------ | ---------------------------------------------------------------------------- |
| `Frequency`       | Hz     | Observed AC Frequency.                                                       |
| `Lifetime Energy` | kWh    | Lifetime produced power from this panel / inverter                           |
| `Power`           | kW     | Power this panel is measuring                                                |
| `Voltage`         | Volts  | Voltage this panel is measuring (wired across both phases so seeing 240+-)   |
| `Current`         | Amps   | Electrical current this inverter is producing on the AC side                 |
| `Temperature`     | oC     | Temperature of this inverter                                                 |

### Meter

This is the data from the built-in PVS meter. These sensors provide detailed electrical measurements and energy statistics from the meter.

| Entity                  | Units | Description                              |
|-------------------------|-------|------------------------------------------|
| `3-Phase Power`         | kW    | Total 3-phase power                      |
| `3-Phase Voltage`       | V     | Total 3-phase voltage                    |
| `3-Phase Current`       | A     | Total 3-phase current                    |
| `Frequency`             | Hz    | Grid frequency                           |
| `Lifetime Energy 3-Phase`| kWh  | Lifetime energy measured (3-phase)       |
| `CT Scale Factor`       |       | Current transformer scale factor         |
| `Current Phase 1`       | A     | Current on phase 1                       |
| `Current Phase 2`       | A     | Current on phase 2                       |
| `Negative Lifetime Energy`| kWh | Negative lifetime energy                 |
| `Net Lifetime Energy`   | kWh   | Net lifetime energy                      |
| `Power Phase 1`         | kW    | Power on phase 1                         |
| `Power Phase 2`         | kW    | Power on phase 2                         |
| `Positive Lifetime Energy`| kWh | Positive lifetime energy                 |
| `Reactive Power 3-Phase`| kVAR  | Total 3-phase reactive power             |
| `Apparent Power 3-Phase`| kVA   | Total 3-phase apparent power             |
| `Total Power Factor`    |       | Total power factor ratio                 |
| `Line-to-Line Voltage`  | V     | Voltage between phases                   |
| `Phase 1-N Voltage`     | V     | Voltage phase 1 to neutral               |
| `Phase 2-N Voltage`     | V     | Voltage phase 2 to neutral               |

### ESS (Energy Storage System)

This is the data from the Equinox ESS device. These sensors provide information about the battery, inverter, and operational state of the ESS.

| Entity                    | Units | Description                                 |
|---------------------------|-------|---------------------------------------------|
| `3-Phase Power`           | kW    | Total 3-phase power                         |
| `Negative Lifetime Energy`| kWh   | Negative lifetime energy                    |
| `Positive Lifetime Energy`| kWh   | Positive lifetime energy                    |
| `Phase 1-N Voltage`       | V     | Voltage, phase 1 to neutral                 |
| `Phase 2-N Voltage`       | V     | Voltage, phase 2 to neutral                 |
| `Operating Mode`          | enum  | Current ESS operating mode                  |
| `State of Charge`         | %     | Battery state of charge                     |
| `Customer State of Charge`| %     | Customer-reported state of charge           |
| `State of Health`         | %     | Battery state of health                     |
| `Inverter Temperature`    | °C    | Inverter temperature                        |
| `Battery Voltage`         | V     | Battery voltage                             |
| `Charge Limit Power Max`  | kW    | Maximum charge power limit                  |
| `Discharge Limit Power Max`| kW   | Maximum discharge power limit               |
| `Max Battery Cell Temp`   | °C    | Maximum battery cell temperature            |
| `Min Battery Cell Temp`   | °C    | Minimum battery cell temperature            |
| `Max Battery Cell Voltage`| V     | Maximum battery cell voltage                |
| `Min Battery Cell Voltage`| V     | Minimum battery cell voltage                |

### MIDC (Microgrid Interconnected Device Controller)

This is the data from the MIDC (Transfer Switch) device. These sensors provide state and voltage information about the MIDC.

| Entity             | Units   | Description                        |
| ------------------ | ------- | ---------------------------------- |
| `MIDC State`       |         | Current MIDC state                 |
| `PVD1 State`       |         | Current PVD1 state                 |
| `MIDC Temperature` | °C      | MIDC internal temperature          |
| `Grid Phase 1-N Voltage` | V | Grid voltage, phase 1 to neutral   |
| `Phase 1-N Voltage`| V       | Output voltage, phase 1 to neutral |
| `Grid Phase 2-N Voltage` | V | Grid voltage, phase 2 to neutral   |
| `Phase 2-N Voltage`| V       | Output voltage, phase 2 to neutral |
| `MIDC Supply Voltage` | V    | MIDC supply voltage                |


## Debugging

### Installed through HACS but I can't find it in the integrations list

Some people seem to have a browser caching / refresh issue it seems to be solved by completely
clearing caches or using another browser.

***
[mppt]: https://en.wikipedia.org/wiki/Maximum_power_point_tracking
[power-factor]: https://en.wikipedia.org/wiki/Power_factor
[sunpower-us]: https://us.sunpower.com/products/solar-panels

## Credits

This integration is based on the work of the following projects:

- [krbaker/hass-sunpower](https://github.com/krbaker/hass-sunpower)
- [home-assistant/integration-enphase_envoy](https://www.home-assistant.io/integrations/enphase_envoy/)

Please note that this integration is not a continuation of the above projects, but rather a separate implementation inspired by them.
Thus, transitioning, for example, from the `hass-sunpower` integration is not possible, and users will need to just use this
integration as a replacement.