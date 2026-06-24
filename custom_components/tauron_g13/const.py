"""Constants for the Tauron G13 integration."""

from __future__ import annotations

DOMAIN = "tauron_g13"

# IANA timezone the G13 schedule is defined in. Zones flip on Polish wall-clock
# time regardless of the Home Assistant instance's configured timezone.
TIMEZONE = "Europe/Warsaw"

# Human-friendly labels for the calendar / UI, keyed by Zone value.
ZONE_LABELS = {
    "peak": "Szczyt (peak)",
    "mid": "Przedpołudnie (mid)",
    "offpeak": "Pozaszczytowa (off-peak)",
}

# How far the calendar will synthesize events when asked for an open-ended or
# very large window, as a safety bound (days).
MAX_CALENDAR_DAYS = 31

# Span of the per-hour `timeline` attribute on the zone sensor, used by the
# dashboard strip (last few hours for context + the day ahead for planning).
# Configurable via the options flow; keys live in entry.options.
CONF_TIMELINE_HOURS_BEHIND = "timeline_hours_behind"
CONF_TIMELINE_HOURS_AHEAD = "timeline_hours_ahead"

DEFAULT_TIMELINE_HOURS_BEHIND = 4
DEFAULT_TIMELINE_HOURS_AHEAD = 24

# Upper bounds for the options form. The ahead bound stays under MAX_CALENDAR_DAYS
# so the timeline can never out-reach what the calendar engine will synthesize.
TIMELINE_MAX_HOURS_BEHIND = 24
TIMELINE_MAX_HOURS_AHEAD = 7 * 24
