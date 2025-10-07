# streamlit_app.py
# Demo deck with flip animation, two-team turns, and basic story prompts
# Dependencies: streamlit, pillow (usually preinstalled in Streamlit cloud)
import base64
import io
import random
import textwrap
from typing import List, Dict, Tuple

import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps

st.set_page_config(page_title="TTX Card Deck Demo", page_icon="🃏", layout="wide")

# --------------------------- CONFIG ---------------------------
CARD_W, CARD_H, R = 360, 540, 24     # card size
DECK_SIZE = 12                       # number of cards
TEAMS = ["Team A", "Team B"]         # two teams
FONT_SIZE_BIG = 72
FONT_SIZE_SMALL = 26

# Simple mapping: Q1..Q12 -> short prompt (replace with your inject text later)
STORY: Dict[str, str] = {
    "Q1":  "Strategic: Activate CIRP immediately?",
    "Q2":  "Tactical: First containment action?",
    "Q3":  "Operational: HR calm comms?",
    "Q4":  "Strategic: Partner notification timing?",
    "Q5":  "Tactical: Isolate repos/servers?",
    "Q6":  "Operational: Contact center script?",
    "Q7":  "Strategic: Ransom stance (LE & backups)?",
    "Q8":  "Tactical: Verify backup integrity first?",
    "Q9":  "Operational: Staff breach notice guidance?",
    "Q10": "Strategic: Improve CIRP + BCP?",
    "Q11": "Tactical: Backup test + EDR + awareness?",
    "Q12": "Wildcard: Chaos card / random constraint",
}

# --------------------------- IMAGE GEN ---------------------------
def rounded_mask(w: int, h: int, r: int) -> Image.Image:
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, w-1, h-1], r, fill=255)
    return m

def draw_card_back() -> Image.Image:
    """Create a simple navy/grey/white card back."""
    NAVY=(16,34,64); MID=(36,58,104); WHITE=(248, 251, 255)
    img = Image.new("RGB", (CARD_W, CARD_H), NAVY)
    d = ImageDraw.Draw(img)
    # diagonal lines
    for x in range(-CARD_H, CARD_W+CARD_H, 36):
        d.line([(x,0),(x+CARD_H,CARD_H)], fill=(255,255,255,32), width=2)
    # center '🦉'
    try:
        # fallback emoji render via text
        d.text((CARD_W//2, CARD_H//2-40), "🦉", anchor="mm", fill=WHITE, align="center", font=None)
    except Exception:
        pass
    # band
    d.rectangle([0, int(CARD_H*0.72), CARD_W, int(CARD_H*0.78)], fill=(230,236,246))
    # rounded mask & white border
    img = ImageOps.expand(img, border=8, fill=(240,244,252))
    img = ImageOps.expand(img, border=3, fill=(220,226,236))
    return img

def get_font(size: int):
    # Streamlit environments often don't have TTF paths; none uses default bitmap font.
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default()

def draw_front(label: str, subtitle: str) -> Image.Image:
    """Generate a simple front image: large Q label + small subtitle wrap."""
    NAVY=(16,34,64); LIGHT=(236, 240, 248); STRIPE=(208, 213, 221)
    img = Image.new("RGB", (CARD_W, CARD_H), NAVY)
    d = ImageDraw.Draw(img)

    # stripes
    d.rectangle([0, int(CARD_H*0.16), CARD_W, int(CARD_H*0.19)], fill=STRIPE)
    d.rectangle([0, int(CARD_H*0.72), CARD_W, int(CARD_H*0.75)], fill=STRIPE)

    # label
    f_big = get_font(FONT_SIZE_BIG)
    d.text((CARD_W//2, int(CARD_H*0.30)), label, anchor="mm", fill=LIGHT, font=f_big)

    # subtitle wrapped
    f_small = get_font(FONT_SIZE_SMALL)
    wrapped = textwrap.fill(subtitle, width=22)
    d.multiline_text((CARD_W//2, int(CARD_H*0.55)), wrapped, anchor="mm", fill=LIGHT, font=f_small, align="center")

    # subtle border
    img = ImageOps.expand(img, border=8, fill=(240,244,252))
    img = ImageOps.expand(img, border=3, fill=(220,226,236))
    return img

def pil_to_base64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

# --------------------------- STATE ---------------------------
def init_state():
    if "deck" not in st.session_state:
        # Create deck Q1..Q12
        labels = [f"Q{i}" for i in range(1, DECK_SIZE+1)]
        # fronts/backs as base64
        back = draw_card_back()
        back_b64 = pil_to_base64(back)

        cards = []
        for lab in labels:
            front = draw_front(lab, STORY.get(lab, ""))
            front_b64 = pil_to_base64(front)
            cards.append({
                "id": lab,
                "front_b64": front_b64,
                "back_b64": back_b64,
                "flipped": False,
                "owner": None,         # "Team A" | "Team B" once flipped
            })

        random.shuffle(cards)
        st.session_state.deck = cards
        st.session_state.turn = 0           # 0 = Team A, 1 = Team B
        st.session_state.score = {t: 0 for t in TEAMS}
        st.session_state.log: List[str] = []

init_state()

# --------------------------- ACTIONS ---------------------------
def reset_deck():
    st.session_state.pop("deck", None)
    init_state()

def shuffle_unflipped():
    # shuffle positions of unflipped cards
    deck = st.session_state.deck
    unflipped = [c for c in deck if not c["flipped"]]
    random.shuffle(unflipped)
    st.session_state.deck = [c for c in deck if c["flipped"]] + unflipped

def flip_card(idx: int):
    card = st.session_state.deck[idx]
    if card["flipped"]:
        return
    team = TEAMS[st.session_state.turn]
    card["flipped"] = True
    card["owner"] = team
    st.session_state.score[team] += 1
    st.session_state.turn = 1 - st.session_state.turn
    st.session_state.log.append(f'{team} flipped {card["id"]}: {STORY.get(card["id"], "")}')

# --------------------------- UI ---------------------------
st.markdown(
    """
    <style>
    .card-container { perspective: 1000px; }
    .card {
      width: 100%;
      aspect-ratio: 2 / 3;
      position: relative;
    }
    .card-inner {
      position: absolute;
      width: 100%;
      height: 100%;
      transform-style: preserve-3d;
      transition: transform 0.6s ease;
    }
    .flipped .card-inner { transform: rotateY(180deg); }
    .card-face {
      position: absolute;
      width: 100%;
      height: 100%;
      -webkit-backface-visibility: hidden;
      backface-visibility: hidden;
      border-radius: 12px;
      overflow: hidden;
    }
    .card-front { transform: rotateY(0deg); }
    .card-back  { transform: rotateY(180deg); }
    .img-fit { width: 100%; height: 100%; object-fit: cover; }
    </style>
    """,
    unsafe_allow_html=True
)

left, mid, right = st.columns([1.2, 2.4, 1.2], gap="large")

with left:
    st.subheader("Teams & Turns")
    st.markdown(f"**Current Turn:** {TEAMS[st.session_state.turn]}")
    st.write("**Score**")
    for t in TEAMS:
        st.write(f"- {t}: {st.session_state.score[t]}")
    st.button("🔄 Reset Deck", on_click=reset_deck, use_container_width=True)
    st.button("🔀 Shuffle Unflipped", on_click=shuffle_unflipped, use_container_width=True)

    st.markdown("---")
    st.subheader("How to play")
    st.markdown(
        """
        1. Teams take turns.  
        2. Click **Flip** on any facedown card.  
        3. The flipped card is assigned to the team on turn.  
        4. Discuss the prompt shown on the card (your real inject).  
        5. Use the scoreboard to keep track of progress.  
        """
    )

with right:
    st.subheader("Event Log")
    if st.session_state.log:
        for ln in reversed(st.session_state.log[-20:]):
            st.write("•", ln)
    else:
        st.caption("No flips yet.")

with mid:
    st.subheader("Deck")
    deck = st.session_state.deck

    # render grid (4 x 3)
    rows = [deck[i:i+4] for i in range(0, len(deck), 4)]
    for r, row in enumerate(rows):
        cols = st.columns(4)
        for c, card in enumerate(row):
            idx = r*4 + c
            with cols[c]:
                front = f"data:image/png;base64,{card['front_b64']}"
                back  = f"data:image/png;base64,{card['back_b64']}"

                flipped_class = "flipped" if card["flipped"] else ""
                html = f"""
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
                """
                st.markdown(html, unsafe_allow_html=True)

                if not card["flipped"]:
                    st.button(f"Flip", key=f"flip_{idx}", on_click=flip_card, args=(idx,), use_container_width=True)
                else:
                    st.success(f"{card['id']} → {card['owner']}")
                    # show the text prompt under the flipped card for quick reference
                    st.caption(STORY.get(card["id"], ""))

st.caption("Demo: generated graphics only. Replace STORY text with your real injects/questions.")
