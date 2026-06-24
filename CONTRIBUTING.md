# Contributing

## Project layout

```
custom_components/tauron_g13/
  zones.py          # pure, HA-free zone engine — the part that must be correct
  coordinator.py    # holiday calendar + no-poll scheduling at zone boundaries
  entity.py         # shared base entity / device
  sensor.py         # sensor.tauron_g13_zone
  binary_sensor.py  # is_cheap / is_peak
  calendar.py       # calendar.tauron_g13_zones (timeline source)
  config_flow.py    # field-less single-instance setup
  tests/            # tests for the pure engine
examples/dashboard.yaml
```

The design principle: **all tariff logic lives in `zones.py` as pure functions**
(no Home Assistant imports), so it can be unit-tested in isolation. The HA-facing
modules are thin wrappers. When fixing a logic bug, add a test in
`tests/test_zones.py` first.

## Running the tests

The engine tests don't need Home Assistant installed — `tests/conftest.py` loads
`zones.py` as a standalone module:

```bash
uv run --with holidays --with pytest python -m pytest custom_components/tauron_g13/tests -q
```

All datetimes in the engine are timezone-aware (Europe/Warsaw). Cover the things
that actually break: season flip (Apr 1 / Oct 1), DST transitions, free-days
(weekends + Polish holidays, incl. the 2025+ Wigilia change), and long holiday
weekends (boundary search must span several days).

## Verifying HA-facing code

The engine is tested, but entity/coordinator/config-flow code can only be fully
validated by loading it in a real Home Assistant instance. Two cheap checks
before pushing:

```bash
# Syntax / import-structure (won't catch wrong HA import *paths*):
python3 -m py_compile custom_components/tauron_g13/*.py
```

When changing a `from homeassistant...` import, verify the path against the
installed HA version — module locations move between releases. (Example: in
HA 2026.x, `DeviceInfo` is in `homeassistant.helpers.device_registry`, **not**
`homeassistant.helpers.device_info`.)

## Releasing

HACS tracks **GitHub releases**, so a fix isn't usable by HACS users until a new
release is tagged. To cut one:

1. Bump `"version"` in `custom_components/tauron_g13/manifest.json`.
2. Commit and push to `main`.
3. Tag a release:
   ```bash
   gh release create v0.1.1 --title v0.1.1 --notes "what changed"
   ```

## Deploying to a live box (and verifying it actually landed)

A recurring gotcha: **HACS may not copy updated files to disk** — clicking
"update" or dismissing the notification is not enough; use HACS → the
integration → ⋮ → **Redownload** and pick the version. After any update, confirm
the files on the box match the repo rather than trusting that they did.

```bash
# On the HA host, files live under /config/custom_components/tauron_g13/

# 1. Confirm a specific fix landed:
grep -n device_ /config/custom_components/tauron_g13/entity.py
#   -> must show device_registry, not device_info

# 2. Compare every file to a local checkout (run from your checkout):
for f in custom_components/tauron_g13/*.py; do
  l=$(sha256sum "$f" | cut -d' ' -f1)
  r=$(ssh root@homeassistant.local "sha256sum /config/$f 2>/dev/null" | cut -d' ' -f1)
  [ "$l" = "$r" ] && echo "OK   $f" || echo "DIFF $f"
done

# 3. Clear stale bytecode after editing files directly:
rm -rf /config/custom_components/tauron_g13/__pycache__
```

Then **fully restart** Home Assistant (Settings → System → Restart) — a reload
does not clear HA's per-process platform-import cache, so a failed import stays
cached until the process restarts.

> Note: the HA OS host is a minimal (busybox-ish) environment. `sha256sum` and
> `md5sum` exist; `shasum` does not.
