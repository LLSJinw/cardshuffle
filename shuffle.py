# streamlit_app.py
# Two-team TTX demo with 4 phases (3 cards each), "pick 2 of 3" per phase,
# flip animation, and zoom-on-click for flipped cards.

import base64, io, random, textwrap
from typing import Dict, List
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps

st.set_page_config(page_title="TTX Phased Deck", page_icon="🃏", layout="wide")

# --------------------- layout / style ---------------------
CARD_W, CARD_H, R = 360, 540, 24
FONT_SIZE_BIG = 72
FONT_SIZE_SMALL = 26
TEAMS = ["Team A", "Team B"]

PHASES = {
    "Phase 1 – Detection & Analysis": ["Q1", "Q2", "Q3"],
    "Phase 2 – Containment & Eradication": ["Q4", "Q5", "Q6"],
    "Phase 3 – Recovery": ["Q7", "Q8", "Q9"],
    "Phase 4 – Post-Incident": ["Q10", "Q11", "Q12"],
}

# one-line prompts (replace with your real injects later)
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

# ------------- helper: card image generation -------------
def get_font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default()

def draw_card_back() -> Image.Image:
    NAVY=(16,34,64); WHITE=(248,251,255)
    img = Image.new("RGB", (CARD_W, CARD_H), NAVY)
    d = ImageDraw.Draw(img)
    # diagonal lines
    for x in range(-CARD_H, CARD_W+CARD_H, 36):
        d.line([(x,0),(x+CARD_H,CARD_H)], fill=(255,255,255,32), width=2)
    # owl emoji
    d.text((CARD_W//2, CARD_H//2-40), "🦉", anchor="mm", fill=WHITE)
    # border bands
    img = ImageOps.expand(img, border=8, fill=(240,244,252))
    img = ImageOps.expand(img, border=3, fill=(220,226,236))
    return img

def draw_front(label: str, subtitle: str) -> Image.Image:
    NAVY=(16,34,64); STRIPE=(208,213,221); LIGHT=(236,240,248)
    img = Image.new("RGB", (CARD_W, CARD_H), NAVY)
    d = ImageDraw.Draw(img)
    # stripes
    d.rectangle([0, int(CARD_H*0.16), CARD_W, int(CARD_H*0.19)], fill=STRIPE)
    d.rectangle([0, int(CARD_H*0.72), CARD_W, int(CARD_H*0.75)], fill=STRIPE)
    # label
    f_big = get_font(FONT_SIZE_BIG)
    d.text((CARD_W//2, int(CARD_H*0.30)), label, anchor="mm", fill=LIGHT, font=f_big)
    # subtitle
    f_small = get_font(FONT_SIZE_SMALL)
    wrapped = textwrap.fill(subtitle, width=22)
    d.multiline_text((CARD_W//2, int(CARD_H*0.55)), wrapped, anchor="mm",
                     fill=LIGHT, font=f_small, align="center")
    # border
    img = ImageOps.expand(img, border=8, fill=(240,244,252))
    img = ImageOps.expand(img, border=3, fill=(220,226,236))
    return img

def pil_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

# --------------------- state init ---------------------
def init():
    if "cards" in st.session_state: return
    back_b64 = pil_to_b64(draw_card_back())
    cards = {}
    for ph, ids in PHASES.items():
        ids = ids[:]                 # copy
        random.shuffle(ids)          # randomize within phase (optional)
        phase_cards = []
        for qid in ids:
            front_b64 = pil_to_b64(draw_front(qid, STORY.get(qid, "")))
            phase_cards.append({
                "id": qid,
                "front": front_b64,
                "back": back_b64,
                "flipped": False,
                "owner": None,       # Team A / Team B
            })
        cards[ph] = phase_cards
    st.session_state.cards = cards
    st.session_state.turn = 0                 # 0 = Team A, 1 = Team B
    st.session_state.score = {t: 0 for t in TEAMS}
    st.session_state.zoom = None              # (phase, idx) or None

init()

# --------------------- actions ---------------------
def reset_all():
    st.session_state.pop("cards", None)
    init()

def shuffle_unflipped_in_phase(phase_name: str):
    pcs = st.session_state.cards[phase_name]
    flipped = [c for c in pcs if c["flipped"]]
    unflipped = [c for c in pcs if not c["flipped"]]
    random.shuffle(unflipped)
    st.session_state.cards[phase_name] = flipped + unflipped

def can_flip(phase_name: str) -> bool:
    pcs = st.session_state.cards[phase_name]
    return sum(c["flipped"] for c in pcs) < 2

def flip_card(phase_name: str, idx: int):
    if not can_flip(phase_name):
        return
    card = st.session_state.cards[phase_name][idx]
    if card["flipped"]:
        return
    team = TEAMS[st.session_state.turn]
    card["flipped"] = True
    card["owner"] = team
    st.session_state.score[team] += 1
    st.session_state.turn = 1 - st.session_state.turn

def toggle_zoom(phase_name: str, idx: int):
    if st.session_state.zoom == (phase_name, idx):
        st.session_state.zoom = None
    else:
        st.session_state.zoom = (phase_name, idx)

# --------------------- CSS for flip ---------------------
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
.zoom-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center; z-index: 9999;
}
.zoom-card { width: min(60vw, 600px); }
</style>
""", unsafe_allow_html=True)

# --------------------- header / controls ---------------------
left, mid, right = st.columns([1.3, 1.8, 1.3])
with left:
    st.subheader("Teams & Turn")
    st.markdown(f"**Current Turn:** {TEAMS[st.session_state.turn]}")
    st.write("**Score**")
    for t in TEAMS: st.write(f"- {t}: {st.session_state.score[t]}")
    st.button("🔄 Reset All", on_click=reset_all, use_container_width=True)

with right:
    st.subheader("Phase Tools")
    for ph in PHASES:
        st.button(f"🔀 Shuffle Unflipped – {ph}", key=f"shuf_{ph}", on_click=shuffle_unflipped_in_phase, args=(ph,), use_container_width=True)

# --------------------- phases grid ---------------------
st.markdown("---")
for phase_name, plist in PHASES.items():
    st.subheader(f"{phase_name}  ·  Pick 2 of 3")
    pcs = st.session_state.cards[phase_name]
    picked = sum(c["flipped"] for c in pcs)
    st.caption(f"Selected: {picked}/2")

    cols = st.columns(3)
    for i, col in enumerate(cols):
        with col:
            card = pcs[i]
            front = f"data:image/png;base64,{card['front']}"
            back  = f"data:image/png;base64,{card['back']}"
            flipped = "flipped" if card["flipped"] else ""
            html = f"""
            <div class="card-container">
              <div class="card {flipped}">
                <div class="card-inner">
                  <div class="card-face card-front">
                    <img class="img-fit" src="{back}"/>
                  </div>
                  <div class="card-face card-back">
                    <img class="img-fit" src="{front}"/>
                  </div>
                </div>
              </div>
            </div>"""
            st.markdown(html, unsafe_allow_html=True)

            row1 = st.columns(2)
            with row1[0]:
                disabled = (not can_flip(phase_name)) or card["flipped"]
                st.button("Flip", key=f"flip_{phase_name}_{i}", on_click=flip_card,
                          args=(phase_name,i), disabled=disabled, use_container_width=True)
            with row1[1]:
                st.button("Zoom", key=f"zoom_{phase_name}_{i}", on_click=toggle_zoom,
                          args=(phase_name,i), disabled=not card["flipped"], use_container_width=True)

            if card["flipped"]:
                st.success(f"{card['id']} → {card['owner']}")
                st.caption(STORY.get(card["id"], ""))

    st.markdown("---")

# --------------------- zoom overlay ---------------------
if st.session_state.zoom is not None:
    ph, idx = st.session_state.zoom
    card = st.session_state.cards[ph][idx]
    img_b64 = card["front"] if card["flipped"] else card["back"]
    st.markdown(f"""
    <div class="zoom-overlay" onclick="window.parent.postMessage('close-zoom', '*')">
      <div class="zoom-card">
        <img class="img-fit" src="data:image/png;base64,{img_b64}"/>
      </div>
    </div>
    """, unsafe_allow_html=True)
    # quick close button as fallback
    st.button("Close", on_click=lambda: toggle_zoom(ph, idx), type="primary")

# JS to close zoom when clicking overlay
st.markdown("""
<script>
window.addEventListener("message", (event) => {
  if (event.data === "close-zoom") {
    const btns = parent.document.querySelectorAll('button[kind="primary"]');
    if (btns && btns.length) { btns[0].click(); }
  }
});
</script>
""", unsafe_allow_html=True)

st.caption("Tip: replace STORY text with your real injects. Phase limit is enforced (2 of 3).")
