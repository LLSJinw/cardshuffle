# streamlit_app.py
# Phased TTX deck (2×2 grid), flip/zoom, admin controls.
# Real-drill: Phase1=3 cards; Phases2–4=2 cards each.
# Supports real images under /assets; falls back to generated placeholders.

import os
import base64, io, random, textwrap
from typing import Dict, List, Tuple
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps

st.set_page_config(page_title="TTX Phased Deck", page_icon="🃏", layout="wide")

# ---------- Assets ----------
ASSET_DIR = "assets"  # holds back.png, card01.png, card02.png, ...

def load_image_b64(filename: str) -> str:
    """Read an image from assets and return base64 string."""
    path = os.path.join(ASSET_DIR, filename)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

# ---------- Background (1920x1080 recommended) ----------
BG_PATH = "BG.png"
with open(BG_PATH, "rb") as f:
    bg_base64 = base64.b64encode(f.read()).decode()

# CSS + Title (fix stray quote)
st.markdown(f"""
<style>
/* App background & dark theme */
.stApp {{
  background: url("data:image/png;base64,{bg_base64}") no-repeat center center fixed;
  background-size: cover;
  background-color: #0e1525 !important;
  color: #fff !important;
}}

.title-bg {{
  font-size: 1.8rem;                 /* similar to st.title */
  font-weight: 800;
  margin: .25rem 0 .35rem 0;
  display: inline-block;
  background: rgba(0,0,0,.50);       /* dark translucent slab */
  padding: .35rem .65rem;
  border-radius: 10px;
}}
.block-container, header, .st-emotion-cache-18ni7ap, .st-emotion-cache-1v0mbdj {{
  background: transparent !important;
  box-shadow: none !important;
  backdrop-filter: none !important;
}}
/* Sidebar clean dark */
[data-testid="stSidebar"] {{
  background: rgba(10,15,25,1) !important;
  color: #fff !important;
  box-shadow: none !important;
}}
[data-testid="stSidebar"] > div:first-child {{
  background: transparent !important;
}}

/* Phase container styling */
.phase-box {{ padding: .25rem .35rem .6rem .35rem; border-radius: 10px; }}
.phase-title {{  margin: 0 0 .25rem 0;
  font-weight: 700;
  font-size: 1.05rem;
  background: rgba(0,0,0,.45);
  display: inline-block;
  padding: .25rem .5rem;
  border-radius: 8px;
  line-height: 1.2; }}
.hr-compact  {{ margin: 0.6rem 0 1rem 0; border: 0; height: 1px; background: rgba(255,255,255,.15); }}
.badge {{
  display:inline-block; padding:.15rem .45rem; margin-left:.35rem;
  border-radius: 999px; font-size:.75rem; background:rgba(255,255,255,.12);
}}

/* Card + Flip */
.card-container {{ perspective: 1000px; }}
.card {{
  width: 288px;              /* <- fixed width */
  height: 432px;             /* <- fixed height (2:3) */
  margin: 0 auto;            /* center in its column */
  position: relative;
}}
.card-inner {{
  position: absolute; width: 100%; height: 100%;
  transform-style: preserve-3d; transition: transform 0.6s ease;
}}
.flipped .card-inner {{ transform: rotateY(180deg); }}
.card-face {{ position: absolute; width: 100%; height: 100%;
  -webkit-backface-visibility: hidden; backface-visibility: hidden;
  border-radius: 12px; overflow: hidden; }}
.card-front {{ transform: rotateY(0deg); }}
.card-back  {{ transform: rotateY(180deg); }}
.img-fit {{ width: 100%; height: 100%; object-fit: cover; }}

/* Zoom overlay (CSS-only modal) */
.overlay {{
  position: fixed; inset: 0; background: rgba(0,0,0,0.72);
  display: flex; align-items: center; justify-content: center;
  z-index: 2147483646; pointer-events: none;
}}
.overlay .cardwrap {{
  max-width: min(90vw, 900px);     /* wider */
  transform: scale(1.00);          /* +25% zoom */
  border-radius: 20px; overflow: hidden;
  box-shadow: 0 10px 30px rgba(0,0,0,0.55);
  pointer-events: auto;
}}
.overlay img {{ width: 100%; height: auto; display:block; }}

/* Floating close button on stage */
.closebar {{
  position: fixed; bottom: 18px; left: 18px;
  z-index: 2147483647;
}}
.closebar .stButton > button {{
  position: relative; font-weight: 700;
  box-shadow: 0 6px 16px rgba(0,0,0,0.35);
}}
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="title-bg">Phased TTX Card Deck (All Phases)</div>', unsafe_allow_html=True)

# ---------- Cards (now 20% smaller on board) ----------
CARD_W, CARD_H = 288, 432   # 360x540 * 0.8

TEAMS = ["Team A", "Team B"]

# Phase pools (keep all Qs/What-Ifs here)
PHASES = {
    "Phase 1 – Detection & Analysis": ["Q1", "Q2", "Q3"],
    "Phase 2 – Containment & Eradication": ["Q4", "Q5", "Q6"],
    "Phase 3 – Recovery": ["Q7", "Q8", "Q9"],
    "Phase 4 – Post-Incident": ["Q10", "Q11", "Q12"],
}

# Deal counts per phase (3, 2, 2, 2)
PHASE_DEAL_COUNT = {
    "Phase 1 – Detection & Analysis": 3,
    "Phase 2 – Containment & Eradication": 2,
    "Phase 3 – Recovery": 2,
    "Phase 4 – Post-Incident": 2,
}

# Flip limits per phase (3, 2, 2, 2)
PHASE_FLIP_LIMIT = {
    "Phase 1 – Detection & Analysis": 3,
    "Phase 2 – Containment & Eradication": 2,
    "Phase 3 – Recovery": 2,
    "Phase 4 – Post-Incident": 2,
}

STORY = {
    "Q1":  "Strategic: Activate CIRP immediately?",
    "Q2":  "Tactical: First containment action?",
    "Q3":  "Operational: HR calm comms?",
    "Q4":  "Strategic: Partner notification timing?",
    "Q5":  "Tactical: Isolate repos/servers?",
    "Q6":  "Operational: Contact-center message?",
    "Q7":  "Strategic: Ransom stance (LE & backups)?",
    "Q8":  "Tactical: Verify backup integrity first?",
    "Q9":  "Operational: Staff breach notice?",
    "Q10": "Strategic: Improve CIRP + BCP?",
    "Q11": "Tactical: Backup test + EDR + awareness?",
    "Q12": "Wildcard: Chaos card / random constraint",
}

# ---------- Fallback card drawing (used if an image is missing) ----------
def get_font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default()

def draw_card_back() -> Image.Image:
    NAVY=(16,34,64); WHITE=(248,251,255)
    img = Image.new("RGB", (CARD_W, CARD_H), NAVY)
    d = ImageDraw.Draw(img)
    for x in range(-CARD_H, CARD_W+CARD_H, 36):
        d.line([(x,0),(x+CARD_H,CARD_H)], fill=(255,255,255,32), width=2)
    d.text((CARD_W//2, CARD_H//2-40), "🦉", anchor="mm", fill=WHITE)
    img = ImageOps.expand(img, border=8, fill=(240,244,252))
    img = ImageOps.expand(img, border=3, fill=(220,226,236))
    return img

def draw_front(label: str, subtitle: str) -> Image.Image:
    NAVY=(16,34,64); STRIPE=(208,213,221); LIGHT=(236,240,248)
    img = Image.new("RGB", (CARD_W, CARD_H), NAVY)
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(CARD_H*0.16), CARD_W, int(CARD_H*0.19)], fill=STRIPE)
    d.rectangle([0, int(CARD_H*0.72), CARD_W, int(CARD_H*0.75)], fill=STRIPE)
    d.text((CARD_W//2, int(CARD_H*0.30)), label, anchor="mm", fill=LIGHT, font=get_font(68))
    wrapped = textwrap.fill(subtitle, width=22)
    d.multiline_text((CARD_W//2, int(CARD_H*0.55)), wrapped, anchor="mm",
                     fill=LIGHT, font=get_font(24), align="center")
    img = ImageOps.expand(img, border=8, fill=(240,244,252))
    img = ImageOps.expand(img, border=3, fill=(220,226,236))
    return img

def pil_to_b64(img) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

# ---------- State ----------
def init():
    if "cards" in st.session_state:
        return

    # Load back image (fallback to drawn back if missing)
    try:
        back_b64 = load_image_b64("back.png")
    except Exception:
        back_b64 = pil_to_b64(draw_card_back())

    cards: Dict[str, List[Dict]] = {}
    for ph, ids in PHASES.items():
        ids_pool = ids[:]
        random.shuffle(ids_pool)
        # DEAL only 3 / 2 / 2 / 2 per phase
        deal_n = PHASE_DEAL_COUNT.get(ph, len(ids_pool))
        chosen = ids_pool[:deal_n]

        phase_cards = []
        for qid in chosen:
            # Map Q-id like "Q7" -> "card07.png"
            try:
                qnum = int(qid[1:])
            except ValueError:
                qnum = 0  # safety; will fall back to placeholder
            img_filename = f"card{qnum:02}.png"
            img_path = os.path.join(ASSET_DIR, img_filename)

            # Use real front if exists, else draw placeholder
            if os.path.exists(img_path):
                try:
                    front_b64 = load_image_b64(img_filename)
                except Exception:
                    front_b64 = pil_to_b64(draw_front(qid, STORY.get(qid, "")))
            else:
                front_b64 = pil_to_b64(draw_front(qid, STORY.get(qid, "")))

            phase_cards.append({
                "id": qid,
                "front": front_b64,
                "back": back_b64,
                "flipped": False,
                "owner": None,
            })

        cards[ph] = phase_cards

    st.session_state.cards = cards
    st.session_state.turn = 0
    st.session_state.score = {t: 0 for t in TEAMS}
    st.session_state.zoom: Tuple[str, int] | None = None

init()

# ---------- Admin / helpers ----------
def reset_all():
    st.session_state.pop("cards", None)
    init()

def shuffle_unflipped_in_phase(phase_name: str):
    pcs = st.session_state.cards[phase_name]
    flipped = [c for c in pcs if c["flipped"]]
    unflipped = [c for c in pcs if not c["flipped"]]
    random.shuffle(unflipped)
    st.session_state.cards[phase_name] = flipped + unflipped

def phase_effective_limit(phase_name: str, enforce: bool, global_limit: int) -> int:
    """Respect old sidebar controls but enforce 3/2/2/2 when 'enforce' is True."""
    if not enforce:
        return 0  # unlimited
    return PHASE_FLIP_LIMIT.get(phase_name, global_limit or 0)

def can_flip(phase_name: str, enforce: bool, limit: int, reveal_all: bool) -> bool:
    if reveal_all:
        return True
    eff_limit = phase_effective_limit(phase_name, enforce, limit)
    if eff_limit == 0:
        return True
    pcs = st.session_state.cards[phase_name]
    return sum(c["flipped"] for c in pcs) < eff_limit

def flip_card(phase_name: str, idx: int):
    card = st.session_state.cards[phase_name][idx]
    if card["flipped"]:
        return
    team = TEAMS[st.session_state.turn]
    card["flipped"] = True
    card["owner"] = team
    st.session_state.score[team] += 1
    st.session_state.turn = 1 - st.session_state.turn

def toggle_zoom(phase_name: str, idx: int):
    st.session_state.zoom = None if st.session_state.zoom == (phase_name, idx) else (phase_name, idx)

def close_zoom():
    st.session_state.zoom = None

# ---------- Sidebar (old UI preserved) ----------
with st.sidebar:
    st.header("Admin / Demo Controls")
    if st.session_state.get("zoom") is not None:
        st.button("✕ Close Zoom (Admin)", on_click=close_zoom, type="primary", use_container_width=True)
        st.caption("Visible only while a card is zoomed.")
        st.markdown("---")

    enforce_limit = st.checkbox("Enforce phase limit", value=True)
    limit_per_phase = st.number_input("Limit per phase (0 = unlimited)", min_value=0, max_value=3, value=2, step=1)
    st.caption("Tip: set 0 or toggle off to allow opening the 3rd card.")

    st.markdown("---")
    st.subheader("Per-Phase Override")
    phase_reveal_flags: Dict[str, bool] = {}
    for ph in PHASES:
        phase_reveal_flags[ph] = st.checkbox(f"Reveal all in {ph}", value=False, key=f"reveal_{ph}")
    st.markdown("---")
    st.button("🔄 Reset All", on_click=reset_all, use_container_width=True)
    for ph in PHASES:
        st.button(f"🔀 Shuffle Unflipped – {ph}", on_click=shuffle_unflipped_in_phase,
                  args=(ph,), use_container_width=True, key=f"shuf_{ph}")

    st.markdown("---")
    st.header("Teams & Score")
    st.write(f"**Current Turn:** {TEAMS[st.session_state.turn]}")
    for t in TEAMS:
        st.write(f"- {t}: {st.session_state.score[t]}")

    st.markdown("---")
    st.header("🎲 Quick Random Assignment")

    if st.button("Randomize Phase Assignment", use_container_width=True, type="primary"):
        all_phases = list(PHASES.keys())
        random.shuffle(all_phases)
        # Split 4 phases → 2 for Team A, 2 for Team B
        team_a_phases = all_phases[:2]
        team_b_phases = all_phases[2:]
        st.session_state["team_phase_map"] = {
            "Team A": team_a_phases,
            "Team B": team_b_phases
        }

    # Show current assignment (if any)
    if "team_phase_map" in st.session_state:
        st.subheader("Current Phase Assignment")
        for team, phases in st.session_state["team_phase_map"].items():
            st.write(f"**{team}:** {', '.join(phases)}")
    else:
        st.caption("Press the button above to randomly assign phases to each team.")


# ---------- Main: 2×2 Grid of Phases ----------
st.caption("Inject 1 flips up to 3 cards; Inject 2–4 flip up to 2. Click **Zoom** on a flipped card.")

def render_phase(phase_name: str):
    pcs = st.session_state.cards[phase_name]
    picked = sum(c["flipped"] for c in pcs)
    eff_limit = phase_effective_limit(phase_name, enforce_limit, limit_per_phase)
    limit_txt = f"{eff_limit if eff_limit else '∞'}"
    st.markdown(
        f'<div class="phase-title">{phase_name} '
        f'<span class="badge">{picked}/{limit_txt}</span></div>',
        unsafe_allow_html=True
    )
    # columns adapt to the number of dealt cards for this phase
    cols = st.columns(len(pcs), gap="small")
    for i, col in enumerate(cols):
        with col:
            card = pcs[i]
            front = f"data:image/png;base64,{card['front']}"
            back  = f"data:image/png;base64,{card['back']}"
            flipped_class = "flipped" if card["flipped"] else ""
            st.markdown(f"""
            <div class="card-container">
              <div class="card {flipped_class}">
                <div class="card-inner">
                  <div class="card-face card-front">
                    <img class="img-fit" src="{back}"/>
                  </div>
                  <div class="card-face card-back">
                    <img class="img-fit" src="{front}"/>
                  </div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            b1, b2 = st.columns(2, gap="small")
            with b1:
                flip_disabled = card["flipped"] or not can_flip(
                    phase_name, enforce_limit, limit_per_phase, phase_reveal_flags[phase_name]
                )
                st.button("Flip", key=f"flip_{phase_name}_{i}", on_click=flip_card,
                          args=(phase_name, i), disabled=flip_disabled, use_container_width=True)
            with b2:
                st.button("Zoom", key=f"zoom_{phase_name}_{i}", on_click=toggle_zoom,
                          args=(phase_name, i), disabled=not card["flipped"], use_container_width=True)
            if card["flipped"]:
                st.caption(f"**{card['id']}** → {card['owner']}")
                st.caption(STORY.get(card["id"], ""))

# 2×2 matrix layout
row1 = st.columns(2, gap="large")
with row1[0]:
    st.markdown('<div class="phase-box">', unsafe_allow_html=True)
    render_phase("Phase 1 – Detection & Analysis")
    st.markdown('</div>', unsafe_allow_html=True)
with row1[1]:
    st.markdown('<div class="phase-box">', unsafe_allow_html=True)
    render_phase("Phase 2 – Containment & Eradication")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<hr class="hr-compact">', unsafe_allow_html=True)

row2 = st.columns(2, gap="large")
with row2[0]:
    st.markdown('<div class="phase-box">', unsafe_allow_html=True)
    render_phase("Phase 3 – Recovery")
    st.markdown('</div>', unsafe_allow_html=True)
with row2[1]:
    st.markdown('<div class="phase-box">', unsafe_allow_html=True)
    render_phase("Phase 4 – Post-Incident")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Zoom overlay ----------
if st.session_state.zoom is not None:
    ph, idx = st.session_state.zoom
    card = st.session_state.cards[ph][idx]
    img_b64 = card["front"] if card["flipped"] else card["back"]
    st.markdown(f"""
    <div class="overlay">
      <div class="cardwrap">
        <img src="data:image/png;base64,{img_b64}" />
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="closebar">', unsafe_allow_html=True)
    st.button("✕ Close Zoom", on_click=close_zoom, type="primary")
    st.markdown('</div>', unsafe_allow_html=True)
