# streamlit_app.py
# Phased TTX deck with two teams, flip/zoom, and admin controls for phase limits.
# Production-safe zoom (CSS only) + Sidebar Close button (visible only when zoom is active)

import base64, io, random, textwrap
from typing import Dict, List, Tuple
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps

st.set_page_config(page_title="TTX Phased Deck", page_icon="🃏", layout="wide")
import base64, io
from PIL import Image
import streamlit as st

def _b64_bg(path: str) -> str:
    img = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()

# choose one: "cover" (hero) or "repeat-y" (tactile vertical)
BG_MODE = st.session_state.get("BG_MODE", "cover")  # or set in sidebar later
BG_B64 = _b64_bg("BG.png")

if BG_MODE == "cover":
    # Fullscreen responsive hero image, fixed for subtle parallax
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{
      background-image: url("data:image/png;base64,{BG_B64}");
      background-size: cover;
      background-position: center center;
      background-repeat: no-repeat;
      background-attachment: fixed;
    }}
    /* Sidebar can be tinted to maintain readability (optional) */
    [data-testid="stSidebar"] > div:first-child {{
      backdrop-filter: blur(2px);
      background: rgba(255,255,255,0.70);
    }}
    /* Main content readability layer (optional, subtle) */
    .block-container {{
      background: rgba(255,255,255,0.70);
      border-radius: 12px;
      padding: 1rem 1.25rem;
    }}
    </style>
    """, unsafe_allow_html=True)
else:
    # Tactile vertical pattern (repeat-y), fixed width, centered
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{
      background-image: url("data:image/png;base64,{BG_B64}");
      background-repeat: repeat-y;
      background-position: top center;
      background-size: 1920px auto;   /* lock width, keep aspect */
      background-attachment: scroll;  /* follow page scroll */
    }}
    [data-testid="stSidebar"] > div:first-child {{
      backdrop-filter: blur(2px);
      background: rgba(255,255,255,0.75);
    }}
    .block-container {{
      background: rgba(255,255,255,0.78);
      border-radius: 12px;
      padding: 1rem 1.25rem;
    }}
    </style>
    """, unsafe_allow_html=True)
# --------------------- layout / style ---------------------
CARD_W, CARD_H = 360, 540  # size used for generated PNGs
TEAMS = ["Team A", "Team B"]

PHASES = {
    "Phase 1 – Detection & Analysis": ["Q1", "Q2", "Q3"],
    "Phase 2 – Containment & Eradication": ["Q4", "Q5", "Q6"],
    "Phase 3 – Recovery": ["Q7", "Q8", "Q9"],
    "Phase 4 – Post-Incident": ["Q10", "Q11", "Q12"],
}

# One-line prompts (replace with your real injects later)
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

# --------------------- image generation ---------------------
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
    d.text((CARD_W//2, int(CARD_H*0.30)), label, anchor="mm", fill=LIGHT, font=get_font(72))
    wrapped = textwrap.fill(subtitle, width=22)
    d.multiline_text((CARD_W//2, int(CARD_H*0.55)), wrapped, anchor="mm",
                     fill=LIGHT, font=get_font(26), align="center")
    img = ImageOps.expand(img, border=8, fill=(240,244,252))
    img = ImageOps.expand(img, border=3, fill=(220,226,236))
    return img

def pil_to_b64(img) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

# --------------------- state init ---------------------
def init():
    if "cards" in st.session_state:
        return
    back_b64 = pil_to_b64(draw_card_back())
    cards: Dict[str, List[Dict]] = {}
    for ph, ids in PHASES.items():
        ids = ids[:]
        random.shuffle(ids)
        phase_cards = []
        for qid in ids:
            phase_cards.append({
                "id": qid,
                "front": pil_to_b64(draw_front(qid, STORY.get(qid, ""))),
                "back": back_b64,
                "flipped": False,
                "owner": None,  # Team A / Team B
            })
        cards[ph] = phase_cards
    st.session_state.cards = cards
    st.session_state.turn = 0
    st.session_state.score = {t: 0 for t in TEAMS}
    st.session_state.zoom: Tuple[str,int] | None = None

init()

# --------------------- admin & helpers ---------------------
def reset_all():
    st.session_state.pop("cards", None)
    init()

def shuffle_unflipped_in_phase(phase_name: str):
    pcs = st.session_state.cards[phase_name]
    flipped = [c for c in pcs if c["flipped"]]
    unflipped = [c for c in pcs if not c["flipped"]]
    random.shuffle(unflipped)
    st.session_state.cards[phase_name] = flipped + unflipped

def can_flip(phase_name: str, enforce: bool, limit: int, reveal_all: bool) -> bool:
    if not enforce or limit == 0 or reveal_all:
        return True
    pcs = st.session_state.cards[phase_name]
    return sum(c["flipped"] for c in pcs) < limit

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

# --------------------- CSS for flip & overlay zoom (no JS) ---------------------
st.markdown("""
<style>
.card-container { perspective: 1000px; }
.card { width: 100%; aspect-ratio: 2 / 3; position: relative; }
.card-inner {
  position: absolute; width: 100%; height: 100%;
  transform-style: preserve-3d; transition: transform 0.6s ease;
}
.flipped .card-inner { transform: rotateY(180deg); }
.card-face { position: absolute; width: 100%; height: 100%;
  -webkit-backface-visibility: hidden; backface-visibility: hidden;
  border-radius: 12px; overflow: hidden; }
.card-front { transform: rotateY(0deg); }
.card-back  { transform: rotateY(180deg); }
.img-fit { width: 100%; height: 100%; object-fit: cover; }

/* Overlay that looks like a modal but uses CSS only */
.overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.72);
  display: flex; align-items: center; justify-content: center;
  z-index: 2147483646;
  pointer-events: none;               /* background ignores clicks */
}
.overlay .cardwrap {
  max-width: min(72vw, 760px);
  border-radius: 16px; overflow: hidden;
  box-shadow: 0 10px 30px rgba(0,0,0,0.45);
  pointer-events: auto;               /* the card itself can accept clicks if needed */
}
.overlay img { width: 100%; height: auto; display:block; }

/* Floating close button on stage */
.closebar {
  position: fixed; bottom: 18px; left: 18px;
  z-index: 2147483647;               /* higher than overlay */
}
.closebar .stButton > button {
  position: relative; font-weight: 700;
  box-shadow: 0 6px 16px rgba(0,0,0,0.35);
}
</style>
""", unsafe_allow_html=True)

# --------------------- SIDEBAR: Admin + Teams ---------------------
with st.sidebar:
    st.header("Admin / Demo Controls")

    # Context-aware Close Zoom (only shows when zoom is active)
    if st.session_state.get("zoom") is not None:
        st.button("✕ Close Zoom (Admin)", on_click=close_zoom, type="primary", use_container_width=True)
        st.caption("Visible only while a card is in zoom mode.")
        st.markdown("---")

    enforce_limit = st.checkbox("Enforce phase limit", value=True)
    limit_per_phase = st.number_input("Limit per phase (0 = unlimited)", min_value=0, max_value=3, value=2, step=1)
    st.caption("Tip: set 0 or toggle off to allow opening the 3rd card for fun.")

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

# --------------------- MAIN: Phases grid ---------------------
st.title("Phased TTX Card Deck")
st.caption("Flip any 2 of 3 per phase (unless admin disables the limit). Click **Zoom** on a flipped card to present it fullscreen.")

for phase_name, ids in PHASES.items():
    st.subheader(f"{phase_name}  ·  Pick {limit_per_phase if limit_per_phase>0 else '∞'} of 3")
    pcs = st.session_state.cards[phase_name]
    picked = sum(c["flipped"] for c in pcs)
    if enforce_limit and limit_per_phase > 0 and not phase_reveal_flags[phase_name]:
        st.caption(f"Selected: {picked}/{limit_per_phase}")
    else:
        st.caption(f"Selected: {picked}/∞ (limit disabled)")

    cols = st.columns(3)
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

            btn_cols = st.columns(2)
            with btn_cols[0]:
                flip_disabled = card["flipped"] or not can_flip(
                    phase_name, enforce_limit, limit_per_phase, phase_reveal_flags[phase_name]
                )
                st.button("Flip", key=f"flip_{phase_name}_{i}", on_click=flip_card,
                          args=(phase_name, i), disabled=flip_disabled, use_container_width=True)
            with btn_cols[1]:
                st.button("Zoom", key=f"zoom_{phase_name}_{i}", on_click=toggle_zoom,
                          args=(phase_name, i), disabled=not card["flipped"], use_container_width=True)

            if card["flipped"]:
                st.success(f"{card['id']} → {card['owner']}")
                st.caption(STORY.get(card["id"], ""))

    st.markdown("---")

# --------------------- ZOOM OVERLAY (CSS-only; buttons to close) ---------------------
if st.session_state.zoom is not None:
    ph, idx = st.session_state.zoom
    card = st.session_state.cards[ph][idx]
    img_b64 = card["front"] if card["flipped"] else card["back"]

    # Dark overlay + centered card (CSS only; background ignores clicks)
    st.markdown(f"""
    <div class="overlay">
      <div class="cardwrap">
        <img src="data:image/png;base64,{img_b64}" />
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Bottom floating close button as a second safe control
    st.markdown('<div class="closebar">', unsafe_allow_html=True)
    st.button("✕ Close Zoom", on_click=close_zoom, type="primary")
    st.markdown('</div>', unsafe_allow_html=True)
