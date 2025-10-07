# card_backs.py
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import numpy as np, math, os

# --- paths ---
OWL = "images/owl.png"
OUT = "out_backs"
os.makedirs(OUT, exist_ok=True)

# --- card size & style ---
W, H, R = 900, 1400, 64  # px
NAVY=(16,34,64); MID=(35,56,102)
DARKG=(72,78,92); GREY=(208,213,221)
WHITE=(250,252,255); SILVER=(224,228,236)

def radial_grad(size, inner, outer):
    w,h=size; cx,cy=w//2,h//2; md=max(w,h)
    arr=np.zeros((h,w,3),dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            t=min(1.0, math.hypot(x-cx,y-cy)/md)
            arr[y,x]=(int(inner[0]*(1-t)+outer[0]*t),
                      int(inner[1]*(1-t)+outer[1]*t),
                      int(inner[2]*(1-t)+outer[2]*t))
    return Image.fromarray(arr,'RGB')

def rounded_mask(w,h,r):
    m=Image.new("L",(w,h),0); d=ImageDraw.Draw(m)
    d.rounded_rectangle([0,0,w-1,h-1], r, fill=255); return m

def subtle_diagonal(size, spacing=48, alpha=20):
    img=Image.new("RGBA", size, (0,0,0,0)); d=ImageDraw.Draw(img)
    for x in range(-size[1], size[0]+size[1], spacing):
        d.line([(x,0),(x+size[1],size[1])], fill=(255,255,255,alpha), width=2)
    return img

def add_border(card):
    return ImageOps.expand(ImageOps.expand(card, border=26, fill=WHITE), border=6, fill=SILVER)

def center_logo(canvas, logo, scale=0.55, y_offset=0):
    w=int(canvas.width*scale); r=w/logo.width; nh=int(logo.height*r)
    logo_r=logo.resize((w,nh), Image.LANCZOS)
    x=(canvas.width-w)//2; y=int((canvas.height-nh)//2 + y_offset)
    layer=Image.new("RGBA", canvas.size, (0,0,0,0))
    # soft white outline for contrast
    alpha=logo_r.split()[-1]
    outline=alpha.filter(ImageFilter.MaxFilter(13))
    glow=Image.new("RGBA", logo_r.size, (255,255,255,170)); glow.putalpha(outline)
    layer.alpha_composite(glow,(x,y)); layer.alpha_composite(logo_r,(x,y))
    return Image.alpha_composite(canvas, layer)

# load owl
owl = Image.open(OWL).convert("RGBA")
mask = rounded_mask(W,H,R)

# --- 1) MONO ---
bg = radial_grad((W,H), inner=MID, outer=NAVY).convert("RGBA")
bg = Image.alpha_composite(bg, subtle_diagonal((W,H), spacing=48, alpha=18))
mono = Image.new("RGBA",(W,H),(0,0,0,0)); mono.paste(bg,(0,0),mask)
mono = center_logo(mono, owl, scale=0.5, y_offset=-30)
d = ImageDraw.Draw(mono)
d.rounded_rectangle([80,H-180,W-80,H-130], radius=20, fill=(255,255,255,42),
                    outline=(255,255,255,90), width=2)
mono = add_border(mono); mono.save(os.path.join(OUT, "card_back_mono.png"))

# --- 2) DUO ---
bg = Image.new("RGBA",(W,H), NAVY); d2=ImageDraw.Draw(bg)
d2.polygon([(0,int(H*0.55)),(W,int(H*0.35)),(W,H),(0,H)], fill=DARKG)
bg = Image.alpha_composite(bg, subtle_diagonal((W,H), spacing=56, alpha=22))
duo = Image.new("RGBA",(W,H),(0,0,0,0)); duo.paste(bg,(0,0),mask)
duo = center_logo(duo, owl, scale=0.56, y_offset=-20)
shine = Image.new("RGBA",(W,H),(255,255,255,0)); ds=ImageDraw.Draw(shine)
ds.ellipse([-200,-500,W+200,600], fill=(255,255,255,18))
duo = Image.alpha_composite(duo, shine)
duo = add_border(duo); duo.save(os.path.join(OUT, "card_back_duo.png"))

# --- 3) TRI-TONE ---
bg = radial_grad((W,H), inner=(28,51,96), outer=NAVY).convert("RGBA")
tri = Image.new("RGBA",(W,H),(0,0,0,0)); tri.paste(bg,(0,0),mask)
d3=ImageDraw.Draw(tri); sh=46
d3.rectangle([0, int(H*0.68), W, int(H*0.68)+sh], fill=GREY+(255,))
d3.rectangle([0, int(H*0.68)+sh+16, W, int(H*0.68)+sh*2+16], fill=WHITE+(255,))
tri = center_logo(tri, owl, scale=0.54, y_offset=-60)
tri = add_border(tri); tri.save(os.path.join(OUT, "card_back_tritone.png"))

print("Done → check the 'out_backs' folder.")
