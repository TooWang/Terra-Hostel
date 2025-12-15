
from PIL import Image, ImageDraw, ImageFilter
from moviepy import VideoFileClip

from moviepy import *

clip = VideoFileClip("./test.mp4")
clip = clip.fx(vfx.fadein, 1)
clip = clip.fx(vfx.fadeout, 1)

formation = Image.open("BG.png")
formation = formation.convert("RGBA")
rm_image = Image.open("Cover.png")
rm_image = rm_image.convert("RGBA")
Tachie = Image.open("Haruka.png")
Tachie = Tachie.convert("RGBA")

TachieMask = Image.open("Mask.png")
TachieMask = TachieMask.convert("RGBA")

TachieWidth, TachieHeight = Tachie.size
maskImg = Image.new("L", (TachieWidth, TachieHeight))
maskDraw = ImageDraw.Draw(maskImg)
maskDraw.rectangle([(TachieWidth/1.4), 0, TachieWidth, TachieHeight], fill=255)
maskImg = maskImg.filter(ImageFilter.GaussianBlur(80))

Empty = Image.new("RGBA", (TachieWidth, TachieHeight))
maskDraw = ImageDraw.Draw(Empty)

formation.alpha_composite(rm_image)
formation.alpha_composite(Image.composite(Empty, Tachie, maskImg),((-round(TachieWidth/2)+520),90))
formation.show()