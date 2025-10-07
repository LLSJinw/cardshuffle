# streamlit_app.py
# Minimal demo: flip a card, then zoom that exact card. Close Zoom is a normal button.

import base64, io, textwrap
import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageFont

st.set_page_config(page_title="Zoom Test", page_icon="🔎", layout="wide")

CARD_W, CARD_H = 360, 540

# ----- helpers -----
def get_font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default()

def make_back()->Image.Image:
    NAVY=(16,34,64); WHITE=(248,251,255)
    img = Image.new("RGB", (CARD_W, CARD_H), NAVY)
    d = ImageDraw.Draw(img)
    for x in range(-CARD_H, CARD_W+CARD_H, 36):
        d.line([(x,0),(x+CARD_H,CARD_H)], fill=(255,255,255,32), width=2)
    d.text((CARD_W//2, CARD_H//2-40), "🦉", anchor="mm", fill=WHITE)
    img = ImageOps.expand(img, border=8, fill=(240,244,252))
    img = ImageOps.expand(img, border=3, fill=(220,226,236))
    return img

def make_front(label:str, subtitle:str)->Image.Image:
    NAVY=(16,34,64); STRIPE=(208,213,221); LIGHT=(236,240,248)
    img = Image.new("RGB", (CARD_W, CARD_H), NAVY)
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(CARD_H*0.16), CARD_W, int(CARD_H*0.19)], fill=STRIPE)
    d.rectangle([0, int(CARD_H*0.72), CARD_W, int(CARD_H*0.75)], fill=STRIPE)
    d.text((CARD_W//2, int(CARD_H*0.30)), label, anchor="mm", fill=LIGHT, font=get_font(72))
    txt = textwrap.fill(subtitle, width=22)
    d.multiline_text((CARD_W//2, int(CARD_H*0.55)), txt, anchor="mm", fill=LIGHT, font=get_font(24), align="center")
    img = ImageOps.expand(img, border=8, fill=(240,244,252))
    img = ImageOps.expand(img, border=3, fill=(220,226,236))
    return img

def pil_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

# ----- state -----
if "cards" not in st.session_state:
    back_b64 = pil_to_b64(make_back())
    demo = [("Q1","Activate CIRP?"), ("Q2","First containment?"), ("Q3","HR calm comms?")]
    st.session_state.cards = []
    for q, sub in demo:
        st.session_state.cards.append({
            "id": q,
            "front": pil_to_b64(make_front(q, sub)),
            "back": back_b64,
            "flipped": False,
        })
    st.session_state.zoom_index = None  # None or int

def flip(i:int):
    st.session_state.cards[i]["flipped"] = True

def open_zoom(i:int):
    st.session_state.zoom_index = i

def close_zoom():
    st.session_state.zoom_index = None

# ----- layout -----
st.title("Card Zoom – Minimal Proof")

cols = st.columns(3)
for i, col in enumerate(cols):
    with col:
        card = st.session_state.cards[i]
        img_b64 = card["front"] if card["flipped"] else card["back"]
        st.image(f"data:image/png;base64,{img_b64}", use_container_width=True)
        bcols = st.columns(2)
        with bcols[0]:
            st.button("Flip", key=f"flip_{i}", on_click=flip, args=(i,), disabled=card["flipped"], use_container_width=True)
        with bcols[1]:
            st.button("Zoom", key=f"zoom_{i}", on_click=open_zoom, args=(i,), disabled=not card["flipped"], use_container_width=True)

# ----- zoom overlay -----
# No JS. Just a normal Streamlit container at the bottom that shows a big image + Close button.
if st.session_state.zoom_index is not None:
    st.markdown("---")
    st.subheader("🔎 Zoomed Card")
    idx = st.session_state.zoom_index
    card = st.session_state.cards[idx]
    big = Image.open(io.BytesIO(base64.b64decode(card["front"])))
    # upscale for presentation
    scale = st.slider("Zoom", 1.0, 2.0, 1.6, 0.1, help="Adjust on the fly")
    big_resized = big.resize((int(CARD_W*scale), int(CARD_H*scale)))
    st.image(big_resized, use_column_width=False)
    st.button("✕ Close Zoom", on_click=close_zoom, type="primary")
