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
| `sensor.tauron_g13_zone` | enum sensor | Current zone: `peak` / `mid` / `offpeak`. Attributes: `season`, `is_free_day`, `next_zone`, `next_change`, `minutes_until_change`, and `timeline` (one `{start, zone}` per hour over a configurable window, for the dashboard strip). |
| `binary_sensor.tauron_g13_is_cheap` | binary | On during off-peak — **run** flexible loads now. |
| `binary_sensor.tauron_g13_is_peak` | binary | On during the afternoon peak — **defer** loads. |
| `calendar.tauron_g13_zones` | calendar | Zone blocks as events, past and future — powers the timeline view. |

## Installation

### HACS (custom repository)

1. HACS → ⋮ → **Custom repositories**.
2. Add `https://github.com/kubukoz/ha-tauron-g13`, category **Integration**.
3. Install **Tauron G13**, restart Home Assistant.
4. **Settings → Devices & Services → Add Integration → Tauron G13**. There is
   nothing required to configure.

> **Options.** The integration's **Configure** button lets you set how many
> hours *behind* and *ahead* the `timeline` attribute (used by the dashboard
> strip) reaches around the current hour. Defaults are 4 behind / 24 ahead.

### Manual

Copy `custom_components/tauron_g13/` into your HA `config/custom_components/`
directory and restart.

## Dashboard

A ready-made dashboard view (current zone + countdown, a colored per-hour
timeline strip, and a color-coded upcoming-zones agenda) is in
**[`examples/dashboard.yaml`](examples/dashboard.yaml)**. Paste it under `views:`
via *Dashboard → Edit → Raw configuration editor*.

Two of the cards are HACS frontend resources (the rest is built in):

| Card | Used for | HACS |
|------|----------|------|
| [HTML+Jinja2 Template card](https://github.com/PiotrMachowski/Home-Assistant-Lovelace-HTML-Jinja2-Template-card) (`html-template-card`) | the per-hour SVG strip | required |
| [`atomic-calendar-revive`](https://github.com/totaldebug/atomic-calendar-revive) | the color-coded agenda | required |

Both are in the **default HACS store** — install via *HACS → search by name →
Download* (no custom repository needed), then restart / hard-refresh.

### Timeline strip (HA-style merged-segment bar)

The strip renders directly from the sensor's `timeline` attribute — a
precomputed list of `{start, zone}` per hour — so there's no charting library
and no REST call. It's styled like Home Assistant's own history *timeline* row,
but extends into the future: consecutive same-zone hours are **merged** into one
continuous segment, the exact start time is labelled at every zone change, "now"
is marked, and each segment has a hover tooltip. The window is whatever you set
in the integration's **Options** (default −4h … +24h).

> **Why not the built-in history-graph for the past?** HA excludes the `sensor`
> domain from state colouring (it isn't in `STATE_COLORED_DOMAIN`), so a
> `history-graph` of the zone sensor paints the enum states with an arbitrary
> cycling palette — e.g. off-peak comes out **red**, exactly backwards. This SVG
> strip colours zones semantically (green = cheap, amber = mid, red = peak) for
> both past and future, so it replaces the history card entirely. Increase
> *hours behind* in Options for a longer history tail.

> The card's `content` is a **Jinja2** template (PiotrMachowski's card), not
> JavaScript. **`ignore_line_breaks: true` is required** — otherwise the card
> turns every template newline into a `<br>` and the SVG breaks, so the markup
> is emitted on as few lines as possible with Jinja whitespace control
> (`{%- -%}`). See [`examples/dashboard.yaml`](examples/dashboard.yaml) for the
> full card (segment merging, boundary labels, now-marker, tooltips).

> The "now" marker and boundary labels assume Home Assistant's timezone matches
> the schedule's (Europe/Warsaw). If yours differs, the bars are still correct —
> only the "now" highlight may land on the wrong cell.

### Color-coded agenda

The single `calendar.tauron_g13_zones` entity is listed three times in
[Atomic Calendar Revive](https://github.com/totaldebug/atomic-calendar-revive),
each with an `allowlist` regex matched against the event summary and its own
`color`, so peak / mid / off-peak blocks show in three colors:

```yaml
type: custom:atomic-calendar-revive
name: Upcoming zones
maxDaysToShow: 7
entities:
  - entity: calendar.tauron_g13_zones
    allowlist: '\(peak\)'
    color: '#c62828'   # peak — red
  - entity: calendar.tauron_g13_zones
    allowlist: '\(mid\)'
    color: '#f9a825'   # mid — amber
  - entity: calendar.tauron_g13_zones
    allowlist: '\(off-peak\)'
    color: '#2e7d32'   # offpeak — green
```

> The off-peak summary also contains the substring `peak`, so the peak
> allowlist is anchored on `\(peak\)` and off-peak on `\(off-peak\)`.
>
> Prefer zero HACS dependencies? The built-in **Calendar card**
> (`type: calendar`, `initial_view: listWeek`) shows the same blocks as a plain
> week agenda — just without per-zone colors.

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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the project layout, how to run the
tests, the release process, and the deploy/verify workflow.

## License

MIT — see [LICENSE](LICENSE).
