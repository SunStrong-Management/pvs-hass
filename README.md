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

- PVS firmware version
  - 61839 or Greater

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

Note: If prompted for a password, use the last 5 Characters in your PVS Serial. Easily located in the System Info in the Sunstrong Management App.


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


## Migrating from hass-sunpower

There is no automatic migration from [hass-sunpower](https://github.com/krbaker/hass-sunpower), but both integrations read the same values from the PVS, so you can keep the history of your sensors, including the Energy dashboard, by giving the new entities the entity IDs of the old ones:

1. Set up this integration and write down the entity IDs of the hass-sunpower sensors you want to keep, for example the ones used in the Energy dashboard.
2. Remove the hass-sunpower integration. Its history stays in the database.
3. For each sensor, open the matching entity of this integration (see the table below) in **Settings** > **Devices & services** > **Entities**, and in its settings change the **Entity ID** to the old one.

The renamed entity continues the history and long-term statistics of the old entity ID. Readings recorded under the new entity ID before the rename are not moved, so rename the entities soon after setting up the integration.

The sensors are on the device with the same serial number as in hass-sunpower:

| Device   | hass-sunpower     | This integration           |
| -------- | ----------------- | -------------------------- |
| Meter    | `KWh To Home`     | `Positive Lifetime Energy` |
| Meter    | `KWh To Grid`     | `Negative Lifetime Energy` |
| Meter    | `Lifetime Power`  | `Net Lifetime Energy`      |
| Meter    | `Power`           | `3-Phase Power`            |
| Meter    | `KVA Reactive`    | `Reactive Power 3-Phase`   |
| Meter    | `KVA Apparent`    | `Apparent Power 3-Phase`   |
| Meter    | `Power Factor`    | `Total Power Factor`       |
| Meter    | `Frequency`       | `Frequency`                |
| Meter    | `Supply Volts`    | `Line-to-Line Voltage`     |
| Meter    | `Leg 1 Volts`     | `Phase 1-N Voltage`        |
| Meter    | `Leg 2 Volts`     | `Phase 2-N Voltage`        |
| Meter    | `Leg 1 Amps`      | `Current Phase 1`          |
| Meter    | `Leg 2 Amps`      | `Current Phase 2`          |
| Meter    | `Leg 1 KW`        | `Power Phase 1`            |
| Meter    | `Leg 2 KW`        | `Power Phase 2`            |
| Inverter | `Lifetime Power`  | `Lifetime Production`      |
| Inverter | `Power`           | `Current Power Production` |
| Inverter | `Voltage`         | `Production Voltage`       |
| Inverter | `Amps`            | `Production Current`       |
| Inverter | `Frequency`       | `Frequency`                |
| Inverter | `Temperature`     | `Heatsink Temperature`     |

The PVS sensors of hass-sunpower (for example `System Load` or `Memory Used`) report different values than the gateway sensors of this integration, and the MPPT sensors of the inverters are not available.


## Debugging

### Installed through HACS but I can't find it in the integrations list

Some people seem to have a browser caching / refresh issue it seems to be solved by completely
clearing caches or using another browser.

***
[mppt]: https://en.wikipedia.org/wiki/Maximum_power_point_tracking
[power-factor]: https://en.wikipedia.org/wiki/Power_factor
[sunpower-us]: https://us.sunpower.com/products/solar-panels

## Development

This project includes a [devcontainer](https://containers.dev/) configuration for a fully reproducible development environment. It works with VS Code, GitHub Codespaces, or any devcontainer-compatible tool.

### Getting started

1. **Open in a devcontainer** — open this repository in VS Code and select *Reopen in Container* when prompted, or launch it directly in GitHub Codespaces.
2. **Wait for setup** — the `postCreateCommand` runs `scripts/setup`, which installs all Python dependencies from `requirements.txt`.
3. **Start Home Assistant** — run the develop script:

   ```bash
   scripts/develop
   ```

   Home Assistant will start on **port 8123** with the `sunstrong_pvs` custom component loaded automatically. The devcontainer forwards this port, so you can open the HA UI in your browser.

4. **Complete onboarding** — on first launch, open `http://localhost:8123` and create an initial user account. Then add the PVS integration through *Settings → Devices & Services → Add Integration → PVS*.

### Available scripts

| Script | Description |
| --- | --- |
| `scripts/setup` | Installs Python dependencies |
| `scripts/develop` | Starts Home Assistant in debug mode with the custom component |
| `scripts/lint` | Formats and lints the codebase with [Ruff](https://docs.astral.sh/ruff/) |

### Tests

The tests use [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component), which installs the Home Assistant version it was built for, so use a separate virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
```

The tests run pypvs against a mocked PVS that answers from the varserver variables in `tests/fixtures/`. After an intended change to the entities, update the snapshots with `.venv/bin/pytest --snapshot-update` and review the changes in `tests/snapshots/`.

### Project layout

```
custom_components/sunstrong_pvs/   # The integration source code
config/                            # HA config directory (created on first run, gitignored)
scripts/                           # Development helper scripts
tests/                             # Tests, PVS fixtures and snapshots
```

### Tips

- The `scripts/develop` script sets `PYTHONPATH` so that `custom_components/sunstrong_pvs` is discoverable by Home Assistant without symlinks.
- Edits to files under `custom_components/` take effect after restarting Home Assistant (Ctrl+C the running script and re-run `scripts/develop`).
- Run `scripts/lint` before committing to ensure consistent formatting.

## Credits

This integration is based on the work of the following projects:

- [krbaker/hass-sunpower](https://github.com/krbaker/hass-sunpower)
- [home-assistant/integration-enphase_envoy](https://www.home-assistant.io/integrations/enphase_envoy/)

Please note that this integration is not a continuation of the above projects, but rather a separate implementation inspired by them.
There is no automatic migration from the `hass-sunpower` integration, but you can keep the history of your sensors, see
[Migrating from hass-sunpower](#migrating-from-hass-sunpower).
