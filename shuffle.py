# streamlit_app.py
import io
import math
from typing import Tuple

import streamlit as st
from PIL import Image, ImageDraw, ImageFilter, ImageOps

st.set_page_config(page_title="Card Back Generator", page_icon="🦉", layout="centered")

# --- Palette (navy / grey / white) ---
NAVY  = (16, 34, 64)
MID   = (35, 56, 102)
DARKG = (72, 78, 92)
GREY  = (208, 213, 221)
WHITE = (250, 252, 255)
SILVER= (224, 228, 236)

# ---------------- helpers ----------------
def rounded_mask(w: int, h: int, r: int) -> Image.Image:
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, w-1, h-1], r, fill=255)
    return m

def radial_gradient(size: Tuple[int,int], inner: Tuple[int,int,int], outer: Tuple[int,int,int]) -> Image.Image:
    """PIL-only radial gradient (no numpy). Optimized with bands, good enough for UI."""
    w, h = size
    img = Image.new("RGB", size, outer)
    draw = ImageDraw.Draw(img)
    cx, cy = w//2, h//2
    # draw concentric circles from center outward
    max_r = int(math.hypot(cx, cy))
    steps = 220  # higher = smoother
    for i in range(steps, -1, -1):
        t = i/steps
        col = (
            int(inner[0]*t + outer[0]*(1-t)),
            int(inner[1]*t + outer[1]*(1-t)),
            int(inner[2]*t + outer[2]*(1-t)),
        )
        r = int(max_r * t)
        bbox = [cx-r, cy-r, cx+r, cy+r]
        draw.ellipse(bbox, fill=col)
    return img

def subtle_diagonal(size: Tuple[int,int], spacing=48, alpha=22) -> Image.Image:
    w, h = size
    img = Image.new("RGBA", size, (0,0,0,0))
    d = ImageDraw.Draw(img)
    for x in range(-h, w+h, spacing):
        d.line([(x,0),(x+h,h)], fill=(255,255,255,alpha), width=2)
    return img

def add_border(card: Image.Image) -> Image.Image:
    card = ImageOps.expand(card, border=26, fill=WHITE)
    card = ImageOps.expand(card, border=6, fill=SILVER)
    return card

def center_logo(canvas: Image.Image, logo: Image.Image, scale=0.55, y_offset=0) -> Image.Image:
    w = int(canvas.width * scale)
    r = w / logo.width
    nh = int(logo.height * r)
    logo_r = logo.resize((w, nh), Image.LANCZOS)

    # soft white outline for contrast
    alpha = logo_r.split()[-1] if logo_r.mode == "RGBA" else Image.new("L", logo_r.size, 255)
    outline = alpha.filter(ImageFilter.MaxFilter(13))
    glow = Image.new("RGBA", logo_r.size, (255,255,255,170))
    glow.putalpha(outline)

    layer = Image.new("RGBA", canvas.size, (0,0,0,0))
    x = (canvas.width - w)//2
    y = int((canvas.height - nh)//2 + y_offset)
    layer.alpha_composite(glow, (x,y))
    layer.alpha_composite(logo_r.convert("RGBA"), (x,y))
    return Image.alpha_composite(canvas.convert("RGBA"), layer)

def to_download_bytes(img: Image.Image, filename: str):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    st.download_button("⬇️ Download " + filename, data=buf.getvalue(), file_name=filename, mime="image/png")

# ---------------- UI ----------------
st.title("🦉 Card Back Generator")
st.caption("Palette: navy · grey · white")

colA, colB = st.columns([1,1])
with colA:
    uploaded = st.file_uploader("Upload your owl/logo (PNG with transparency preferred)", type=["png","jpg","jpeg"])
with colB:
    W = st.slider("Card width (px)", 480, 1200, 900, 60)
    aspect = st.selectbox("Aspect ratio", ["2:3 (portrait)", "3:5 (tall portrait)"], index=0)
    if aspect == "2:3 (portrait)":
        H = int(W * 3/2)
    else:
        H = int(W * 5/3)
R = 48 if W <= 700 else 64

if not uploaded:
    st.info("Upload your owl logo to generate the card backs.")
    st.stop()

# load owl
owl = Image.open(uploaded).convert("RGBA")

# common mask
mask = rounded_mask(W, H, R)

# -------- Variant 1: MONO --------
bg1 = radial_gradient((W,H), inner=MID, outer=NAVY).convert("RGBA")
bg1.alpha_composite(subtle_diagonal((W,H), spacing=48, alpha=18))
card1 = Image.new("RGBA",(W,H),(0,0,0,0))
card1.paste(bg1, (0,0), mask)
card1 = center_logo(card1, owl, scale=0.5, y_offset=-int(H*0.02))
d1 = ImageDraw.Draw(card1)
d1.rounded_rectangle([int(W*0.09), H- int(H*0.13), W- int(W*0.09), H- int(H*0.08)],
                     radius=20, fill=(255,255,255,42), outline=(255,255,255,90), width=2)
mono = add_border(card1)

# -------- Variant 2: DUO --------
bg2 = Image.new("RGBA",(W,H), NAVY)
d2 = ImageDraw.Draw(bg2)
d2.polygon([(0,int(H*0.55)), (W,int(H*0.35)), (W,H), (0,H)], fill=DARKG)
bg2.alpha_composite(subtle_diagonal((W,H), spacing=56, alpha=22))
card2 = Image.new("RGBA",(W,H),(0,0,0,0))
card2.paste(bg2, (0,0), mask)
card2 = center_logo(card2, owl, scale=0.56, y_offset=-int(H*0.02))
shine = Image.new("RGBA",(W,H),(255,255,255,0))
ds = ImageDraw.Draw(shine)
ds.ellipse([-int(W*0.22), -int(H*0.36), int(W*1.22), int(H*0.43)], fill=(255,255,255,18))
card2 = Image.alpha_composite(card2, shine)
duo = add_border(card2)

# -------- Variant 3: TRI-TONE --------
bg3 = radial_gradient((W,H), inner=(28,51,96), outer=NAVY).convert("RGBA")
card3 = Image.new("RGBA",(W,H),(0,0,0,0))
card3.paste(bg3, (0,0), mask)
d3 = ImageDraw.Draw(card3)
stripe_h = max(36, int(H*0.035))
d3.rectangle([0, int(H*0.68), W, int(H*0.68)+stripe_h], fill=GREY+(255,))
d3.rectangle([0, int(H*0.68)+stripe_h+16, W, int(H*0.68)+stripe_h*2+16], fill=WHITE+(255,))
card3 = center_logo(card3, owl, scale=0.54, y_offset=-int(H*0.04))
tri = add_border(card3)

# ---------------- show & download ----------------
st.subheader("Previews")
c1, c2, c3 = st.columns(3)
with c1:
    st.image(mono, caption="Mono", use_column_width=True)
    to_download_bytes(mono, "card_back_mono.png")
with c2:
    st.image(duo, caption="Duo", use_column_width=True)
    to_download_bytes(duo, "card_back_duo.png")
with c3:
    st.image(tri, caption="Tri-Tone", use_column_width=True)
    to_download_bytes(tri, "card_back_tritone.png")

st.success("Done. Use one of these as the **back** image for all cards in your Streamlit deck.")

