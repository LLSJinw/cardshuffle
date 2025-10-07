# streamlit_app.py
# Phased card board with production-safe "overlay-feel" zoom (no JS).

import base64, io, random, textwrap
from typing import Dict, List, Tuple
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps

st.set_page_config(page_title="TTX Deck", page_icon="🃏", layout="wide")

# ---------- visuals ----------
CARD_W, CARD_H = 360, 540
PHASES = {
    "Phase 1 – Detection & Analysis": ["Q1", "Q2", "Q3"],
    "Phase 2 – Containment & Eradication": ["Q4", "Q5", "Q6"],
    "Phase 3 – Recovery": ["Q7", "Q8", "Q9"],
    "Phase 4 – Post-Incident": ["Q10", "Q11", "Q12"],
}
STORY = {
    "Q1":"Activate CIRP?",
    "Q2":"First containment?",
    "Q3":"HR calm comms?",
    "Q4":"Partner notification?",
    "Q5":"Isolate repos/servers?",
    "Q6":"Contact-center msg?",
    "Q7":"Ransom stance (LE+backup)?",
    "Q8":"Verify backups first?",
    "Q9":"Staff breach notice?",
    "Q10":"Improve CIRP/BCP?",
    "Q11":"Backup test + EDR + Awareness?",
    "Q12":"Chaos / wildcard",
}

def _font(sz:int):
    try: return ImageFont.truetype("DejaVuSans-Bold.ttf", sz)
    except: return ImageFont.load_default()

def make_back()->Image.Image:
    NAVY=(16,34,64); WHITE=(246,249,255)
    img = Image.new("RGB", (CARD_W, CARD_H), NAVY)
    d = ImageDraw.Draw(img)
    for x in range(-CARD_H, CARD_W+CARD_H, 36):
        d.line([(x,0),(x+CARD_H,CARD_H)], fill=(255,255,255,28), width=2)
    d.text((CARD_W//2, CARD_H//2-40), "🦉", anchor="mm", fill=WHITE, font=_font(64))
    img = ImageOps.expand(img, border=8, fill=(240,244,252))
    img = ImageOps.expand(img, border=3, fill=(220,226,236))
    return img

def make_front(label:str, subtitle:str)->Image.Image:
    NAVY=(16,34,64); STRIPE=(208,213,221); LIGHT=(236,240,248)
    img = Image.new("RGB", (CARD_W, CARD_H), NAVY)
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(CARD_H*0.16), CARD_W, int(CARD_H*0.19)], fill=STRIPE)
    d.rectangle([0, int(CARD_H*0.72), CARD_W, int(CARD_H*0.75)], fill=STRIPE)
    d.text((CARD_W//2, int(CARD_H*0.30)), label, anchor="mm", fill=LIGHT, font=_font(72))
    wrapped = textwrap.fill(subtitle or "", width=22)
    d.multiline_text((CARD_W//2, int(CARD_H*0.55)), wrapped, anchor="mm",
                     fill=LIGHT, font=_font(24), align="center")
    img = ImageOps.expand(img, border=8, fill=(240,244,252))
    img = ImageOps.expand(img, border=3, fill=(220,226,236))
    return img

def pil_to_b64(img)->str:
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

# ---------- state ----------
def init():
    if "cards" in st.session_state: return
    back_b64 = pil_to_b64(make_back())
    cards: Dict[str, List[Dict]] = {}
    for phase, ids in PHASES.items():
        ids = ids[:]; random.shuffle(ids)
        arr=[]
        for q in ids:
            arr.append({
                "id": q,
                "front": pil_to_b64(make_front(q, STORY.get(q,""))),
                "back": back_b64,
                "flipped": False,
            })
        cards[phase]=arr
    st.session_state.cards = cards
    st.session_state.zoom = None  # (phase, idx) or None

def reset_all():
    st.session_state.pop("cards", None)
    st.session_state.pop("zoom", None)
    init()

init()

# ---------- sidebar admin ----------
with st.sidebar:
    st.header("Admin")
    enforce_limit = st.checkbox("Enforce limit per phase", value=True)
    limit = st.number_input("Limit (0 = unlimited)", 0, 3, 2, 1)
    st.button("🔄 Reset All", on_click=reset_all, use_container_width=True)
    st.markdown("---")
    st.caption("Tip: disable the limit or set 0 to reveal all three for discussion.")

# ---------- card helpers ----------
def can_flip(phase:str)->bool:
    if not enforce_limit or limit==0: return True
    picked=sum(c["flipped"] for c in st.session_state.cards[phase])
    return picked<limit

def flip_card(phase:str, idx:int):
    if st.session_state.cards[phase][idx]["flipped"]: return
    if not can_flip(phase): return
    st.session_state.cards[phase][idx]["flipped"]=True

def open_zoom(phase:str, idx:int):
    if not st.session_state.cards[phase][idx]["flipped"]: return
    st.session_state.zoom=(phase,idx)

def close_zoom():
    st.session_state.zoom=None

# ---------- CSS: overlay-feel ----------
st.markdown("""
<style>
.overlay {
  position: fixed; inset:0; background: rgba(0,0,0,0.72);
  display: flex; align-items: center; justify-content: center;
  z-index: 9999;
}
.overlay .cardwrap {
  max-width: min(72vw, 760px);
  border-radius: 16px; overflow: hidden;
  box-shadow: 0 10px 30px rgba(0,0,0,0.45);
}
.overlay img { width: 100%; height: auto; display:block; }
.closebar {
  position: fixed; bottom: 18px; left: 18px; z-index: 10000;
}
.cardgrid img { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

# ---------- main layout ----------
st.title("Phased TTX Deck (Production-safe Zoom)")
st.caption("Flip 2 of 3 per phase (unless admin disables). Click Zoom to present a card full screen.")

for phase, ids in PHASES.items():
    st.subheader(phase)
    picked=sum(c["flipped"] for c in st.session_state.cards[phase])
    cap = f"{picked}/{limit if (enforce_limit and limit>0) else '∞'} selected"
    st.caption(cap)

    cols = st.columns(3)
    for i, col in enumerate(cols):
        with col:
            card = st.session_state.cards[phase][i]
            b64 = card["front"] if card["flipped"] else card["back"]
            st.image(f"data:image/png;base64,{b64}", use_container_width=True)
            b1, b2 = st.columns(2)
            with b1:
                st.button("Flip", key=f"flip_{phase}_{i}", on_click=flip_card,
                          args=(phase,i),
                          disabled=card["flipped"] or (not can_flip(phase)),
                          use_container_width=True)
            with b2:
                st.button("Zoom", key=f"zoom_{phase}_{i}", on_click=open_zoom,
                          args=(phase,i),
                          disabled=not card["flipped"],
                          use_container_width=True)
    st.markdown("---")

# ---------- overlay-feel zoom (no JS) ----------
if st.session_state.zoom:
    ph, idx = st.session_state.zoom
    c = st.session_state.cards[ph][idx]
    img_b64 = c["front"]

    # draw a fixed overlay with the image centered (pure CSS)
    st.markdown(f"""
    <div class="overlay">
      <div class="cardwrap">
        <img src="data:image/png;base64,{img_b64}" />
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Close button that always works in Streamlit Cloud
    with st.container():
        st.markdown('<div class="closebar">', unsafe_allow_html=True)
        st.button("✕ Close Zoom", on_click=close_zoom, type="primary")
        st.markdown('</div>', unsafe_allow_html=True)
