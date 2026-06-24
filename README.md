# Tauron G13 — Home Assistant integration

Tracks the current **Tauron G13** electricity tariff zone so you can shift
flexible loads (dishwasher, washing machine, EV, heat pump) into the cheap
hours and avoid the afternoon peak.

G13 is a **fixed, published three-zone schedule** — not a market tariff — so
this integration computes everything **offline**. No scraping, no API, no
account. The only input it needs is the Polish public-holiday calendar, which
it derives from the [`holidays`](https://pypi.org/project/holidays/) library
(so movable feasts like Boże Ciało, and the 2025+ Wigilia day off, are handled
automatically).

It does **not** track prices — only zones.

## Zones

| Zone | Winter (Oct 1 – Mar 31) | Summer (Apr 1 – Sep 30) |
|------|-------------------------|-------------------------|
| `peak` (most expensive)    | 16:00–21:00 | 19:00–22:00 |
| `mid`  (medium)            | 07:00–13:00 | 07:00–13:00 |
| `offpeak` (cheapest)       | 13:00–16:00, 21:00–07:00 | 13:00–19:00, 22:00–07:00 |

Weekends and Polish public holidays are `offpeak` all day.

## Entities

| Entity | Type | What it's for |
|--------|------|---------------|
| `sensor.tauron_g13_zone` | enum sensor | Current zone: `peak` / `mid` / `offpeak`. Attributes: `season`, `is_free_day`, `next_zone`, `next_change`, `minutes_until_change`. |
| `binary_sensor.tauron_g13_is_cheap` | binary | On during off-peak — **run** flexible loads now. |
| `binary_sensor.tauron_g13_is_peak` | binary | On during the afternoon peak — **defer** loads. |
| `calendar.tauron_g13_zones` | calendar | Zone blocks as events, past and future — powers the timeline view. |

## Installation

### HACS (custom repository)

1. HACS → ⋮ → **Custom repositories**.
2. Add `https://github.com/kubukoz/ha-tauron-g13`, category **Integration**.
3. Install **Tauron G13**, restart Home Assistant.
4. **Settings → Devices & Services → Add Integration → Tauron G13**. There is
   nothing to configure.

### Manual

Copy `custom_components/tauron_g13/` into your HA `config/custom_components/`
directory and restart.

## Dashboard

A ready-made dashboard view (current zone + countdown, a −4h…+12h timeline
strip, and the upcoming-zones calendar) is in
**[`examples/dashboard.yaml`](examples/dashboard.yaml)**. Paste it under `views:`
via *Dashboard → Edit → Raw configuration editor*. The timeline strip uses the
[ApexCharts Card](https://github.com/RomRider/apexcharts-card) HACS resource;
the rest is built in.

## Timeline view (past 4h + next 12h)

The calendar entity feeds Home Assistant's built-in **Calendar card** — no
custom frontend needed. The card shows past and upcoming zone blocks as a
timeline:

```yaml
type: calendar
title: Tauron G13 zones
entities:
  - calendar.tauron_g13_zones
initial_view: listWeek
```

For a denser, color-coded strip showing exactly the **last 4 hours and next 12
hours**, use [ApexCharts Card](https://github.com/RomRider/apexcharts-card)
with a timeline (range-bar) series driven by the same calendar:

```yaml
type: custom:apexcharts-card
graph_span: 16h
span:
  start: hour
  offset: "-4h"
experimental:
  color_threshold: true
header:
  show: true
  title: G13 zones (−4h … +12h)
now:
  show: true
  label: now
series:
  - entity: sensor.tauron_g13_zone
    name: Zone
    type: column
    color_threshold:
      - value: 0
        color: "#2e7d32"   # offpeak — green
      - value: 1
        color: "#f9a825"   # mid — amber
      - value: 2
        color: "#c62828"   # peak — red
```

> The ApexCharts example graphs the **current** zone over time using HA history.
> The Calendar card is the zero-dependency way to see future blocks.

## Example automations

Run the dishwasher when energy is cheap:

```yaml
automation:
  - alias: Dishwasher on cheap energy
    trigger:
      - platform: state
        entity_id: binary_sensor.tauron_g13_is_cheap
        to: "on"
    condition:
      - condition: state
        entity_id: input_boolean.dishwasher_ready
        state: "on"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.dishwasher
```

Drop the heat-pump setpoint during the afternoon peak:

```yaml
automation:
  - alias: Ease off heating during peak
    trigger:
      - platform: state
        entity_id: binary_sensor.tauron_g13_is_peak
        to: "on"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.heat_pump
        data:
          temperature: 19
```

## How it works

The core is a pure, fully-tested function `zone_at(dt, is_free_day)` in
[`zones.py`](custom_components/tauron_g13/zones.py). The coordinator schedules a
single timer at the **next** zone boundary (`async_track_point_in_time`), so
entities update exactly when a zone flips — no polling, no drift. DST and the
seasonal flip on Apr 1 / Oct 1 are covered by the test suite.

## Running the tests

```bash
uv run --with holidays --with pytest python -m pytest custom_components/tauron_g13/tests -q
```

## Caveats

- **Zones only, no prices.** If you want złoty cost tracking, pair this with a
  meter integration (e.g. [Tauron AMIplus](https://github.com/PiotrMachowski/Home-Assistant-custom-components-Tauron-AMIplus))
  and wire prices in the Energy Dashboard yourself.
- Zone **hours** are part of the Tauron distribution tariff and change very
  rarely; if Tauron ever restructures G13, the hours in `zones.py` need a code
  update (and the tests make that safe).

## License

MIT — see [LICENSE](LICENSE).
