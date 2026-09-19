/* =========================================================================
 * Haiven Native — hand-written Lovelace card library
 * =========================================================================
 *
 * Same architecture as Willow Bank's wb2-cards.js: one file, plain custom
 * elements with shadow DOM, no framework, no build step, no card-mod.
 *
 * SOURCE lives at www-src/haiven-cards.js in this repo.
 * DEPLOYS to /config/www/haiven-cards.js on the box, which is gitignored
 * there, so a git checkout does NOT deploy it. Copying it is the whole deploy:
 *
 *   node --check www-src/haiven-cards.js
 *   tar czf - --no-xattrs -C www-src haiven-cards.js | ssh <ha-host> 'tar xzf - -C /config/www'
 *
 * No restart, no version bump, no UI. haiven-loader.js revalidates this file
 * on every dashboard load and imports it under its current ETag; see the
 * comment at the top of that file for why the manual bump had to go.
 *
 * THEMING BY INHERITANCE
 * Nothing here hardcodes a colour. THEME maps the card variables onto the
 * Haiven theme's tokens, which carry measured contrast values, so changing
 * themes/haiven.yaml reflows every card with no JS involved. Fallbacks are the
 * light-mode values so the cards stay legible under a non-Haiven theme.
 *
 * RULES
 *  - A dash means no data. A zero means zero. Never render one as the other.
 *  - Status colour is never the only channel: it always carries a word too.
 *  - A tick is impossible to render while coverage is incomplete.
 * ====================================================================== */

const THEME = `
  :host{
    --ground:var(--haiven-ground, var(--primary-background-color, #F7F5F1));
    --surface:var(--haiven-surface, var(--card-background-color, #FFFFFF));
    --surface-2:var(--haiven-surface-2, var(--secondary-background-color, #EFEBE4));
    --ink:var(--haiven-ink, var(--primary-text-color, #1A1815));
    --muted:var(--haiven-muted, var(--secondary-text-color, #6B6560));
    --faint:var(--haiven-faint, #786F66);
    --line:var(--haiven-line, var(--divider-color, #E2DDD5));
    --accent:var(--haiven-accent, var(--primary-color, #1F5459));
    --good:var(--haiven-good, var(--success-color, #2E6B45));
    --warn:var(--haiven-warning, var(--warning-color, #9A5B12));
    --crit:var(--haiven-alert, var(--error-color, #A32B22));
    --good-wash:var(--haiven-good-wash, #E4EDE6);
    --warn-wash:var(--haiven-warning-wash, #F6EDE1);
    --crit-wash:var(--haiven-alert-wash, #F7E8E6);
    --on-status:var(--haiven-on-status, #FFFFFF);
    --room-kitchen:var(--haiven-room-kitchen, #11393F);
    --room-bedroom:var(--haiven-room-bedroom, #4C569A);
    --room-bathroom:var(--haiven-room-bathroom, #B2719A);
    font-family:var(--paper-font-body1_-_font-family, -apple-system,"SF Pro Text",system-ui,sans-serif);
    display:block;
  }
  *{box-sizing:border-box}
  .mono{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
  .lbl{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint);font-weight:600}
`;

/* ------------------------------- helpers -------------------------------- */

// The whole point of the dash rule. Anything missing renders as an em dash,
// never as 0 and never as a blank, so "0 bathroom visits" and "we cannot see
// the bathroom" can never look the same on screen.
const DASH = "—";
const isUn = (e) => !e || e.state === "unavailable" || e.state === "unknown" || e.state === "";
const num = (v) => { const n = Number(v); return Number.isFinite(n) ? n : null; };
const txt = (hass, id, fallback = DASH) => {
  const e = hass && hass.states[id];
  return isUn(e) ? fallback : e.state;
};
// A number without its unit is a different number. Anything that prints a
// state prints the unit the entity declares, unless the card config supplies
// its own wording.
const unit = (e) => (e && e.attributes && e.attributes.unit_of_measurement) || "";
const withUnit = (e) => (isUn(e) ? DASH : (unit(e) ? `${e.state} ${unit(e)}` : e.state));

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
));

// Age of an entity's last state change, in minutes. null when we cannot say,
// which is different from 0 and must stay different all the way to the screen.
const ageMin = (hass, id) => {
  const e = hass && hass.states[id];
  if (!e || !e.last_changed) return null;
  return (Date.now() - new Date(e.last_changed).getTime()) / 60000;
};

const relTime = (mins) => {
  if (mins === null) return DASH;
  if (mins < 1) return "just now";
  if (mins < 60) return `${Math.round(mins)} min ago`;
  const h = Math.floor(mins / 60), m = Math.round(mins % 60);
  if (h < 24) return m ? `${h}h ${m}m ago` : `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
};

const fmtClock = (t) => new Date(t).toLocaleTimeString("en-GB",
  { hour: "2-digit", minute: "2-digit" });

// "3h 20m" / "45m". Rounded to the minute, because the band is sampled into
// buckets and pretending to seconds would be a precision the data has not got.
const durStr = (mins) => {
  const m = Math.round(mins);
  if (m < 60) return `${m}m`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
};

const clockOf = (hass, id) => {
  const e = hass && hass.states[id];
  if (!e || !e.last_changed) return DASH;
  return new Date(e.last_changed).toLocaleTimeString("en-GB",
    { hour: "2-digit", minute: "2-digit" });
};

/* --------------------------- coverage model ------------------------------
 * Four states, not two, because they mean different things to a carer and a
 * single "offline" flattens them:
 *   live    reporting, and changed recently enough to believe
 *   dead    present but unavailable/unknown
 *   absent  the entity is not in the state machine at all
 *   stuck   present, plausible, and has not changed in longer than it should
 * `stuck` is the dangerous one: a latched presence sensor actively asserts that
 * someone is there, which satisfies every no-movement rule that reads it.
 * Thresholds mirror the ones already in sensor.sensor_health_status.
 * ---------------------------------------------------------------------- */

// `entity` is the health signal (what proves the sensor is alive). `motion` is
// the on/off signal used for ribbons and triangulation. They are the same
// entity for every room by default; set them separately in ROOMS if your
// kitchen sensor reports health and motion through different entities.
const ROOMS = [
  { key: "kitchen",  name: "Kitchen",  entity: "event.kitchen_motion",                    motion: "event.kitchen_motion",                    staleH: 12 },
  { key: "bedroom",  name: "Bedroom",  entity: "binary_sensor.haiven_bedroom_occupancy",  motion: "binary_sensor.haiven_bedroom_occupancy",  staleH: 18 },
  { key: "bathroom", name: "Bathroom", entity: "binary_sensor.haiven_bathroom_motion",    motion: "binary_sensor.haiven_bathroom_motion",    staleH: 12 },
];

function coverageOf(hass, room) {
  const e = hass && hass.states[room.entity];
  if (!e) return { state: "absent", mins: null };
  if (isUn(e)) return { state: "dead", mins: ageMin(hass, room.entity) };
  const mins = ageMin(hass, room.entity);
  if (mins !== null && mins > room.staleH * 60) return { state: "stuck", mins };
  return { state: "live", mins };
}

function coverage(hass) {
  const rooms = ROOMS.map((r) => ({ ...r, ...coverageOf(hass, r) }));
  const live = rooms.filter((r) => r.state === "live");
  const bad = rooms.filter((r) => r.state !== "live");
  return { rooms, live: live.length, total: rooms.length, bad };
}

const COVER_COLOUR = { live: "var(--good)", dead: "var(--faint)", absent: "var(--warn)", stuck: "var(--crit)" };

/* Sentence for the header. Deliberately says what is wrong and names the room,
 * because "2 of 3" alone tells a carer nothing about which safety net is off. */
function coverageLine(c) {
  if (c.live === c.total) return `${c.total} of ${c.total} rooms`;
  const names = c.bad.map((r) => r.name.toLowerCase());
  const list = names.length === 1 ? names[0]
    : names.slice(0, -1).join(", ") + " and " + names[names.length - 1];
  const stuck = c.bad.filter((r) => r.state === "stuck").map((r) => r.name.toLowerCase());
  if (stuck.length) return `${c.live} of ${c.total} rooms, ${stuck.join(" and ")} stuck`;
  return `${c.live} of ${c.total} rooms, ${list} not reporting`;
}

/* ------------------------------- presence -------------------------------
 * Whether she is in the house at all. This has to be read BEFORE anything is
 * inferred from the sensors, because every rule in the system is a rule about
 * a house she is inside: "no kitchen activity for three hours" is an alarm if
 * she is home and meaningless if she is at her sister's. Away is not a good
 * state or a bad one, so it gets the accent, never a status colour.
 * --------------------------------------------------------------------- */

const HOME_ENTITY = "binary_sensor.elderly_person_home";
const WHERE_ENTITY = "sensor.elderly_person_location";

function presence(hass) {
  const e = hass && hass.states[HOME_ENTITY];
  const w = hass && hass.states[WHERE_ENTITY];
  const where = isUn(w) ? null : w.state;
  if (isUn(e)) return { known: false, home: null, word: "Presence unknown", where };
  const home = e.state === "on";
  return { known: true, home, word: home ? "Home" : (where && !/home/i.test(where) ? where : "Out"), where };
}

/* ------------------------------ care circle -----------------------------
 * One definition of who is in the circle, used by both the Home summary and
 * the Circle screen, so the two cannot drift apart. Override with `people:`
 * in a card's config when the roster differs.
 *
 * "Nearest" is a claim about now, so a position nobody has updated for hours
 * can never take the top slot from a fresh one however small its number is.
 * A tracker that stopped reporting five days ago still says "60 km" with
 * complete confidence, and someone deciding whether to drive over will
 * believe it.
 * --------------------------------------------------------------------- */

const CIRCLE = [
  { location: "sensor.primary_contact_location",   distance: "sensor.primary_contact_distance",   fallback: "input_text.contact_1_name" },
  { location: "sensor.secondary_contact_location", distance: "sensor.secondary_contact_distance", fallback: "input_text.contact_2_name" },
];

// Age of a contact's last position fix, in minutes. The location state is a
// word ("Away") that can sit unchanged for days while the phone reports every
// few minutes, so the age comes from the tracker timestamp the template puts
// in last_updated, and only falls back to the label's last change.
const seenMin = (hass, id) => {
  const e = hass && hass.states[id];
  const t = e && e.attributes ? Date.parse(e.attributes.last_updated) : NaN;
  return Number.isNaN(t) ? ageMin(hass, id) : (Date.now() - t) / 60000;
};

function circleOf(hass, cfg = {}) {
  const staleMin = Number(cfg.stale_hours || 6) * 60;
  return (cfg.people || CIRCLE).map((p) => {
    const l = hass.states[p.location];
    const d = hass.states[p.distance];
    const who = (l && l.attributes && l.attributes[p.name_attr || "contact_name"])
      || txt(hass, p.fallback, "");
    const age = seenMin(hass, p.location);
    return {
      who,
      where: isUn(l) ? null : l.state,
      km: isUn(d) ? null : num(d.state),
      dist: d,
      age,
      stale: age !== null && age > staleMin,
      missing: isUn(l),
      near: !isUn(l) && /home|nearby|near/i.test(l.state),
    };
  }).filter((p) => p.who && p.who !== DASH);
}

// Fresh before stale, then closest first. A missing distance sorts last
// rather than sorting as zero.
const byNearest = (a, b) => {
  const rank = (p) => (p.missing ? 2 : p.stale ? 1 : 0);
  if (rank(a) !== rank(b)) return rank(a) - rank(b);
  if (a.km === null) return b.km === null ? 0 : 1;
  if (b.km === null) return -1;
  return a.km - b.km;
};

// Same push-state dance the nav does, so an in-app link does not reload the
// whole frontend.
function goTo(path) {
  history.pushState(null, "", path);
  window.dispatchEvent(new CustomEvent("location-changed", { bubbles: true, composed: true }));
}

/* ---------------------------- base element ------------------------------
 * Sig-guard: a card only re-renders when something it actually draws has
 * changed. Without it every hass push rebuilds the shadow root, which throws
 * away scroll position and any in-progress interaction.
 * --------------------------------------------------------------------- */

class HaivenCard extends HTMLElement {
  setConfig(config) { this._config = config || {}; this._sig = null; }
  getCardSize() { return 3; }
  set hass(hass) {
    this._hass = hass;
    const sig = this.signature(hass);
    if (sig === this._sig) return;
    this._sig = sig;
    this.render(hass);
  }
  get hass() { return this._hass; }
  signature() { return Math.random(); }
  render() {}
  paint(html) {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `<style>${THEME}${this.css || ""}</style>${html}`;
  }
}

/* ------------------------------ haiven-status ---------------------------
 * The screen's answer to "is she all right, and does the system actually
 * know?". The AI summary is the headline; coverage sits directly under it so
 * the two are read together. A tick is impossible while coverage is short.
 * --------------------------------------------------------------------- */

class HaivenStatus extends HaivenCard {
  get css() { return `
    .card{background:var(--surface);border:1px solid var(--line);padding:18px 18px 16px;display:flex;flex-direction:column;gap:13px}
    .top{display:flex;justify-content:space-between;align-items:center;gap:12px}
    .badge{display:flex;align-items:center;gap:8px}
    .dot{width:9px;height:9px;border-radius:50%;flex:0 0 auto}
    .dot.sq{border-radius:2px}
    .dot.di{border-radius:1px;transform:rotate(45deg)}
    .word{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;font-weight:700}
    .when{font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint)}
    .when.asking{color:var(--accent);font-weight:700}
    .card.tappable{cursor:pointer}
    .card.tappable:hover{background:var(--surface-2)}
    .card.tappable:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
    .here{display:flex;align-items:center;gap:6px;font-size:10.5px;letter-spacing:.1em;
          text-transform:uppercase;font-weight:700}
    .here .p{width:7px;height:7px;border-radius:50%;flex:0 0 auto}
    .meta{display:flex;align-items:center;gap:12px;flex:0 0 auto}
    .summary{font-size:17px;line-height:1.45;color:var(--ink);margin:0;text-wrap:pretty}
    .summary.none{color:var(--muted)}
    .cover{display:flex;align-items:center;gap:9px;padding-top:2px}
    .dots{display:flex;gap:4px}
    .cover .t{font-size:13px;color:var(--muted)}
  `; }

  signature(hass) {
    const c = coverage(hass);
    return [
      this._asking ? "asking" : "",
      txt(hass, this._config.summary_entity || "input_text.current_summary", ""),
      c.rooms.map((r) => r.state).join(","),
      txt(hass, "sensor.elderly_care_status", ""),
      txt(hass, HOME_ENTITY, ""), txt(hass, WHERE_ENTITY, ""),
      Math.round((ageMin(hass, "sensor.activity_data") || 0) / 5),
    ].join("|");
  }

  render(hass) {
    const c = coverage(hass);
    const status = txt(hass, "sensor.elderly_care_status", "unknown");
    const complete = c.live === c.total;

    const p = presence(hass);

    // Severity collapses five internal levels to three at the surface, and
    // incomplete coverage can only ever hold it back, never let it through.
    let sev = "good", word = "All well", shape = "";
    if (["caution"].includes(status)) { sev = "warn"; word = "Worth checking"; shape = "sq"; }
    if (["concern", "critical"].includes(status)) { sev = "crit"; word = "Needs attention"; shape = "di"; }
    if (c.bad.some((r) => r.state === "stuck")) { sev = "crit"; word = "Sensor stuck"; shape = "di"; }
    else if (!complete && sev === "good") { sev = "warn"; word = "Partial cover"; shape = "sq"; }

    // Out of the house, a quiet kitchen is the expected reading, not a
    // symptom. Anything the sensors would otherwise be shouting about is
    // demoted, and the headline says where she is instead.
    if (p.known && !p.home) { sev = "away"; word = "Out"; shape = "sq"; }

    const colour = { good: "var(--good)", warn: "var(--warn)", crit: "var(--crit)",
                     away: "var(--accent)" }[sev];
    const pColour = !p.known ? "var(--faint)" : p.home ? "var(--good)" : "var(--accent)";
    const summaryId = this._config.summary_entity || "input_text.current_summary";
    const s = hass.states[summaryId];
    const written = s && s.last_changed
      ? new Date(s.last_changed).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })
      : null;

    const body = isUn(s)
      ? `<p class="summary none">No summary yet. ${DASH}</p>`
      : `<p class="summary">${esc(s.state)}</p>`;

    // Tapping the summary asks for a new one. The refresh automation is
    // triggered by the button's state change, and the button's state is a
    // timestamp, so pressing it twice in a row genuinely fires twice.
    const refresh = this._config.refresh_entity || "input_button.refresh_summary";
    const canAsk = !!hass.states[refresh];

    const dots = c.rooms.map((r) =>
      `<div class="dot" style="background:${COVER_COLOUR[r.state]}" title="${esc(r.name)}: ${r.state}"></div>`
    ).join("");

    this.paint(`
      <div class="card">
        <div class="top">
          <div class="badge">
            <div class="dot ${shape}" style="background:${colour}"></div>
            <div class="word" style="color:${colour}">${esc(word)}</div>
          </div>
          <div class="meta">
            <div class="here" style="color:${pColour}">
              <div class="p" style="background:${pColour}"></div>${esc(p.word)}
            </div>
            ${this._asking ? `<div class="when asking">Thinking&hellip;</div>`
                            : (written ? `<div class="when">${written}</div>` : "")}
          </div>
        </div>
        ${body}
        <div class="cover">
          <div class="dots">${dots}</div>
          <div class="t">${esc(coverageLine(c))} &middot; seen ${esc(relTime(ageMin(hass, "sensor.activity_data")))}</div>
        </div>
      </div>
    `);

    if (!canAsk) return;
    const card = this.shadowRoot.querySelector(".card");
    card.classList.add("tappable");
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    card.setAttribute("aria-label", "Ask for a new summary");
    const ask = () => {
      if (this._asking) return;
      this._asking = true;
      this._sig = null;                     // force the "Thinking" repaint
      this.render(this._hass);
      this._hass.callService("input_button", "press", { entity_id: refresh });
      // The AI call takes several seconds and the card repaints when the
      // summary lands. This only clears a stuck spinner if it never does.
      clearTimeout(this._askTimer);
      this._askTimer = setTimeout(() => {
        this._asking = false; this._sig = null; this.render(this._hass);
      }, 45000);
    };
    card.addEventListener("click", ask);
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); ask(); }
    });
    // A new summary arriving is the real end of the wait.
    if (this._asking && written && written !== this._askedAt) this._asking = false;
    this._askedAt = written;
  }
}

/* ------------------------------ haiven-facts ----------------------------
 * Three figures, facts only. Any judgement about whether a number is good
 * belongs in the summary prose above, never in a tile.
 * --------------------------------------------------------------------- */

class HaivenFacts extends HaivenCard {
  get css() { return `
    .grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line)}
    .cell{background:var(--surface);padding:14px 12px;display:flex;flex-direction:column;gap:5px;min-width:0}
    .v{font-size:19px;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .v.long{font-size:15px}
    .v.none{color:var(--faint)}
    .sub{font-size:11.5px;color:var(--faint);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  `; }

  signature(hass) {
    return (this._config.cells || []).map((c) => txt(hass, c.entity, "")).join("|");
  }

  render(hass) {
    const cells = (this._config.cells || []).slice(0, 3).map((c) => {
      const e = hass.states[c.entity];
      const missing = isUn(e);
      // `unit: false` where the sub-label already carries it, so a third of a
      // phone screen does not have to hold "136 triggers" above "triggers a
      // day". Anything still long steps down a size rather than bulging the
      // cell or pushing its neighbours out of line.
      const value = missing ? DASH : (c.unit === false ? e.state : withUnit(e));
      return `<div class="cell">
        <div class="lbl">${esc(c.label || "")}</div>
        <div class="v mono ${missing ? "none" : ""} ${String(value).length > 8 ? "long" : ""}">${esc(value)}</div>
        <div class="sub">${esc(missing ? "not reporting" : (c.sub || ""))}</div>
      </div>`;
    }).join("");
    this.paint(`<div class="grid">${cells}</div>`);
  }
}

/* ------------------------------ haiven-rooms ----------------------------
 * One row per room, always all three, so a missing room is a visible gap
 * rather than a shorter list. Each row carries both a relative and an
 * absolute time: the relative one answers "is this recent", the absolute one
 * is what you read out on the phone to someone else.
 * --------------------------------------------------------------------- */

class HaivenRooms extends HaivenCard {
  get css() { return `
    .wrap{background:var(--surface);border:1px solid var(--line)}
    .row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 16px;min-height:46px;border-bottom:1px solid var(--surface-2)}
    .row:last-child{border-bottom:0}
    .l{display:flex;align-items:center;gap:11px;min-width:0}
    .dot{width:7px;height:7px;border-radius:50%;flex:0 0 auto}
    .dot.sq{border-radius:2px}
    .dot.di{border-radius:1px;transform:rotate(45deg)}
    .n{font-size:15px;color:var(--ink)}
    .r{display:flex;align-items:baseline;gap:9px;flex:0 0 auto}
    .rel{font-size:13px;color:var(--faint)}
    .abs{font-size:13.5px;color:var(--muted)}
    .fault{font-size:12.5px;color:var(--crit)}
  `; }

  signature(hass) {
    return coverage(hass).rooms.map((r) => `${r.state}:${Math.round((r.mins || 0) / 2)}`).join("|");
  }

  render(hass) {
    const rows = coverage(hass).rooms.map((r) => {
      const shape = r.state === "stuck" ? "di" : r.state === "absent" ? "sq" : "";
      let right;
      if (r.state === "absent") right = `<div class="fault">missing from Home Assistant</div>`;
      else if (r.state === "dead") right = `<div class="rel">${DASH}</div><div class="abs">not reporting</div>`;
      else if (r.state === "stuck") right = `<div class="fault">unchanged ${relTime(r.mins).replace(" ago", "")} &mdash; stuck</div>`;
      else right = `<div class="rel">${esc(relTime(r.mins))}</div><div class="abs mono">${esc(clockOf(hass, r.entity))}</div>`;
      return `<div class="row">
        <div class="l"><div class="dot ${shape}" style="background:${COVER_COLOUR[r.state]}"></div><div class="n">${esc(r.name)}</div></div>
        <div class="r">${right}</div>
      </div>`;
    }).join("");
    this.paint(`<div class="wrap">${rows}</div>`);
  }
}

/* ----------------------------- haiven-section ---------------------------
 * Replaces HA's oversized vertical-stack titles, and exists as a component
 * rather than as card-mod ::before content, which is how the three headings
 * in the old dashboard were built and why they vanish if card-mod does.
 * --------------------------------------------------------------------- */

class HaivenSection extends HaivenCard {
  get css() { return `.s{padding:16px 2px 6px}`; }
  signature() { return this._config.title || ""; }
  render() { this.paint(`<div class="s"><div class="lbl">${esc(this._config.title || "")}</div></div>`); }
}


/* ------------------------------- haiven-tabs ----------------------------
 * Sub-tabs inside a single Lovelace view. Home Assistant has no such thing:
 * its only navigation unit is a whole view, so "Today / Patterns / Nights"
 * would otherwise be three top-level tabs competing with Home and Alerts.
 *
 * Children are real Lovelace cards built through loadCardHelpers(), so
 * anything valid in a view is valid in a tab, Haiven cards included. Every
 * child is kept alive and fed hass whether or not its tab is showing, so
 * switching is instant and a chart never re-fetches on the way back.
 * --------------------------------------------------------------------- */

class HaivenTabs extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._tabs = Array.isArray(this._config.tabs) ? this._config.tabs : [];
    if (!this._tabs.length) throw new Error("haiven-tabs: needs at least one tab");
    this._key = "haiven-tabs:" + (this._config.id || this._tabs.map((t) => t.name).join("/"));
    this._active = 0;
    const want = this._remembered() || this._config.default_tab;
    const i = this._tabs.findIndex((t) => t.name === want);
    if (i >= 0) this._active = i;
    this._panes = [];
    this._kids = [];
    this._built = false;
  }

  getCardSize() { return 12; }

  // Storage can throw outright in a private window, not just come back empty,
  // so both directions are guarded and a failure silently means "no memory".
  _remembered() { try { return localStorage.getItem(this._key); } catch (e) { return null; } }
  _remember(name) { try { localStorage.setItem(this._key, name); } catch (e) { /* no memory */ } }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) { this._build(); return; }
    for (const kid of this._kids) kid.hass = hass;
  }

  async _build() {
    this._built = true;                       // set first: _build is async and
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });   // hass pushes
    const helpers = await window.loadCardHelpers();              // keep arriving

    const bar = document.createElement("div");
    bar.className = "bar";
    const panes = document.createElement("div");
    panes.className = "panes";

    this._tabs.forEach((tab, idx) => {
      const b = document.createElement("button");
      b.className = "tab";
      b.type = "button";
      b.textContent = tab.name || `Tab ${idx + 1}`;
      b.addEventListener("click", () => this._select(idx));
      bar.appendChild(b);

      const pane = document.createElement("div");
      pane.className = "pane";
      for (const cfg of (tab.cards || [])) {
        const el = helpers.createCardElement(cfg);
        if (this._hass) el.hass = this._hass;
        this._kids.push(el);
        pane.appendChild(el);
      }
      panes.appendChild(pane);
      this._panes.push(pane);
    });

    const style = document.createElement("style");
    style.textContent = THEME + `
      .bar{display:flex;gap:0;border-bottom:1px solid var(--line);background:var(--surface);
           overflow-x:auto;scrollbar-width:none}
      .bar::-webkit-scrollbar{display:none}
      .tab{appearance:none;background:none;border:0;border-bottom:2px solid transparent;
           padding:13px 15px 11px;font:inherit;font-size:12px;letter-spacing:.09em;
           text-transform:uppercase;font-weight:600;color:var(--faint);cursor:pointer;
           white-space:nowrap;flex:0 0 auto}
      .tab:hover{color:var(--muted)}
      .tab[aria-current="true"]{color:var(--accent);border-bottom-color:var(--accent)}
      .tab:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
      .panes{display:block}
      .pane{display:none;flex-direction:column;gap:10px;padding-top:10px}
      .pane.on{display:flex}
    `;
    this.shadowRoot.replaceChildren(style, bar, panes);
    this._bar = bar;
    this._paint();
  }

  _select(idx) {
    this._active = idx;
    this._remember(this._tabs[idx].name);
    this._paint();
  }

  _paint() {
    if (!this._bar) return;
    [...this._bar.children].forEach((b, i) =>
      b.setAttribute("aria-current", String(i === this._active)));
    this._panes.forEach((p, i) => p.classList.toggle("on", i === this._active));
  }
}

/* ------------------------------ haiven-ribbon ---------------------------
 * ONE continuous band showing which room she was in, not three lanes of
 * on/off blocks. The lanes version was technically accurate and useless to
 * look at: three rows of confetti, because a PIR fires in one-minute pulses
 * and drawing every pulse draws the sensor's behaviour rather than hers.
 *
 * The window is sampled into buckets and each bucket takes the room with the
 * most activity in it, so adjacent pulses merge into one run and you see
 * "kitchen all morning" instead of forty separate ticks. Runs of the same
 * room then merge again, which is what makes the band continuous.
 *
 * Reads the recorder directly over the WebSocket rather than through a
 * template sensor, the only way to get sub-minute resolution and more than
 * the 48h the log script keeps.
 *
 * Where no sensor fired the band is empty, and where the recorder could not
 * see it is hatched. Those two must never look the same: one means she was
 * still, the other means we do not know. That is the dash rule applied to a
 * chart.
 * --------------------------------------------------------------------- */

const NIGHT_FROM = 21, NIGHT_TO = 6;

class HaivenRibbon extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._hours = Number(this._config.hours) || 24;
    this._mode = this._config.mode || "band";      // "band" | "lanes"
    this._buckets = Number(this._config.buckets || 200);
    this._lanes = this._config.lanes ||
      ROOMS.map((r) => ({ name: r.name, entity: r.motion, health: r.entity, key: r.key }));
    this._hist = null;
    this._err = null;
  }

  getCardSize() { return 5; }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._draw();
      this._load();
      // Two minutes. The window slides continuously but nothing on a 24h
      // ribbon is legible at finer grain than that, and the recorder query is
      // not free.
      this._timer = setInterval(() => this._load(), 120000);
      return;
    }
    // Any lane flipping on or off makes the drawing stale immediately.
    const sig = this._lanes.map((l) => {
      const e = hass.states[l.entity];
      return e ? e.state : "?";
    }).join("|");
    if (sig !== this._sig) { this._sig = sig; this._load(); }
  }

  disconnectedCallback() { clearInterval(this._timer); }

  async _load() {
    const hass = this._hass;
    if (!hass || this._busy) return;
    this._busy = true;
    const end = new Date();
    const start = new Date(end.getTime() - this._hours * 3600000);
    try {
      const res = await hass.callWS({
        type: "history/history_during_period",
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        entity_ids: this._lanes.map((l) => l.entity),
        minimal_response: true,
        no_attributes: true,
        significant_changes_only: false,
      });
      this._hist = res || {};
      this._err = null;
    } catch (e) {
      // Say so on the card. A silent failure here draws three empty lanes,
      // which reads as "she did not move all day".
      this._err = (e && e.message) ? e.message : "history unavailable";
      this._hist = null;
    }
    this._busy = false;
    this._start = start.getTime();
    this._end = end.getTime();
    this._draw();
  }

  // Recorder rows -> [start, end] pairs clipped to the window. An interval
  // still open at the right edge runs to now rather than being dropped.
  //
  // Segments separated by less than one pixel of ribbon are merged. Over a
  // week the kitchen alone produces a couple of thousand on/off pairs, and
  // drawing each as its own element is thousands of sub-pixel divs that
  // render as one solid bar anyway. Merging keeps the DOM bounded and changes
  // nothing that was visible.
  _segments(rows, start, end) {
    const segs = [];
    let open = null;
    for (const r of (rows || [])) {
      const t = (r.lu || r.last_updated || 0) * 1000;
      const on = String(r.s !== undefined ? r.s : r.state) === "on";
      if (on) { if (open === null) open = t; }
      else if (open !== null) { segs.push([open, t]); open = null; }
    }
    if (open !== null) segs.push([open, end]);

    const clipped = segs
      .map(([a, b]) => [Math.max(a, start), Math.min(b, end)])
      .filter(([a, b]) => b > a)
      .sort((x, y) => x[0] - y[0]);

    const grain = (end - start) / 600;
    const out = [];
    for (const seg of clipped) {
      const last = out[out.length - 1];
      if (last && seg[0] - last[1] < grain) last[1] = Math.max(last[1], seg[1]);
      else out.push([seg[0], seg[1]]);
    }
    return out;
  }

  // Periods the recorder could not see. The coverage model only knows about
  // NOW, so without this a week-long ribbon draws six dead days and one live
  // one as though she simply had not moved: exactly the confusion the dash
  // rule exists to prevent, transplanted into a chart. Anything recorded as
  // unavailable or unknown is hatched, and so is the run before the first row
  // if the entity was not being recorded at the start of the window.
  _blind(rows, start, end) {
    const out = [];
    const list = rows || [];
    if (!list.length) return [[start, end]];
    const first = (list[0].lu || list[0].last_updated || 0) * 1000;
    if (first > start) out.push([start, Math.min(first, end)]);
    let open = null;
    for (const r of list) {
      const t = (r.lu || r.last_updated || 0) * 1000;
      const v = String(r.s !== undefined ? r.s : r.state);
      const gone = v === "unavailable" || v === "unknown";
      if (gone) { if (open === null) open = t; }
      else if (open !== null) { out.push([open, t]); open = null; }
    }
    if (open !== null) out.push([open, end]);
    return out
      .map(([a, b]) => [Math.max(a, start), Math.min(b, end)])
      .filter(([a, b]) => b > a);
  }

  // How much of [a,b] the intervals cover. Used to decide which room owns a
  // bucket when two sensors overlap, which happens constantly: the mmWave
  // latches on in the bedroom while the bathroom PIR fires next door.
  _cover(segs, a, b) {
    let t = 0;
    for (const [x, y] of segs) {
      const lo = Math.max(x, a), hi = Math.min(y, b);
      if (hi > lo) t += hi - lo;
    }
    return t;
  }

  // The window as a sequence of runs: {key, a, b}. `key` is a room key, or
  // "quiet" for nothing firing, or "blind" for nothing being recorded.
  _band(start, end) {
    const n = this._buckets;
    const step = (end - start) / n;
    const lanes = this._lanes.map((l) => ({
      key: l.key,
      segs: this._segments(this._hist[l.entity], start, end),
      dark: this._blind(this._hist[l.entity], start, end),
    }));

    const cells = [];
    for (let i = 0; i < n; i++) {
      const a = start + i * step, b = a + step;
      let win = null, best = 0;
      for (const l of lanes) {
        const c = this._cover(l.segs, a, b);
        if (c > best) { best = c; win = l.key; }
      }
      if (win) { cells.push(win); continue; }
      // Nothing fired. Only call it blind if EVERY room was unrecorded for
      // most of the bucket; one dead sensor does not make the moment unknown.
      const dark = lanes.every((l) => this._cover(l.dark, a, b) > step * 0.5);
      cells.push(dark ? "blind" : "quiet");
    }

    const runs = [];
    for (let i = 0; i < n; i++) {
      const last = runs[runs.length - 1];
      if (last && last.key === cells[i]) last.b = start + (i + 1) * step;
      else runs.push({ key: cells[i], a: start + i * step, b: start + (i + 1) * step });
    }

    // Bridge short quiet gaps between two runs of the SAME room. A PIR drops
    // between pulses, so without this the kitchen renders as stripes: she is
    // standing at the sink and the chart says she left and came back eleven
    // times. A four-minute gap flanked by kitchen on both sides IS kitchen.
    //
    // Only same-room gaps are bridged. A quiet gap between two DIFFERENT
    // rooms is her walking between them, and inventing a room to fill it
    // would be making up where she was.
    const bridge = Number(this._config.bridge_mins || 12) * 60000;
    for (let i = 1; i < runs.length - 1; i++) {
      const a = runs[i - 1], q = runs[i], b = runs[i + 1];
      if (q.key !== "quiet" || q.b - q.a > bridge) continue;
      if (a.key !== b.key || a.key === "quiet" || a.key === "blind") continue;
      q.key = a.key;
    }

    const merged = [];
    for (const r of runs) {
      const last = merged[merged.length - 1];
      if (last && last.key === r.key) last.b = r.b;
      else merged.push(r);
    }
    return merged;
  }

  // Shaded 21:00-06:00 bands, walked hour by hour so a window spanning the
  // boundary shades correctly instead of guessing from the window's midpoint.
  _nightBands(start, end) {
    const bands = [];
    let cur = null;
    const h0 = new Date(start); h0.setMinutes(0, 0, 0);
    for (let t = h0.getTime(); t <= end; t += 3600000) {
      const h = new Date(t).getHours();
      const night = h >= NIGHT_FROM || h < NIGHT_TO;
      if (night && cur === null) cur = Math.max(t, start);
      if (!night && cur !== null) { bands.push([cur, Math.min(t, end)]); cur = null; }
    }
    if (cur !== null) bands.push([cur, end]);
    return bands.filter(([a, b]) => b > a);
  }

  // Past two days every tick is a midnight, so "00" six times over tells you
  // nothing. Long windows get weekday names instead.
  _ticks(start, end) {
    const out = [];
    const step = this._hours <= 12 ? 2 : this._hours <= 36 ? 6 : 24;
    const asDays = this._hours > 48;
    const d = new Date(start);
    d.setMinutes(0, 0, 0);
    while (d.getHours() % step !== 0) d.setHours(d.getHours() + 1);
    for (let t = d.getTime(); t <= end; t += step * 3600000) {
      const dt = new Date(t);
      out.push({
        t,
        label: asDays ? dt.toLocaleDateString("en-GB", { weekday: "short" })
                      : String(dt.getHours()).padStart(2, "0"),
      });
    }
    return out;
  }

  _draw() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const hass = this._hass;
    const end = this._end || Date.now();
    const start = this._start || (end - this._hours * 3600000);
    const span = end - start;
    const pc = (t) => ((t - start) / span) * 100;

    const night = this._nightBands(start, end)
      .map(([a, b]) => `<div class="night" style="left:${pc(a)}%;width:${pc(b) - pc(a)}%"></div>`)
      .join("");

    if (this._mode === "band") { this._drawBand(start, end, pc, night); return; }

    const rows = this._lanes.map((lane) => {
      const room = ROOMS.find((r) => r.key === lane.key);
      const cov = room ? coverageOf(hass, room) : { state: hass && hass.states[lane.entity] ? "live" : "absent" };
      const blind = cov.state !== "live";

      let track;
      if (this._err) {
        track = `<div class="blind"></div><div class="note">history unavailable</div>`;
      } else if (blind) {
        track = `<div class="blind"></div><div class="note">${esc(cov.state === "stuck" ? "sensor stuck" : "not reporting")}</div>`;
      } else if (!this._hist) {
        // Quiet, not alarming. Waiting on the recorder is not a fault, and
        // this is the state every ribbon starts in.
        track = `<div class="note quiet">loading</div>`;
      } else {
        const rows = this._hist[lane.entity];
        const segs = this._segments(rows, start, end);
        // Hatch sits on top of the blocks: where the recorder was blind, no
        // claim about activity is being made either way.
        const gaps = this._blind(rows, start, end)
          .map(([a, b]) => `<div class="gap" style="left:${pc(a)}%;width:${pc(b) - pc(a)}%"></div>`)
          .join("");
        track = segs.length
          ? segs.map(([a, b]) =>
              `<div class="blk" style="left:${pc(a)}%;width:${Math.max(pc(b) - pc(a), 0.35)}%"></div>`).join("") + gaps
          : gaps + `<div class="note quiet">no activity in ${this._hours}h</div>`;
      }

      return `<div class="lane">
        <div class="lname">${esc(lane.name)}</div>
        <div class="track">${night}${track}</div>
      </div>`;
    }).join("");

    // Drop any tick that would collide with "now" at the right edge. Losing
    // one label costs nothing; two words on top of each other costs legibility.
    const ticks = this._ticks(start, end)
      .filter((k) => pc(k.t) < 88)
      .map((k) => `<div class="tick" style="left:${pc(k.t)}%"><span>${k.label}</span></div>`)
      .join("");

    this.shadowRoot.innerHTML = `<style>${THEME}${HaivenRibbon.css}</style>
      <div class="card">
        <div class="lanes">${rows}</div>
        <div class="axis">${ticks}<div class="now" style="left:100%"><span>now</span></div></div>
      </div>`;
  }

  // The band, plus a legend that carries the room NAMES and how long she spent
  // in each. The names are why the legend exists: colour is never the only
  // channel anywhere else in this library and a chart is no exception.
  _drawBand(start, end, pc, night) {
    const ROOM_FILL = {
      kitchen: "var(--room-kitchen)",
      bedroom: "var(--room-bedroom)",
      bathroom: "var(--room-bathroom)",
    };

    let body, legend = "";
    if (this._err) {
      body = `<div class="blind"></div><div class="note">history unavailable</div>`;
    } else if (!this._hist) {
      body = `<div class="note quiet">loading</div>`;
    } else {
      const runs = this._band(start, end);
      // A five-minute bathroom visit is 1% of an eight-hour window and draws
      // as a hairline. Anything under this gets a floor so it is visible at
      // all, and is drawn ON TOP, or the long kitchen run either side paints
      // over the very thing being widened.
      const TINY = 2;
      let widened = false;
      body = runs.map((r) => {
        if (r.key === "quiet") return "";
        const w = pc(r.b) - pc(r.a);
        const tiny = r.key !== "blind" && w < TINY;
        if (tiny) widened = true;
        const cls = `${r.key === "blind" ? "gap" : "run"}${tiny ? " tiny" : ""}`;
        const fill = r.key === "blind" ? "" : `background:${ROOM_FILL[r.key]}`;
        const label = r.key === "blind" ? "not recorded"
          : `${(ROOMS.find((x) => x.key === r.key) || {}).name} ${fmtClock(r.a)}-${fmtClock(r.b)}`;
        return `<div class="${cls}" style="left:${pc(r.a)}%;width:${w}%;${fill}"
                     title="${esc(label)}"></div>`;
      }).join("");

      // Total time per room over the window, from the runs rather than the raw
      // segments, so the legend adds up to exactly what is drawn.
      const mins = {};
      runs.forEach((r) => { if (ROOM_FILL[r.key]) mins[r.key] = (mins[r.key] || 0) + (r.b - r.a) / 60000; });
      const anyBlind = runs.some((r) => r.key === "blind");
      this._widened = widened;
      legend = `<div class="key">
        ${this._lanes.map((l) => {
          const m = mins[l.key] || 0;
          return `<div class="k"><span class="sw" style="background:${ROOM_FILL[l.key]}"></span>
            <span class="kn">${esc(l.name)}</span>
            <span class="kv mono">${m < 1 ? DASH : durStr(m)}</span></div>`;
        }).join("")}
        ${anyBlind ? `<div class="k"><span class="sw hatch"></span>
          <span class="kn">Not recorded</span></div>` : ""}
      </div>
      ${widened ? `<div class="foot">Short visits are drawn wider than they
        were, so they can be seen. The times above are the real ones.</div>` : ""}`;
    }

    const ticks = this._ticks(start, end)
      .filter((k) => pc(k.t) < 88)
      .map((k) => `<div class="tick" style="left:${pc(k.t)}%"><span>${k.label}</span></div>`)
      .join("");

    this.shadowRoot.innerHTML = `<style>${THEME}${HaivenRibbon.css}</style>
      <div class="card band">
        <div class="track tall">${night}${body}</div>
        <div class="axis flush">${ticks}<div class="now" style="left:100%"><span>now</span></div></div>
        ${legend}
      </div>`;
  }

  static get css() { return `
    .card{background:var(--surface);border:1px solid var(--line);padding:14px 14px 8px}
    .card.band{padding:14px 14px 12px}
    .track.tall{height:38px}
    /* A hairline in the track colour between adjacent runs. Two rooms that
       touch now have an edge rather than only a hue change, which survives
       sunlight and colour vision deficiency in a way colour alone does not. */
    .run{position:absolute;top:0;bottom:0;min-width:2px;
         box-shadow:1px 0 0 var(--surface-2), -1px 0 0 var(--surface-2)}
    .run.tiny{min-width:7px;z-index:2}
    .foot{margin-top:8px;font-size:11px;line-height:1.4;color:var(--faint)}
    .axis.flush{margin-left:0}
    .key{display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:12px;
         padding-top:11px;border-top:1px solid var(--surface-2)}
    .k{display:flex;align-items:center;gap:7px;min-width:0}
    .sw{width:11px;height:11px;flex:0 0 auto;border-radius:2px}
    .sw.hatch{background:repeating-linear-gradient(45deg,
      var(--surface-2),var(--surface-2) 3px,var(--line) 3px,var(--line) 6px)}
    .kn{font-size:12px;color:var(--muted)}
    .kv{font-size:12px;color:var(--ink);font-weight:600}
    .lane{display:flex;align-items:center;gap:10px;margin-bottom:7px}
    .lname{flex:0 0 62px;font-size:11.5px;color:var(--muted);text-align:right}
    .track{position:relative;flex:1 1 auto;height:20px;background:var(--surface-2);overflow:hidden}
    .night{position:absolute;top:0;bottom:0;background:var(--line);opacity:.75}
    .blk{position:absolute;top:2px;bottom:2px;background:var(--accent);min-width:2px;border-radius:1px}
    .blind{position:absolute;inset:0;background:repeating-linear-gradient(45deg,
      var(--surface-2),var(--surface-2) 4px,var(--line) 4px,var(--line) 8px)}
    .gap{position:absolute;top:0;bottom:0;background:repeating-linear-gradient(45deg,
      var(--surface-2),var(--surface-2) 4px,var(--line) 4px,var(--line) 8px)}
    .note{position:absolute;inset:0;display:flex;align-items:center;padding-left:8px;
          font-size:10.5px;letter-spacing:.05em;color:var(--crit);text-transform:uppercase}
    .note.quiet{color:var(--faint)}
    .axis{position:relative;height:20px;margin-left:72px}
    .tick{position:absolute;top:0;border-left:1px solid var(--line);height:5px}
    .tick span{position:absolute;top:6px;left:0;transform:translateX(-50%);
               font-size:10px;color:var(--faint);font-variant-numeric:tabular-nums;
               white-space:nowrap}
    .now{position:absolute;top:0;height:5px;border-left:1px solid var(--accent)}
    .now span{position:absolute;top:6px;right:0;font-size:10px;color:var(--accent)}
  `; }
}

/* ----------------------------- haiven-compare ---------------------------
 * Today against her own baseline, which is the only baseline that means
 * anything: there is no population norm for one 82-year-old's wake time.
 *
 * Deltas are deliberately NOT coloured good or bad. Waking an hour late is
 * information, not a fault, and colouring it red teaches a carer to panic at
 * a lie-in. Colour only appears past an explicit `flag:` in the config, and
 * then it is amber, never red.
 * --------------------------------------------------------------------- */

const hhmm = (s) => { const m = /^(\d{1,2}):(\d{2})/.exec(String(s || "")); return m ? (+m[1]) * 60 + (+m[2]) : null; };
const mmStr = (d) => {
  const a = Math.abs(Math.round(d));
  if (a < 60) return `${a} min`;
  const h = Math.floor(a / 60), m = a % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
};

class HaivenCompare extends HaivenCard {
  get css() { return `
    .wrap{background:var(--surface);border:1px solid var(--line)}
    .row{display:flex;align-items:center;gap:12px;padding:13px 16px;border-bottom:1px solid var(--surface-2)}
    .row:last-child{border-bottom:0}
    .l{flex:1 1 auto;min-width:0}
    .lab{font-size:14px;color:var(--ink)}
    .base{font-size:11.5px;color:var(--faint);margin-top:2px}
    .r{flex:0 0 auto;text-align:right}
    .v{font-size:17px;color:var(--ink)}
    .v.none{color:var(--faint);font-size:17px}
    .d{font-size:11.5px;color:var(--muted);margin-top:2px}
    .d.flag{color:var(--warn);font-weight:600}
    .d.same{color:var(--faint)}
  `; }

  signature(hass) {
    return (this._config.rows || [])
      .map((r) => `${txt(hass, r.entity, "")}~${txt(hass, r.baseline, "")}`).join("|");
  }

  render(hass) {
    const rows = (this._config.rows || []).map((r) => {
      const e = hass.states[r.entity];
      const b = hass.states[r.baseline];
      const missing = isUn(e) || (e && ["Not yet", "None", "N/A"].includes(e.state));

      let delta = null, deltaTxt = "", noBase = isUn(b);
      if (!missing && !noBase) {
        if (r.kind === "time") {
          const a = hhmm(e.state), c = hhmm(b.state);
          if (a !== null && c !== null) {
            let d = a - c;
            if (d > 720) d -= 1440;          // bedtimes either side of midnight
            if (d < -720) d += 1440;
            delta = d;
            deltaTxt = d === 0 ? "on her usual time"
              : `${mmStr(d)} ${d > 0 ? "later" : "earlier"} than usual`;
          }
        } else {
          const a = num(e.state), c = num(b.state);
          if (a !== null && c !== null) {
            delta = a - c;
            const shown = Math.abs(delta) < 1 ? Math.abs(delta).toFixed(1) : String(Math.round(Math.abs(delta)));
            deltaTxt = Math.abs(delta) < 0.05 ? "on her usual"
              : `${shown} ${delta > 0 ? "more" : "fewer"} than usual`;
          }
        }
      }

      const flag = r.flag !== undefined && delta !== null && Math.abs(delta) > Number(r.flag);
      const base = noBase ? `no baseline yet ${DASH}` : `usually ${esc(b.state)}${r.unit ? " " + esc(r.unit) : ""}`;
      const cls = flag ? "d flag" : (delta === 0 ? "d same" : "d");

      return `<div class="row">
        <div class="l"><div class="lab">${esc(r.label || "")}</div><div class="base">${base}</div></div>
        <div class="r">
          <div class="v mono ${missing ? "none" : ""}">${missing ? DASH : esc(e.state)}</div>
          <div class="${cls}">${esc(missing ? "not recorded yet" : deltaTxt)}</div>
        </div>
      </div>`;
    }).join("");
    this.paint(`<div class="wrap">${rows}</div>`);
  }
}

/* ------------------------------ haiven-drift ----------------------------
 * A month of nights against a baseline that does not move. One row per
 * chart from sensor.drift_stats (scripts/drift_stats.py): the smoothed
 * level against "usually", a sparkline of the last 28 nights over the usual
 * band, and a state word. Steady / Watching / Changed / Learning, always as
 * a word, never colour alone. Tap a row for the accumulator: how far the
 * run of off nights has climbed towards the trip point.
 *
 * The compare rows above answer "how was last night". This answers "has the
 * last month quietly moved", which a 7-day average cannot see.
 *
 * Row options: chart (visits|wake|activity), label, kind (count|time),
 * unit, period (night|day, for the wording), direction (above|below, which
 * way the chart trips), show (level|today). `show: today` puts the day so
 * far in the number slot against the baseline days' count by the same clock
 * time, which is what the Home page wants; the sparkline stays the last 28
 * complete days.
 * --------------------------------------------------------------------- */

const DRIFT_ENTITY = "sensor.drift_stats";
const DRIFT_WORD = { steady: "Steady", watching: "Watching", changed: "Changed", learning: "Learning" };
const DRIFT_CLS = { steady: "ok", watching: "warn", changed: "crit", learning: "faint" };

class HaivenDrift extends HaivenCard {
  get css() { return `
    .wrap{background:var(--surface);border:1px solid var(--line)}
    .row{padding:12px 16px;border-bottom:1px solid var(--surface-2);cursor:pointer}
    .row:last-child{border-bottom:0}
    .row:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
    .top{display:flex;align-items:center;gap:12px}
    .l{flex:1 1 auto;min-width:0}
    .lab{font-size:14px;color:var(--ink)}
    .base{font-size:11.5px;color:var(--faint);margin-top:2px}
    .spark{flex:0 0 auto;width:84px;height:28px;display:block}
    .r{flex:0 0 auto;text-align:right;min-width:64px}
    .v{font-size:17px;color:var(--ink)}
    .v.none{color:var(--faint)}
    .pill{display:inline-flex;align-items:center;gap:5px;margin-top:3px;font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;padding:2px 7px;border-radius:999px}
    .pill::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor}
    .pill.ok{color:var(--good);background:var(--good-wash)}
    .pill.warn{color:var(--warn);background:var(--warn-wash)}
    .pill.crit{color:var(--crit);background:var(--crit-wash)}
    .pill.faint{color:var(--faint);background:var(--surface-2)}
    .more{display:none;margin-top:10px;padding-top:10px;border-top:1px dashed var(--line)}
    .row.open .more{display:block}
    .more .t{font-size:12px;color:var(--muted);margin-bottom:6px}
    .more .t b{color:var(--ink);font-weight:600}
    .acc{width:100%;height:56px;display:block}
    .more .k{display:flex;justify-content:space-between;font-size:10.5px;color:var(--faint);margin-top:4px}
  `; }

  signature(hass) {
    const e = hass.states[DRIFT_ENTITY];
    return e ? `${e.state}|${e.attributes.generated || ""}` : "?";
  }

  // Sparkline: last 28 nights, usual band, line, emphasised last point.
  _spark(c, kind) {
    const pts = (c.series || []).map((p) => Number(p[1])).filter((v) => Number.isFinite(v));
    if (pts.length < 2) return "";
    const W = 84, H = 28, P = 3;
    const usual = num(c.usual), sd = num(c.sd);
    let lo = Math.min(...pts), hi = Math.max(...pts);
    if (usual !== null && sd !== null) { lo = Math.min(lo, usual - sd); hi = Math.max(hi, usual + sd); }
    if (hi === lo) hi = lo + 1;
    const x = (i) => P + (W - 2 * P) * i / (pts.length - 1);
    const y = (v) => H - P - (H - 2 * P) * (v - lo) / (hi - lo);
    const band = (usual !== null && sd !== null)
      ? `<rect x="0" y="${y(usual + sd).toFixed(1)}" width="${W}" height="${(y(usual - sd) - y(usual + sd)).toFixed(1)}" fill="var(--accent)" opacity=".13"/>
         <line x1="0" x2="${W}" y1="${y(usual).toFixed(1)}" y2="${y(usual).toFixed(1)}" stroke="var(--accent)" stroke-width="1" stroke-dasharray="2 3" opacity=".7"/>`
      : "";
    const d = pts.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
    const colour = kind === "crit" ? "var(--crit)" : kind === "warn" ? "var(--warn)" : "var(--ink)";
    return `<svg class="spark" viewBox="0 0 ${W} ${H}" aria-hidden="true">${band}
      <path d="${d}" fill="none" stroke="${colour}" stroke-width="1.5" stroke-linejoin="round" opacity=".85"/>
      <circle cx="${x(pts.length - 1).toFixed(1)}" cy="${y(pts[pts.length - 1]).toFixed(1)}" r="2.4" fill="${colour}"/>
    </svg>`;
  }

  // Accumulator: one bar per night since the chart last restarted, against
  // the trip point. Empty bars are nights that pulled it back to zero.
  _acc(c) {
    const S = (c.S_series || []).map((p) => Number(p[1]));
    const h = num(c.h) || 5;
    const W = 300, H = 56, P = 4;
    const n = Math.max(S.length, 14);
    const top = Math.max(h * 1.15, ...S, 0.1);
    const y = (v) => H - P - (H - 2 * P) * v / top;
    const bw = (W - 2 * P) / n;
    const bars = S.map((v, i) => {
      const bx = P + i * bw, by = y(v);
      const fill = v > h ? "var(--crit)" : v > h / 2 ? "var(--warn)" : "var(--accent)";
      return v > 0
        ? `<rect x="${(bx + 1).toFixed(1)}" y="${by.toFixed(1)}" width="${Math.max(bw - 2, 1).toFixed(1)}" height="${(H - P - by).toFixed(1)}" fill="${fill}" opacity=".8"/>`
        : `<rect x="${(bx + 1).toFixed(1)}" y="${(H - P - 1.5).toFixed(1)}" width="${Math.max(bw - 2, 1).toFixed(1)}" height="1.5" fill="var(--line)"/>`;
    }).join("");
    return `<svg class="acc" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">
      <line x1="0" x2="${W}" y1="${y(h).toFixed(1)}" y2="${y(h).toFixed(1)}" stroke="var(--crit)" stroke-width="1" stroke-dasharray="3 3" opacity=".7"/>
      <line x1="0" x2="${W}" y1="${(H - P).toFixed(1)}" y2="${(H - P).toFixed(1)}" stroke="var(--line)" stroke-width="1"/>
      ${bars}
    </svg>`;
  }

  _detail(c, r) {
    const isTime = r.kind === "time";
    const fmt = (v) => (isTime ? mmClock(v) : (num(v) === null ? DASH : num(v).toFixed(r.period === "day" ? 0 : 1)));
    const usual = fmt(c.usual);
    const p = r.period === "day" ? "day" : "night", ps = p + "s";
    const dir = r.direction === "below" ? "below" : "above";
    switch (c.state) {
      case "learning":
        return `<b>Learning</b> ${DASH} ${c.days_learned || 0} of 28 ${ps} recorded before this can say anything.`;
      case "changed":
        return `<b>Changed</b> ${DASH} ${fmt(c.recent)}${r.unit ? " " + esc(r.unit) : ""} for ${c.run} ${ps}, against a usual ${usual}. A message went out on the morning after ${dayStr(c.trip_date)}.`;
      case "watching":
        return `<b>Watching</b> ${DASH} ${c.run} ${c.run === 1 ? p : ps} ${dir} usual, the accumulator at ${num(c.S)} of ${num(c.h)}. One ordinary ${p} pulls it back.`;
      default:
        return `<b>Steady</b> ${DASH} nothing has built up since ${dayStr(c.base_to)}. Usual is ${usual}${r.unit ? " " + esc(r.unit) : ""}, from the 28 ${ps} ${dayStr(c.base_from)} to ${dayStr(c.base_to)}.`;
    }
  }

  render(hass) {
    const e = hass.states[DRIFT_ENTITY];
    const rows = (this._config.rows || []).map((r, i) => {
      const c = (e && e.attributes && e.attributes[r.chart]) || null;
      if (!c) {
        return `<div class="row" data-i="${i}" tabindex="0"><div class="top">
          <div class="l"><div class="lab">${esc(r.label || r.chart)}</div><div class="base">not reporting</div></div>
          <div class="r"><div class="v none">${DASH}</div></div></div></div>`;
      }
      const isTime = r.kind === "time";
      const dp = r.period === "day" ? 0 : 1;
      let level, usual, base;
      if (r.show === "today") {
        // The day so far, against what the baseline days had by this time.
        level = num(c.today) === null ? DASH : String(Math.round(num(c.today)));
        usual = num(c.usual_by_now) === null ? null : String(Math.round(num(c.usual_by_now)));
        base = usual === null ? `no baseline yet ${DASH}` : `usually ${esc(usual)} by now`;
      } else {
        level = isTime ? (c.level_text || DASH) : (num(c.level) === null ? DASH : num(c.level).toFixed(dp));
        usual = isTime ? (c.usual_text || null) : (num(c.usual) === null ? null : num(c.usual).toFixed(dp));
        base = usual === null ? `no baseline yet ${DASH}` : `usually ${esc(usual)}${r.unit ? " " + esc(r.unit) : ""}`;
      }
      const cls = DRIFT_CLS[c.state] || "faint";
      return `<div class="row ${this._open === i ? "open" : ""}" data-i="${i}" tabindex="0" aria-expanded="${this._open === i}">
        <div class="top">
          <div class="l"><div class="lab">${esc(r.label || r.chart)}</div><div class="base">${base}</div></div>
          ${this._spark(c, cls)}
          <div class="r">
            <div class="v mono ${level === DASH ? "none" : ""}">${esc(level)}</div>
            <div class="pill ${cls}">${esc(DRIFT_WORD[c.state] || c.state || "?")}</div>
          </div>
        </div>
        <div class="more">
          <div class="t">${this._detail(c, r)}</div>
          ${this._acc(c)}
          <div class="k"><span>each bar is a ${r.period === "day" ? "day" : "night"} since the chart last restarted</span><span>trip point ${esc(num(c.h) || 5)}</span></div>
        </div>
      </div>`;
    }).join("");
    this.paint(`<div class="wrap">${rows}</div>`);

    this.shadowRoot.querySelectorAll(".row").forEach((el) => {
      const i = Number(el.dataset.i);
      const go = () => { this._open = this._open === i ? null : i; this._sig = null; this.render(this._hass); };
      el.addEventListener("click", go);
      el.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(); }
      });
    });
  }
}

// Minutes after midnight -> "05:06"; the drift script sends both forms but
// the sparkline maths needs the number.
const dayStr = (iso) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
  if (!m) return esc(iso || "?");
  return new Date(+m[1], +m[2] - 1, +m[3]).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
};
const mmClock = (v) => {
  const n = num(v);
  if (n === null) return DASH;
  const m = Math.round(n);
  return `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
};

/* ---------------------------- haiven-movement ----------------------------
 * Today's kitchen + bedroom + bathroom trigger count so far, against a
 * plain 7-day average by the same clock time (sensor.movement_stats,
 * scripts/movement_today.py). Deliberately not haiven-drift: no state, no
 * accumulator, no alerting - a description, not a detector, so it is
 * allowed to combine rooms where the drift chart cannot (DRIFT_WATCH.md).
 * The pill is neutral except at "Typical": quieter or busier than usual is
 * just a fact here, not a judgement.
 * --------------------------------------------------------------------- */

const MOVEMENT_ENTITY = "sensor.movement_stats";

class HaivenMovement extends HaivenCard {
  get css() { return `
    .wrap{background:var(--surface);border:1px solid var(--line);padding:12px 16px}
    .top{display:flex;align-items:center;gap:12px}
    .l{flex:1 1 auto;min-width:0}
    .lab{font-size:14px;color:var(--ink)}
    .base{font-size:11.5px;color:var(--faint);margin-top:2px}
    .spark{flex:0 0 auto;width:84px;height:28px;display:block}
    .r{flex:0 0 auto;text-align:right;min-width:64px}
    .v{font-size:17px;color:var(--ink)}
    .v.none{color:var(--faint)}
    .pill{display:inline-flex;align-items:center;gap:5px;margin-top:3px;font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;padding:2px 7px;border-radius:999px}
    .pill::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor}
    .pill.ok{color:var(--good);background:var(--good-wash)}
    .pill.faint{color:var(--faint);background:var(--surface-2)}
  `; }

  signature(hass) {
    const e = hass.states[MOVEMENT_ENTITY];
    return e ? `${e.state}|${e.attributes.generated || ""}` : "?";
  }

  _spark(series) {
    const pts = (series || []).map((p) => Number(p[1])).filter((v) => Number.isFinite(v));
    if (pts.length < 2) return "";
    const W = 84, H = 28, P = 3;
    const lo = Math.min(...pts), hi = Math.max(...pts) || 1;
    const x = (i) => P + (W - 2 * P) * i / (pts.length - 1);
    const y = (v) => H - P - (H - 2 * P) * (v - lo) / ((hi - lo) || 1);
    const d = pts.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
    return `<svg class="spark" viewBox="0 0 ${W} ${H}" aria-hidden="true">
      <path d="${d}" fill="none" stroke="var(--ink)" stroke-width="1.5" stroke-linejoin="round" opacity=".85"/>
      <circle cx="${x(pts.length - 1).toFixed(1)}" cy="${y(pts[pts.length - 1]).toFixed(1)}" r="2.4" fill="var(--ink)"/>
    </svg>`;
  }

  render(hass) {
    const e = hass.states[MOVEMENT_ENTITY];
    const today = e ? num(e.attributes.today) : null;
    const usual = e ? num(e.attributes.usual_by_now) : null;
    const label = (this._config && this._config.label) || "Movement, all rooms";
    if (today === null) {
      this.paint(`<div class="wrap"><div class="top">
        <div class="l"><div class="lab">${esc(label)}</div><div class="base">not reporting</div></div>
        <div class="r"><div class="v none">${DASH}</div></div></div></div>`);
      return;
    }
    const base = usual === null ? `no baseline yet ${DASH}` : `usually ${Math.round(usual)} by now`;
    const ratio = usual ? Math.round((today / usual) * 100) : null;
    const cls = ratio !== null && ratio >= 85 && ratio <= 115 ? "ok" : "faint";
    const word = ratio === null ? null : ratio < 85 ? "Quieter" : ratio > 115 ? "Busier" : "Typical";
    this.paint(`<div class="wrap"><div class="top">
      <div class="l"><div class="lab">${esc(label)}</div><div class="base">${base}</div></div>
      ${this._spark(e.attributes.series)}
      <div class="r">
        <div class="v mono">${today}</div>
        ${word ? `<div class="pill ${cls}">${esc(word)}</div>` : ""}
      </div>
    </div></div>`);
  }
}

/* ------------------------------ haiven-where ----------------------------
 * Triangulation across the three sensors, and honest about when they
 * disagree. Three sensors covering a whole house do not give you a position;
 * they give you evidence, and the useful output is a room plus how much to
 * trust it.
 *
 * The failure this exists to prevent: mmWave latches on in the bedroom while
 * the bathroom fires downstairs. Two rooms claim her at once. A card that
 * picks the most recent and prints it flat would show "Bathroom" with the
 * same confidence it shows anything else.
 * --------------------------------------------------------------------- */

class HaivenWhere extends HaivenCard {
  get css() { return `
    .card{background:var(--surface);border:1px solid var(--line);padding:16px}
    .hd{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:3px}
    .room{font-size:22px;color:var(--ink)}
    .room.none{color:var(--faint)}
    .conf{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;font-weight:700}
    .why{font-size:13px;color:var(--muted);margin-bottom:13px}
    .ev{display:flex;flex-direction:column;gap:0;border-top:1px solid var(--surface-2)}
    .e{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid var(--surface-2)}
    .e:last-child{border-bottom:0}
    .dot{width:7px;height:7px;border-radius:50%;flex:0 0 auto}
    .en{flex:1 1 auto;font-size:13.5px;color:var(--ink)}
    .es{font-size:12.5px;color:var(--faint)}
    .es.on{color:var(--good);font-weight:600}
  `; }

  signature(hass) {
    return coverage(hass).rooms.map((r) => {
      const m = hass.states[r.motion];
      return `${r.state}:${m ? m.state : "?"}:${Math.round((ageMin(hass, r.motion) || 0) / 2)}`;
    }).join("|") + "|" + txt(hass, HOME_ENTITY, "") + txt(hass, WHERE_ENTITY, "");
  }

  render(hass) {
    const c = coverage(hass);
    const p = presence(hass);
    const rooms = c.rooms.map((r) => {
      const m = hass.states[r.motion];
      return { ...r, on: !isUn(m) && m.state === "on", mAge: ageMin(hass, r.motion) };
    });

    const seen = rooms.filter((r) => r.state === "live");
    const on = seen.filter((r) => r.on);
    const recent = seen
      .filter((r) => !r.on && r.mAge !== null && r.mAge <= 5)
      .sort((a, b) => a.mAge - b.mAge);

    let room = null, conf = "unknown", why = "";
    if (on.length === 1) {
      room = on[0]; conf = "certain"; why = "reporting now";
    } else if (on.length > 1) {
      room = on.slice().sort((a, b) => (a.mAge ?? 1e9) - (b.mAge ?? 1e9))[0];
      conf = "unclear";
      why = `${esc(on.map((r) => r.name.toLowerCase()).join(" and "))} both reporting at once`;
    } else if (recent.length) {
      room = recent[0]; conf = "likely"; why = `last movement ${esc(relTime(room.mAge))}`;
    } else {
      const last = seen.filter((r) => r.mAge !== null).sort((a, b) => a.mAge - b.mAge)[0];
      if (last) { room = last; conf = "last known"; why = `no movement anywhere for ${esc(relTime(last.mAge).replace(" ago", ""))}`; }
      else { why = "no sensor is reporting"; }
    }

    // She is not in the house, so which room the sensors last saw is a fact
    // about the dogs. Say where she is and stop guessing.
    if (p.known && !p.home) {
      const evOut = rooms.map((r) => `<div class="e">
        <div class="dot" style="background:${COVER_COLOUR[r.state]}"></div>
        <div class="en">${esc(r.name)}</div>
        <span class="es">${r.state === "live" ? esc(relTime(r.mAge)) : "not reporting"}</span>
      </div>`).join("");
      this.paint(`<div class="card">
        <div class="hd">
          <div class="room">${esc(p.where || "Out")}</div>
          <div class="conf" style="color:var(--accent)">away</div>
        </div>
        <div class="why">Room sensors below are still reporting, but they are not reporting her</div>
        <div class="ev">${evOut}</div>
      </div>`);
      return;
    }

    // Coverage can only ever hold confidence back. A blind room is a room she
    // could be in, so nothing is "certain" while one is dark.
    if (c.live < c.total && room) {
      if (conf === "certain") conf = "likely";
      const blind = c.bad.map((r) => r.name.toLowerCase()).join(" and ");
      why += ` &middot; ${esc(blind)} not covered`;
    }

    const colour = { certain: "var(--good)", likely: "var(--muted)", unclear: "var(--warn)",
                     "last known": "var(--faint)", unknown: "var(--crit)" }[conf];

    const ev = rooms.map((r) => {
      let s;
      if (r.state !== "live") s = `<span class="es">${r.state === "stuck" ? "stuck" : "not reporting"}</span>`;
      else if (r.on) s = `<span class="es on">active now</span>`;
      else s = `<span class="es">${esc(relTime(r.mAge))}</span>`;
      return `<div class="e">
        <div class="dot" style="background:${COVER_COLOUR[r.state]}"></div>
        <div class="en">${esc(r.name)}</div>${s}
      </div>`;
    }).join("");

    this.paint(`<div class="card">
      <div class="hd">
        <div class="room ${room ? "" : "none"}">${room ? esc(room.name) : DASH}</div>
        <div class="conf" style="color:${colour}">${esc(conf)}</div>
      </div>
      <div class="why">${why}</div>
      <div class="ev">${ev}</div>
    </div>`);
  }
}

/* ----------------------------- haiven-devices ---------------------------
 * The sensor page. Not "is it green", but: what stops working if this dies.
 * A carer looking at this screen is usually looking at it because something
 * has already gone wrong, and "Bedroom offline" on its own does not tell them
 * that bedtime detection and time-in-bed have both silently stopped.
 * --------------------------------------------------------------------- */

class HaivenDevices extends HaivenCard {
  get css() { return `
    .wrap{display:flex;flex-direction:column;gap:10px}
    .d{background:var(--surface);border:1px solid var(--line);padding:14px 16px}
    .top{display:flex;align-items:baseline;justify-content:space-between;gap:10px}
    .n{font-size:16px;color:var(--ink)}
    .st{font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;font-weight:700;flex:0 0 auto}
    .kind{font-size:12px;color:var(--faint);margin-top:1px}
    .meta{display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:10px}
    .m{font-size:12.5px;color:var(--muted)}
    .m b{font-weight:600;color:var(--ink)}
    .m.warn b{color:var(--warn)}
    .covers{margin-top:11px;padding-top:10px;border-top:1px solid var(--surface-2);
            font-size:12.5px;color:var(--muted);line-height:1.45}
    .covers.lost{color:var(--crit)}
    .id{margin-top:8px;font-size:10.5px;color:var(--faint);word-break:break-all}
  `; }

  signature(hass) {
    return (this._config.devices || []).map((d) => {
      const room = ROOMS.find((r) => r.key === d.key);
      const c = room ? coverageOf(hass, room) : { state: "absent", mins: null };
      return `${c.state}:${Math.round((c.mins || 0) / 2)}:${txt(hass, d.battery, "")}`;
    }).join("|");
  }

  render(hass) {
    const WORD = { live: "Online", dead: "Offline", absent: "Missing", stuck: "Stuck" };
    const cards = (this._config.devices || []).map((d) => {
      const room = ROOMS.find((r) => r.key === d.key);
      if (!room) return "";
      const c = coverageOf(hass, room);
      const ok = c.state === "live";
      const colour = COVER_COLOUR[c.state];

      const meta = [];
      meta.push(`<div class="m">Last seen <b>${ok ? esc(relTime(c.mins)) : DASH}</b></div>`);
      if (ok) meta.push(`<div class="m">At <b class="mono">${esc(clockOf(hass, room.entity))}</b></div>`);
      if (d.battery) {
        const b = hass.states[d.battery];
        const pct = isUn(b) ? null : num(b.state);
        // A battery reading is itself a sensor that can go missing, so no
        // number means a dash, not an assumed 100%.
        const low = pct !== null && pct <= Number(d.battery_low || 20);
        meta.push(`<div class="m ${low ? "warn" : ""}">Battery <b>${pct === null ? DASH : pct + "%"}</b></div>`);
      }

      return `<div class="d">
        <div class="top">
          <div><div class="n">${esc(room.name)}</div><div class="kind">${esc(d.kind || "")}</div></div>
          <div class="st" style="color:${colour}">${WORD[c.state]}</div>
        </div>
        <div class="meta">${meta.join("")}</div>
        <div class="covers ${ok ? "" : "lost"}">${ok ? "Feeds" : "Not feeding"}: ${esc(d.covers || "")}</div>
        <div class="id mono">${esc(room.entity)}</div>
      </div>`;
    }).join("");
    this.paint(`<div class="wrap">${cards}</div>`);
  }
}

/* ------------------------------ haiven-people ---------------------------
 * The care circle. The number that matters is not distance, it is how old
 * the distance is: a phone that stopped reporting five days ago still says
 * "60 km away" with total confidence, and someone reading that will believe
 * it. Age is shown next to every position, and a stale one is called stale.
 * --------------------------------------------------------------------- */

class HaivenPeople extends HaivenCard {
  get css() { return `
    .wrap{background:var(--surface);border:1px solid var(--line)}
    .subj{display:flex;align-items:center;justify-content:space-between;gap:12px;
          padding:15px 16px;border-bottom:1px solid var(--line)}
    .sn{font-size:16px;color:var(--ink)}
    .sw{font-size:14px;font-weight:600}
    .p{display:flex;align-items:center;gap:12px;padding:13px 16px;border-bottom:1px solid var(--surface-2)}
    .p:last-child{border-bottom:0}
    .dot{width:8px;height:8px;border-radius:50%;flex:0 0 auto}
    .l{flex:1 1 auto;min-width:0}
    .nm{font-size:14.5px;color:var(--ink)}
    .wh{font-size:12px;color:var(--faint);margin-top:2px;overflow:hidden;
        text-overflow:ellipsis;white-space:nowrap}
    .r{flex:0 0 auto;text-align:right}
    .di{font-size:14px;color:var(--muted)}
    .di.none{color:var(--faint)}
    .ag{font-size:11px;color:var(--faint);margin-top:2px}
    .ag.stale{color:var(--warn)}
    .empty{padding:15px 16px;font-size:13px;color:var(--faint)}
  `; }

  signature(hass) {
    const subj = this._config.subject || {};
    return [txt(hass, subj.location_entity, "")].concat(
      (this._config.people || CIRCLE).map((p) =>
        `${txt(hass, p.location, "")}~${txt(hass, p.distance, "")}~${Math.round((seenMin(hass, p.location) || 0) / 10)}`)
    ).join("|");
  }

  render(hass) {
    const subj = this._config.subject || {};
    const name = txt(hass, subj.name_entity, "She");
    const loc = hass.states[subj.location_entity];
    const home = !isUn(loc) && /home/i.test(loc.state) && !/away|not/i.test(loc.state);
    const subjWord = isUn(loc) ? DASH : loc.state;

    const rows = circleOf(hass, this._config).sort(byNearest).map((p) =>
      `<div class="p">
        <div class="dot" style="background:${p.missing ? "var(--faint)" : p.near ? "var(--good)" : "var(--muted)"}"></div>
        <div class="l">
          <div class="nm">${esc(p.who)}</div>
          <div class="wh">${p.missing ? "no position" : esc(p.where)}</div>
        </div>
        <div class="r">
          <div class="di ${p.km === null ? "none" : ""}">${esc(withUnit(p.dist))}</div>
          <div class="ag ${p.stale ? "stale" : ""}">${p.stale ? "last known " : ""}${esc(relTime(p.age))}</div>
        </div>
      </div>`).join("");

    this.paint(`<div class="wrap">
      <div class="subj">
        <div class="sn">${esc(name)}</div>
        <div class="sw" style="color:${isUn(loc) ? "var(--faint)" : home ? "var(--good)" : "var(--muted)"}">${esc(subjWord)}</div>
      </div>
      ${rows || `<div class="empty">No one in the circle yet ${DASH}</div>`}
    </div>`);
  }
}

/* ------------------------------ haiven-alerts ---------------------------
 * Everything currently wrong, worst first, in one card. This replaces five
 * separate conditional cards whose visual order was their order in the YAML,
 * so a fall alert could render below a bathroom-frequency note.
 *
 * When nothing is live it names what IS being watched. "All clear" with
 * nothing behind it is indistinguishable from a monitoring system that has
 * quietly stopped running, which is exactly what happened here for 46 days.
 * --------------------------------------------------------------------- */

const RANK = { critical: 0, warning: 1, info: 2 };

class HaivenAlerts extends HaivenCard {
  get css() { return `
    .wrap{display:flex;flex-direction:column;gap:10px}
    .a{background:var(--surface);border:1px solid var(--line);border-left-width:3px;padding:14px 16px}
    .a.critical{border-left-color:var(--crit);background:var(--crit-wash)}
    .a.warning{border-left-color:var(--warn);background:var(--warn-wash)}
    .a.info{border-left-color:var(--accent)}
    .t{font-size:15px;font-weight:600;color:var(--ink)}
    .b{font-size:13.5px;color:var(--muted);margin-top:5px;line-height:1.45}
    .dt{display:flex;flex-wrap:wrap;gap:3px 16px;margin-top:9px}
    .dt div{font-size:12.5px;color:var(--muted)}
    .dt b{color:var(--ink);font-weight:600;font-variant-numeric:tabular-nums}
    .clear{background:var(--surface);border:1px solid var(--line);padding:16px}
    .cw{display:flex;align-items:center;gap:9px}
    .cd{width:9px;height:9px;border-radius:50%;background:var(--good)}
    .ct{font-size:15px;color:var(--ink);font-weight:600}
    .cl{margin-top:11px;padding-top:10px;border-top:1px solid var(--surface-2)}
    .cl div{font-size:12.5px;color:var(--faint);padding:2px 0}
    .cl .off{color:var(--warn)}
  `; }

  _active(hass, a) {
    const e = hass.states[a.entity];
    if (isUn(e)) return false;
    if (a.above !== undefined) { const n = num(e.state); return n !== null && n > Number(a.above); }
    return e.state === (a.on || "on");
  }

  signature(hass) {
    return (this._config.alerts || []).map((a) => this._active(hass, a) ? "1" : "0").join("")
      + "|" + (this._config.alerts || []).map((a) => txt(hass, a.body_entity, "")).join("|");
  }

  render(hass) {
    const live = (this._config.alerts || [])
      .filter((a) => this._active(hass, a))
      .sort((x, y) => (RANK[x.level] ?? 3) - (RANK[y.level] ?? 3));

    if (live.length) {
      const cards = live.map((a) => {
        const body = a.body_entity ? txt(hass, a.body_entity, "") : (a.note || "");
        const det = (a.detail || []).map((d) => {
          const e = hass.states[d.entity];
          let v = isUn(e) ? DASH : e.state;
          if (!isUn(e) && d.format === "time") v = /\d{2}:\d{2}/.test(v) ? v.slice(0, 5) : v;
          if (!isUn(e) && d.format === "mins") v = `${v} min`;
          return `<div>${esc(d.label)} <b>${esc(v)}</b></div>`;
        }).join("");
        return `<div class="a ${esc(a.level || "info")}">
          <div class="t">${esc(a.title || "")}</div>
          ${body ? `<div class="b">${esc(body)}</div>` : ""}
          ${det ? `<div class="dt">${det}</div>` : ""}
        </div>`;
      }).join("");
      this.paint(`<div class="wrap">${cards}</div>`);
      return;
    }

    // Nothing live. Say what is being watched, and whether the watching is
    // actually switched on.
    const gate = this._config.enabled_entity;
    const on = !gate || (hass.states[gate] && hass.states[gate].state === "on");
    const watching = (this._config.alerts || [])
      .map((a) => {
        const e = hass.states[a.entity];
        const dead = isUn(e);
        return `<div class="${dead ? "off" : ""}">${esc(a.title || "")}${dead ? ` ${DASH} not being checked` : ""}</div>`;
      }).join("");

    this.paint(`<div class="clear">
      <div class="cw">
        <div class="cd" style="background:${on ? "var(--good)" : "var(--warn)"}"></div>
        <div class="ct">${on ? "Nothing wrong" : "Monitoring is switched off"}</div>
      </div>
      <div class="cl">${watching}</div>
    </div>`);
  }
}

/* ----------------------------- haiven-actions ---------------------------
 * A row of buttons that call a service. Nothing here confirms first, so keep
 * the config to actions that are safe to fire twice.
 * --------------------------------------------------------------------- */

class HaivenActions extends HaivenCard {
  get css() { return `
    .row{display:flex;gap:8px}
    .b{flex:1 1 0;appearance:none;border:1px solid var(--line);background:var(--surface);
       color:var(--ink);font:inherit;font-size:14px;padding:14px 10px;cursor:pointer;
       text-align:center;min-height:48px}
    .b:hover{background:var(--surface-2)}
    .b:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
    .b.accent{background:var(--accent);border-color:var(--accent);color:var(--on-status);font-weight:600}
    .b.accent:hover{filter:brightness(1.1)}
    .b.done{background:var(--good);border-color:var(--good);color:var(--on-status)}
  `; }

  signature() { return (this._config.buttons || []).map((b) => b.label).join("|"); }

  render() {
    const btns = (this._config.buttons || []).map((b, i) =>
      `<button class="b ${b.tone === "accent" ? "accent" : ""}" type="button" data-i="${i}">${esc(b.label || "")}</button>`
    ).join("");
    this.paint(`<div class="row">${btns}</div>`);
    this.shadowRoot.querySelectorAll("button").forEach((el) => {
      el.addEventListener("click", () => {
        const b = this._config.buttons[Number(el.dataset.i)];
        const [domain, service] = String(b.action || "").split(".");
        if (!domain || !service) return;
        this._hass.callService(domain, service, b.data || {});
        // Confirm on the button itself. A service call is silent otherwise and
        // people press twice.
        const was = el.textContent;
        el.textContent = b.done || "Done";
        el.classList.add("done");
        setTimeout(() => { el.textContent = was; el.classList.remove("done"); }, 2500);
      });
    });
  }
}

/* ------------------------------ haiven-rows -----------------------------
 * A list of entities: label on the left, value on the right, tap for the
 * more-info dialog, which is where editing actually happens. Toggles flip in
 * place. This is the settings and configuration workhorse.
 * --------------------------------------------------------------------- */

class HaivenRows extends HaivenCard {
  get css() { return `
    .wrap{background:var(--surface);border:1px solid var(--line)}
    .r{display:flex;align-items:center;justify-content:space-between;gap:12px;
       padding:13px 16px;border-bottom:1px solid var(--surface-2);cursor:pointer;min-height:48px}
    /* A sentence in the value column crushes the label to one word per line,
       so long values get their own line underneath instead. */
    .r.stacked{flex-direction:column;align-items:stretch;gap:6px}
    .r.stacked .v{text-align:left;font-size:14px;line-height:1.45;white-space:normal}
    .r:last-child{border-bottom:0}
    .r:hover{background:var(--surface-2)}
    .r:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
    .l{min-width:0}
    .lb{font-size:14.5px;color:var(--ink)}
    .sb{font-size:11.5px;color:var(--faint);margin-top:2px}
    .v{flex:0 0 auto;font-size:14px;color:var(--muted);text-align:right}
    .v.none{color:var(--faint)}
    .v.on{color:var(--good);font-weight:600}
    .v.off{color:var(--warn);font-weight:600}
  `; }

  signature(hass) {
    return (this._config.rows || []).map((r) => txt(hass, r.entity, "")).join("|");
  }

  _fmt(e, r) {
    if (isUn(e)) return { text: DASH, cls: "none" };
    let v = e.state;
    if (r.format === "time") v = /^\d{2}:\d{2}/.test(v) ? v.slice(0, 5) : v;
    if (r.format === "mins") v = `${num(v) ?? v} min`;
    if (r.format === "hours") v = `${num(v) ?? v} h`;
    if (r.toggle) return { text: v === "on" ? "On" : "Off", cls: v === "on" ? "on" : "off" };
    if (!r.format && unit(e)) v = `${v} ${unit(e)}`;
    return { text: v || DASH, cls: v ? "" : "none" };
  }

  render(hass) {
    const rows = (this._config.rows || []).map((r, i) => {
      const e = hass.states[r.entity];
      const f = this._fmt(e, r);
      const stacked = r.stacked === true || String(f.text).length > 34;
      return `<div class="r ${stacked ? "stacked" : ""}" tabindex="0" role="button" data-i="${i}">
        <div class="l"><div class="lb">${esc(r.label || r.entity)}</div>${
          r.sub ? `<div class="sb">${esc(r.sub)}</div>` : ""}</div>
        <div class="v ${f.cls}">${esc(f.text)}</div>
      </div>`;
    }).join("");
    this.paint(`<div class="wrap">${rows}</div>`);

    this.shadowRoot.querySelectorAll(".r").forEach((el) => {
      const r = this._config.rows[Number(el.dataset.i)];
      const go = () => {
        if (r.toggle) { this._hass.callService("homeassistant", "toggle", { entity_id: r.entity }); return; }
        this.dispatchEvent(new CustomEvent("hass-more-info", {
          detail: { entityId: r.entity }, bubbles: true, composed: true,
        }));
      };
      el.addEventListener("click", go);
      el.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(); }
      });
    });
  }
}

/* ----------------------------- haiven-nearest ---------------------------
 * Who could get to her, on the home screen, so the question "should I ring
 * someone" is answered without leaving it. Nearest first, and the age of each
 * position is shown at the same size as the distance, because a number that
 * is six hours old is a different number.
 *
 * Deliberately not a map and not a call button. This card exists to say
 * whether help is close, and the decision about what to do with that belongs
 * to the person reading it.
 * --------------------------------------------------------------------- */

class HaivenNearest extends HaivenCard {
  get css() { return `
    .grid{display:grid;gap:1px;background:var(--line);border:1px solid var(--line);cursor:pointer}
    .grid:hover{background:var(--surface-2)}
    .grid:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
    .c{background:var(--surface);padding:14px 12px;display:flex;flex-direction:column;gap:5px;min-width:0}
    .top{display:flex;align-items:center;gap:7px;min-width:0}
    .dot{width:7px;height:7px;border-radius:50%;flex:0 0 auto}
    .nm{font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:var(--faint);
        font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .v{font-size:19px;color:var(--ink)}
    .v.none{color:var(--faint)}
    .v.here{color:var(--good);font-weight:600}
    .sub{font-size:11.5px;color:var(--faint);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .sub.stale{color:var(--warn)}
    .empty{background:var(--surface);border:1px solid var(--line);padding:15px 16px;
           font-size:13px;color:var(--faint)}
  `; }

  signature(hass) {
    return circleOf(hass, this._config)
      .map((p) => `${p.who}~${p.where}~${p.km}~${Math.round((p.age || 0) / 5)}`).join("|");
  }

  render(hass) {
    const n = Number(this._config.count || 2);
    const people = circleOf(hass, this._config).sort(byNearest).slice(0, n);

    if (!people.length) {
      this.paint(`<div class="empty">No one in the care circle yet ${DASH}</div>`);
      return;
    }

    const cells = people.map((p) => {
      const dot = p.missing ? "var(--faint)" : p.near ? "var(--good)" : "var(--muted)";
      // "At home" is about her house, so a carer who is there is worth more
      // than any distance and gets the word instead of the number.
      const atHers = !p.missing && /home/i.test(p.where) && !/not|away/i.test(p.where);
      const value = atHers ? "Here"
        : p.km === null ? DASH : withUnit(p.dist);
      // p.where is an entity state, so it is escaped like any other state.
      // The middot is the only markup allowed through.
      const sub = p.missing ? "no position"
        : p.stale ? `last known ${esc(relTime(p.age))}`
        : `${esc(p.where)} &middot; ${esc(relTime(p.age))}`;
      return `<div class="c">
        <div class="top"><div class="dot" style="background:${dot}"></div>
          <div class="nm">${esc(p.who)}</div></div>
        <div class="v mono ${atHers ? "here" : (p.km === null ? "none" : "")}">${esc(value)}</div>
        <div class="sub ${p.stale ? "stale" : ""}">${sub}</div>
      </div>`;
    }).join("");

    this.paint(`<div class="grid" tabindex="0" role="link"
      style="grid-template-columns:repeat(${people.length},minmax(0,1fr))">${cells}</div>`);

    const g = this.shadowRoot.querySelector(".grid");
    const open = () => goTo("/lovelace-haiven/circles");
    g.addEventListener("click", open);
    g.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
    });
  }
}

/* ------------------------------ haiven-camera ---------------------------
 * The last camera frame, what the model made of it, and a button to take a
 * fresh one. Together, because separately they are three cards that each
 * answer a third of the question.
 *
 * The image is fetched through media_source, which hands back a SIGNED,
 * expiring URL and requires authentication. The obvious alternative was to
 * copy the frame into /config/www and point an <img> at /local/latest.jpg,
 * which would have worked in one line and published a photo of an elderly
 * woman in her living room to anyone holding the Nabu Casa hostname, with no
 * login. Home Assistant serves /local with no auth at all.
 * --------------------------------------------------------------------- */

const FRAME_ID = "media-source://media_source/haiven/latest.jpg";

class HaivenCamera extends HaivenCard {
  get css() { return `
    .card{background:var(--surface);border:1px solid var(--line)}
    .shot{position:relative;background:var(--surface-2);aspect-ratio:16/9;overflow:hidden}
    .shot img{width:100%;height:100%;object-fit:cover;display:block}
    .none{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
          font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--faint)}
    .when{position:absolute;left:0;bottom:0;padding:5px 9px;font-size:10.5px;
          letter-spacing:.08em;text-transform:uppercase;font-weight:700;
          color:var(--on-status);background:rgba(0,0,0,.55)}
    .body{padding:14px 16px;display:flex;flex-direction:column;gap:11px}
    .v{font-size:14.5px;line-height:1.45;color:var(--ink)}
    .v.none{position:static;display:block;color:var(--faint);text-transform:none;
            letter-spacing:0;font-size:14px}
    .btns{display:flex;gap:8px}
    .b{appearance:none;border:1px solid var(--accent);background:var(--accent);
       color:var(--on-status);font:inherit;font-size:14px;font-weight:600;
       padding:13px 10px;cursor:pointer;min-height:48px;flex:1 1 0}
    .b.alt{background:var(--surface);color:var(--ink);border-color:var(--line)}
    .b.alt:hover{background:var(--surface-2)}
    .b:hover{filter:brightness(1.1)}
    .b:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
    .b[disabled]{opacity:.6;cursor:default}
    .live{position:absolute;inset:0}
    .live > *{width:100%;height:100%;display:block}
    .stamp{font-size:10px;letter-spacing:.1em;text-transform:uppercase;
           font-weight:700;color:var(--faint)}
  `; }

  signature(hass) {
    const e = hass.states[this._config.verdict_entity || "input_text.camera_check_verdict"];
    return `${this._looking ? "L" : ""}|${e ? e.state : ""}|${e ? e.last_changed : ""}`;
  }

  // media_source hands back a signed path that expires, so it is re-resolved
  // whenever the frame changes rather than cached for the life of the card.
  async _resolve() {
    try {
      const r = await this._hass.callWS({ type: "media_source/resolve_media", media_content_id: FRAME_ID });
      return r && r.url ? r.url : null;
    } catch (e) { return null; }
  }

  render(hass) {
    const vId = this._config.verdict_entity || "input_text.camera_check_verdict";
    const btn = this._config.button_entity || "input_button.check_camera";
    const e = hass.states[vId];
    const missing = isUn(e);
    const age = ageMin(hass, vId);

    // No battery row for a mains-powered camera: a percentage that reads 100%
    // forever looks like information and carries none. A value that never
    // changes is the stuck case, and printing it teaches the reader to trust a
    // reading that would not move if the camera were dying.

    this.paint(`<div class="card">
      <div class="shot">
        <div class="none" id="ph">${this._looking ? "Taking a fresh look&hellip;" : "No frame yet " + DASH}</div>
        <img id="img" alt="" style="display:none">
        ${age !== null && !missing ? `<div class="when" id="when">${esc(relTime(age))}</div>` : ""}
      </div>
      <div class="body">
        <div class="v ${missing ? "none" : ""}">${missing
          ? `Nothing looked at yet ${DASH}`
          : (this._live && age !== null
              // Live is showing now; the sentence is not. Without the stamp
              // "No person is visible" sits under a feed with someone in it.
              ? `<span class="stamp">${esc(relTime(age))}</span> ${esc(e.state)}`
              : esc(e.state))}</div>
        <div class="btns">
          <button class="b alt" id="live" type="button">${this._live ? "Stop live" : "Live view"}</button>
          <button class="b" id="check" type="button" ${this._looking ? "disabled" : ""}>${
            this._looking ? "Looking&hellip;" : "Check now"}</button>
        </div>
      </div>
    </div>`);

    if (this._live) this._mountLive();
    else this._resolve().then((url) => {
      if (!url || this._live) return;
      const img = this.shadowRoot.querySelector("#img");
      const ph = this.shadowRoot.querySelector("#ph");
      if (!img) return;
      img.onload = () => { img.style.display = "block"; if (ph) ph.remove(); };
      img.src = url;
    });

    this.shadowRoot.querySelector("#live").addEventListener("click", () => {
      this._live = !this._live; this._sig = null; this.render(this._hass);
    });

    this.shadowRoot.querySelector("#check").addEventListener("click", () => {
      if (this._looking) return;
      this._looking = true; this._sig = null; this.render(this._hass);
      this._hass.callService("input_button", "press", { entity_id: btn });
      // The camera has to wake and take the picture, then the model has to
      // look at it. Cleared by the verdict changing; this only unsticks the
      // button if that never happens.
      clearTimeout(this._t);
      this._t = setTimeout(() => { this._looking = false; this._sig = null; this.render(this._hass); }, 60000);
    });

    // A new verdict means the look finished.
    if (this._looking && e && e.last_changed !== this._seenAt) this._looking = false;
    this._seenAt = e ? e.last_changed : null;
  }

  // Home Assistant already knows how to play this camera: WebRTC live view is
  // what the phone app shows. Rather than reimplement the peer connection,
  // its own picture-entity card is built and dropped into the frame. That is
  // also why live works at all when every server-side path fails; the browser
  // talks to Ring directly and Home Assistant never decodes anything.
  async _mountLive() {
    const shot = this.shadowRoot.querySelector(".shot");
    if (!shot) return;
    const helpers = await window.loadCardHelpers();
    if (!this._live) return;
    const el = helpers.createCardElement({
      type: "picture-entity",
      entity: this._config.camera_entity || "camera.ring_camera_live_view",
      camera_view: "live",
      show_name: false,
      show_state: false,
    });
    el.hass = this._hass;
    const wrap = document.createElement("div");
    wrap.className = "live";
    wrap.appendChild(el);
    shot.replaceChildren(wrap);
    this._liveEl = el;
  }

  set hass(h) {
    super.hass = h;
    if (this._liveEl) this._liveEl.hass = h;   // keep the stream card fed
  }
  get hass() { return this._hass; }
}

/* ------------------------------- haiven-nav -----------------------------
 * The bottom bar, same idea as Willow Bank's wb2-nav. Home Assistant puts its
 * navigation in a top tab strip that is fine on a desktop and wrong on a
 * phone held one-handed: the tabs are at the far end of the screen from the
 * thumb, and there are only six of them.
 *
 * This mounts ITSELF rather than being placed as a card in each of the six
 * views. Two reasons. A fixed-position element in a sections grid still
 * occupies a grid slot, so it would leave a hole in every view; and the bar
 * belongs to the app, not to any one screen, so putting it in the YAML six
 * times invites the six copies to drift apart.
 *
 * It only appears on the Haiven dashboard. The library is loaded through
 * frontend.extra_module_url, which means it runs on every Home Assistant page
 * including Settings and HACS, and a Haiven bar over the HACS store would be
 * both wrong and confusing.
 * --------------------------------------------------------------------- */

const NAV_ROOT = "/lovelace-haiven";

const NAV_SVG = {
  home:     '<svg viewBox="0 0 24 24"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8h5Z"/></svg>',
  activity: '<svg viewBox="0 0 24 24"><path d="M3 13h3.5l2.5 6 4-14 2.5 8h5.5v2h-7l-1.5-5-3.5 12-4-9H3v-2Z"/></svg>',
  alerts:   '<svg viewBox="0 0 24 24"><path d="M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2m6-6v-5a6 6 0 0 0-5-5.91V4a1 1 0 0 0-2 0v1.09A6 6 0 0 0 6 11v5l-2 2v1h16v-1Z"/></svg>',
  circle:   '<svg viewBox="0 0 24 24"><path d="M12 12a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7m-6 .5a2.75 2.75 0 1 0 0-5.5 2.75 2.75 0 0 0 0 5.5m12 0a2.75 2.75 0 1 0 0-5.5 2.75 2.75 0 0 0 0 5.5M12 13.5c-2.7 0-6 1.34-6 3.5V19h12v-2c0-2.16-3.3-3.5-6-3.5M4.5 14C2.7 14.3 0 15.5 0 17.2V19h4.5v-2c0-1.1.5-2.1 1.3-2.8-.4-.1-.9-.2-1.3-.2m15 0c-.4 0-.9.1-1.3.2.8.7 1.3 1.7 1.3 2.8v2H24v-1.8c0-1.7-2.7-2.9-4.5-3.2Z"/></svg>',
  sensors:  '<svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20m0 3.5a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"/></svg>',
  settings: '<svg viewBox="0 0 24 24"><path d="M12 15.5A3.5 3.5 0 1 1 15.5 12 3.5 3.5 0 0 1 12 15.5m7.43-2.53q.07-.48.07-.97t-.07-1l2.11-1.63a.5.5 0 0 0 .12-.64l-2-3.46a.5.5 0 0 0-.61-.22l-2.49 1a7.3 7.3 0 0 0-1.69-.98l-.37-2.65A.51.51 0 0 0 14 2h-4a.51.51 0 0 0-.5.42l-.37 2.65c-.63.25-1.17.59-1.69.98l-2.49-1a.5.5 0 0 0-.61.22l-2 3.46a.5.5 0 0 0 .12.64L4.57 11q-.07.5-.07 1t.07.97l-2.11 1.66a.5.5 0 0 0-.12.64l2 3.46a.5.5 0 0 0 .61.22l2.49-1.01c.52.4 1.06.74 1.69.99l.37 2.65a.51.51 0 0 0 .5.42h4a.51.51 0 0 0 .5-.42l.37-2.65c.63-.26 1.17-.59 1.69-.99l2.49 1.01a.5.5 0 0 0 .61-.22l2-3.46a.5.5 0 0 0-.12-.64Z"/></svg>',
  ha:       '<svg viewBox="0 0 24 24"><path d="M12 2 2 12h3v8h14v-8h3L12 2m0 5.2 4 4V18h-8v-6.8l4-4Z"/></svg>',
  more:     '<svg viewBox="0 0 24 24"><path d="M16 12a2 2 0 1 1 4 0 2 2 0 0 1-4 0m-6 0a2 2 0 1 1 4 0 2 2 0 0 1-4 0m-6 0a2 2 0 1 1 4 0 2 2 0 0 1-4 0Z"/></svg>',
};

// Five in the bar, the rest behind More. The split is by how often a carer
// actually taps them, not by how much work each screen took to build.
const NAV_MAIN = [
  { p: "home",     i: "home",     l: "Home" },
  { p: "activity", i: "activity", l: "Activity" },
  { p: "alerts",   i: "alerts",   l: "Alerts" },
  { p: "circles",  i: "circle",   l: "Circle" },
];
const NAV_MORE = [
  { p: "sensors",  i: "sensors",  l: "Sensors" },
  { p: "settings", i: "settings", l: "Settings" },
  { p: "config/dashboard", i: "ha", l: "Home Assistant", ext: true },
];

class HaivenNav extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._open = false;
    this._onLoc = () => this._sync();
  }

  connectedCallback() {
    if (!this._built) this._build();
    window.addEventListener("location-changed", this._onLoc);
    window.addEventListener("popstate", this._onLoc);
    this._sync();
  }

  disconnectedCallback() {
    window.removeEventListener("location-changed", this._onLoc);
    window.removeEventListener("popstate", this._onLoc);
  }

  _onHaiven() { return location.pathname.startsWith(NAV_ROOT + "/"); }
  _cur() { const m = location.pathname.match(/\/lovelace-haiven\/([^/]+)/); return m ? m[1] : ""; }

  _go(item) {
    this._open = false;
    if (item.ext) { window.location.href = "/" + item.p; return; }
    history.pushState(null, "", `${NAV_ROOT}/${item.p}`);
    window.dispatchEvent(new CustomEvent("location-changed", { bubbles: true, composed: true }));
    this._sync();
  }

  _sync() {
    const on = this._onHaiven();
    this.hidden = !on;
    // The bar covers the bottom of the scroll area, so the last card on a
    // long view would sit underneath it. Push the view's own padding down
    // instead of adding a spacer card to all six views.
    padViewForNav(on);
    if (!on) return;
    const cur = this._cur();
    this.shadowRoot.querySelectorAll("[data-p]").forEach((b) =>
      b.classList.toggle("cur", b.dataset.p === cur));
    const inMore = NAV_MORE.some((m) => m.p === cur);
    this.shadowRoot.querySelector(".more").classList.toggle("cur", inMore || this._open);
    this.shadowRoot.querySelector(".sub").classList.toggle("open", this._open);
  }

  _build() {
    this._built = true;
    this.shadowRoot.innerHTML = `<style>${THEME}
      :host{position:fixed;left:0;right:0;bottom:0;z-index:6}
      :host([hidden]){display:none}
      .sub{position:absolute;right:10px;bottom:calc(100% + 6px);background:var(--surface);
           border:1px solid var(--line);box-shadow:0 8px 24px rgba(0,0,0,.18);padding:5px;
           display:none;flex-direction:column;min-width:180px}
      .sub.open{display:flex}
      .sub button{display:flex;align-items:center;gap:10px;text-align:left;border:0;
                  background:transparent;color:var(--ink);font:inherit;font-size:14px;
                  font-weight:600;padding:11px 12px;cursor:pointer}
      .sub button:hover{background:var(--surface-2)}
      .sub button.cur{color:var(--accent)}
      .sub button span{width:19px;height:19px;flex:none;color:var(--muted)}
      .sub button.cur span{color:var(--accent)}
      .sub svg{width:100%;height:100%;fill:currentColor;display:block}
      nav{background:var(--surface);border-top:1px solid var(--line);display:flex;
          justify-content:space-around;padding:7px 4px calc(6px + env(safe-area-inset-bottom))}
      nav button{border:0;background:transparent;color:var(--faint);display:flex;
                 flex-direction:column;align-items:center;gap:3px;font:inherit;font-size:10.5px;
                 font-weight:600;letter-spacing:.02em;padding:4px 6px;cursor:pointer;
                 min-width:56px;min-height:48px}
      nav button .g{width:23px;height:23px}
      nav button .g svg{width:100%;height:100%;fill:currentColor;display:block}
      nav button.cur{color:var(--accent)}
      nav button:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
    </style>
    <div class="sub">${NAV_MORE.map((m) =>
      `<button data-p="${m.p}"><span>${NAV_SVG[m.i]}</span>${m.l}</button>`).join("")}</div>
    <nav>
      ${NAV_MAIN.map((n) =>
        `<button data-p="${n.p}"><span class="g">${NAV_SVG[n.i]}</span>${n.l}</button>`).join("")}
      <button class="more"><span class="g">${NAV_SVG.more}</span>More</button>
    </nav>`;

    const sr = this.shadowRoot;
    NAV_MAIN.forEach((n) => sr.querySelector(`nav [data-p="${n.p}"]`)
      .addEventListener("click", () => this._go(n)));
    NAV_MORE.forEach((m) => sr.querySelector(`.sub [data-p="${m.p}"]`)
      .addEventListener("click", () => this._go(m)));
    sr.querySelector(".more").addEventListener("click", () => { this._open = !this._open; this._sync(); });
    // Tapping anywhere else closes the submenu, which is what every phone does.
    document.addEventListener("click", (e) => {
      if (this._open && !e.composedPath().includes(this)) { this._open = false; this._sync(); }
    });
  }
}

/* Bottom padding for the view underneath the bar. HA's view container lives
 * inside hui-root's shadow root, so a document stylesheet cannot reach it and
 * the style has to be injected into that root. The lookup is a walk rather
 * than a fixed path because the element chain above hui-root changes between
 * Home Assistant releases; the walk only cares that hui-root exists. */
let _padSheet = null, _padTries = 0;
function padViewForNav(on) {
  const root = findShadow("hui-root");
  if (!root) {
    // The bar mounts on module load, which is before Home Assistant has
    // rendered the dashboard, so the first attempt always misses. Without a
    // retry the style never lands at all and the last card on every view
    // spends its life under the bar.
    if (_padTries++ < 60) setTimeout(() => padViewForNav(on), 250);
    return;
  }
  _padTries = 0;
  if (!_padSheet || !root.contains(_padSheet)) {
    _padSheet = document.createElement("style");
    root.appendChild(_padSheet);
  }
  // Every container HA has used for the view body across recent releases.
  // Padding rather than a margin, so it grows the scrollable box instead of
  // pushing a fixed-height one off the bottom.
  _padSheet.textContent = on
    ? `#view, hui-view, hui-view-container, hui-sections-view, hui-masonry-view,
       hui-panel-view, hui-sidebar-view{padding-bottom:92px !important}`
    : "";
}

function findShadow(tag, root = document, depth = 0) {
  if (depth > 12) return null;
  for (const el of root.querySelectorAll("*")) {
    if (el.tagName.toLowerCase() === tag) return el.shadowRoot;
    if (el.shadowRoot) { const hit = findShadow(tag, el.shadowRoot, depth + 1); if (hit) return hit; }
  }
  return null;
}

// Mount once, and only once, however many times the module is evaluated.
function mountNav() {
  if (document.querySelector("haiven-nav")) return;
  document.body.appendChild(document.createElement("haiven-nav"));
}

// Guarded, because customElements.define throws on a repeat name and one
// throw kills the whole module: every card after it silently fails to
// register. That can happen from a stale Lovelace resource loading the file a
// second time alongside the loader.
const define = (name, cls) => { if (!customElements.get(name)) customElements.define(name, cls); };

define("haiven-status",  HaivenStatus);
define("haiven-facts",   HaivenFacts);
define("haiven-rooms",   HaivenRooms);
define("haiven-section", HaivenSection);
define("haiven-tabs",    HaivenTabs);
define("haiven-ribbon",  HaivenRibbon);
define("haiven-compare", HaivenCompare);
define("haiven-drift",   HaivenDrift);
define("haiven-movement", HaivenMovement);
define("haiven-where",   HaivenWhere);
define("haiven-devices", HaivenDevices);
define("haiven-people",  HaivenPeople);
define("haiven-alerts",  HaivenAlerts);
define("haiven-actions", HaivenActions);
define("haiven-rows",    HaivenRows);
define("haiven-nearest", HaivenNearest);
define("haiven-camera",  HaivenCamera);
define("haiven-nav",     HaivenNav);

window.customCards = window.customCards || [];
window.customCards.push(
  { type: "haiven-status",  name: "Haiven Status",  description: "AI summary with coverage-qualified status" },
  { type: "haiven-facts",   name: "Haiven Facts",   description: "Three figures, facts only" },
  { type: "haiven-rooms",   name: "Haiven Rooms",   description: "Per-room last activity with coverage state" },
  { type: "haiven-section", name: "Haiven Section", description: "Small uppercase section heading" },
  { type: "haiven-tabs",    name: "Haiven Tabs",    description: "Sub-tabs inside one view" },
  { type: "haiven-ribbon",  name: "Haiven Ribbon",  description: "Day ribbon: per-room activity across a rolling window" },
  { type: "haiven-compare", name: "Haiven Compare", description: "Today against her own baseline" },
  { type: "haiven-drift",   name: "Haiven Drift",   description: "A month of nights against a frozen baseline" },
  { type: "haiven-movement", name: "Haiven Movement", description: "Today's all-room trigger count against a 7-day average by now" },
  { type: "haiven-where",   name: "Haiven Where",   description: "Triangulated room with confidence" },
  { type: "haiven-devices", name: "Haiven Devices", description: "Sensor health and what stops working without it" },
  { type: "haiven-people",  name: "Haiven People",  description: "Care circle with position freshness" },
  { type: "haiven-alerts",  name: "Haiven Alerts",  description: "Live conditions, worst first" },
  { type: "haiven-actions", name: "Haiven Actions", description: "Buttons that call a service" },
  { type: "haiven-rows",    name: "Haiven Rows",    description: "Entity list, tap for more-info" },
  { type: "haiven-nearest", name: "Haiven Nearest", description: "Closest carers, freshness included" },
  { type: "haiven-camera",  name: "Haiven Camera",  description: "Last frame, the verdict on it, and a fresh look" },
);

// The bar is not a card and is never placed in a view; it mounts itself.
if (document.body) mountNav();
else document.addEventListener("DOMContentLoaded", mountNav);

console.info("%c HAIVEN-CARDS %c v6 ", "background:#1F5459;color:#fff", "background:#EFEBE4;color:#1A1815");
