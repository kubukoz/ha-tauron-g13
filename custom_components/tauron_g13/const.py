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
