import { LitElement, html, svg, css, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";

/** One per-hour entry as exposed by `sensor.tauron_g13_zone`'s `timeline` attribute. */
interface TimelineEntry {
  /** ISO-8601 local timestamp aligned to the top of the hour, e.g. 2026-06-24T14:00:00+02:00. */
  start: string;
  /** "offpeak" | "mid" | "peak". */
  zone: string;
}

interface CardConfig {
  type: string;
  entity?: string;
  title?: string;
}

// Minimal shapes from the HA frontend we rely on (avoids a custom-card-helpers dep).
interface HassEntity {
  state: string;
  attributes: Record<string, unknown>;
}
interface HomeAssistant {
  states: Record<string, HassEntity>;
}

const DEFAULT_ENTITY = "sensor.tauron_g13_zone";

// Semantic palette: HA does NOT colour enum sensor states (sensor is excluded
// from STATE_COLORED_DOMAIN), and its default cycling palette is meaningless
// here (off-peak comes out red). Green = cheap, amber = mid, red = peak.
const PALETTE: Record<string, string> = {
  offpeak: "#2e7d32",
  mid: "#f9a825",
  peak: "#c62828",
};
const LABELS: Record<string, string> = {
  offpeak: "off-peak",
  mid: "mid",
  peak: "PEAK",
};

/** A run of consecutive same-zone hours, merged like HA's history timeline row. */
interface Segment {
  zone: string;
  startIdx: number;
  endIdx: number; // inclusive
  startLabel: string; // "HH:MM"
}

@customElement("tauron-g13-timeline")
export class TauronG13TimelineCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private _config?: CardConfig;

  public setConfig(config: CardConfig): void {
    this._config = config;
  }

  public getCardSize(): number {
    return 2;
  }

  static styles = css`
    ha-card {
      padding: 12px 16px 8px;
    }
    .title {
      font-size: var(--ha-card-header-font-size, 1.2rem);
      font-weight: var(--ha-card-header-font-weight, 400);
      margin: 0 0 8px;
    }
    .empty {
      color: var(--secondary-text-color);
      padding: 8px 0;
    }
    svg {
      display: block;
      width: 100%;
      overflow: visible;
    }
    rect {
      shape-rendering: crispEdges;
    }
  `;

  protected render(): TemplateResult | typeof nothing {
    if (!this._config || !this.hass) return nothing;

    const entityId = this._config.entity ?? DEFAULT_ENTITY;
    const stateObj = this.hass.states[entityId];
    const tl = stateObj?.attributes?.timeline as TimelineEntry[] | undefined;
    const title = this._config.title ?? "G13 zones";

    if (!stateObj) {
      return html`<ha-card>
        <p class="title">${title}</p>
        <div class="empty">Entity <code>${entityId}</code> not found.</div>
      </ha-card>`;
    }
    if (!tl || tl.length === 0) {
      return html`<ha-card>
        <p class="title">${title}</p>
        <div class="empty">No timeline data yet.</div>
      </ha-card>`;
    }

    return html`<ha-card>
      <p class="title">${title}</p>
      ${this._renderStrip(tl)}
    </ha-card>`;
  }

  private _renderStrip(tl: TimelineEntry[]): TemplateResult {
    const n = tl.length;
    const w = 100 / n;

    // Merge consecutive same-zone hours into segments.
    const segments: Segment[] = [];
    let startIdx = 0;
    for (let i = 0; i < n; i++) {
      const isLast = i === n - 1;
      const changed = !isLast && tl[i + 1].zone !== tl[i].zone;
      if (changed || isLast) {
        segments.push({
          zone: tl[i].zone,
          startIdx,
          endIdx: i,
          startLabel: hhmm(tl[startIdx].start),
        });
        startIdx = i + 1;
      }
    }

    // Index of the hour containing "now", for the marker.
    const nowHour = new Date().getHours();
    const nowDate = isoDateHour(new Date());
    let nowIdx = -1;
    for (let i = 0; i < n; i++) {
      if (tl[i].start.slice(0, 13) === nowDate) {
        nowIdx = i;
        break;
      }
    }
    // Fallback: match by bare hour if tz strings differ.
    if (nowIdx === -1) {
      for (let i = 0; i < n; i++) {
        if (parseInt(tl[i].start.slice(11, 13), 10) === nowHour) {
          nowIdx = i;
          break;
        }
      }
    }

    // Boundary labels: skip one if it would collide with the previously drawn
    // label (~9 user units wide at this font size).
    let lastLabelX = -99;
    const parts: (TemplateResult | typeof nothing)[] = [];

    for (const seg of segments) {
      const x = seg.startIdx * w;
      const segW = (seg.endIdx - seg.startIdx + 1) * w;
      const fill = PALETTE[seg.zone] ?? PALETTE.offpeak;
      const label = LABELS[seg.zone] ?? seg.zone;

      parts.push(svg`
        <rect x=${x} y="0" width=${segW} height="11" fill=${fill}>
          <title>${label} — from ${seg.startLabel}</title>
        </rect>
        ${
          segW > 8
            ? svg`<text x=${x + segW / 2} y="7.5" font-size="3.2"
                text-anchor="middle" fill="#ffffff"
                style="font-weight:600">${label}</text>`
            : nothing
        }
        <line x1=${x} y1="11" x2=${x} y2="13"
          stroke="var(--divider-color, #888)" stroke-width="0.3" />
      `);

      if (x - lastLabelX >= 9) {
        parts.push(svg`<text x=${x} y="17" font-size="3" text-anchor="middle"
          fill="var(--secondary-text-color, #888)">${seg.startLabel}</text>`);
        lastLabelX = x;
      }
    }

    // Right-edge end label.
    parts.push(svg`<text x="100" y="17" font-size="3" text-anchor="end"
      fill="var(--secondary-text-color, #888)">${hhmm(tl[n - 1].start)}</text>`);

    // Now marker.
    if (nowIdx >= 0) {
      const nx = (nowIdx + 0.5) * w;
      parts.push(svg`
        <line x1=${nx} y1="-1" x2=${nx} y2="12"
          stroke="var(--primary-text-color, #fff)" stroke-width="0.5" />
        <text x=${nx} y="-1.5" font-size="3" text-anchor="middle"
          fill="var(--primary-text-color, #fff)">now</text>
      `);
    }

    return html`<svg
      viewBox="0 0 100 20"
      preserveAspectRatio="none"
      role="img"
      aria-label="G13 zone timeline"
    >
      ${parts}
    </svg>`;
  }
}

/** "2026-06-24T14:00:00+02:00" -> "14:00". */
function hhmm(iso: string): string {
  return iso.slice(11, 16);
}

/** Local Date -> "YYYY-MM-DDTHH" to compare against an ISO entry's slice(0,13). */
function isoDateHour(d: Date): string {
  const p = (x: number) => String(x).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(
    d.getHours()
  )}`;
}

// Register in the custom-card picker.
(window as unknown as { customCards?: unknown[] }).customCards =
  (window as unknown as { customCards?: unknown[] }).customCards || [];
((window as unknown as { customCards: unknown[] }).customCards).push({
  type: "tauron-g13-timeline",
  name: "Tauron G13 Timeline",
  description:
    "Past + future G13 tariff zones as a merged-segment timeline bar.",
  preview: false,
});

// eslint-disable-next-line no-console
console.info(
  "%c TAURON-G13-TIMELINE %c 0.3.0 ",
  "color:white;background:#2e7d32;font-weight:700",
  "color:#2e7d32;background:white"
);
