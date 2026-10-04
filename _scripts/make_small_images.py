"""Create small, compressed copies of the project thumbnails and teaser images.

For every projects/<Name>/*_thumb.<ext> and projects/<Name>/*teaser*.<ext> image, writes a
compressed JPEG copy next to it with "_small.jpg" appended to the name, e.g.
GPC_thumb.png -> GPC_thumb_small.jpg. Originals are left untouched, and GIFs and videos are
skipped. The site automatically uses the _small.jpg version when it exists, and falls back
to the original otherwise.

Usage (from the repository root, requires Pillow):
    python _scripts/make_small_images.py          # only new or changed images
    python _scripts/make_small_images.py --force  # regenerate all
"""
import glob
import os
import sys

from PIL import Image

# (filename pattern, max width in pixels, JPEG quality)
#   thumbnails are displayed at 200px on desktop and up to 320px on phones
#   teasers are displayed at up to ~830px; 1760px keeps them sharp on high-resolution screens
IMAGE_TYPES = [
    ("*_thumb.*", 480, 82),
    ("*teaser*.*", 1760, 85),
]
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")  # GIFs and videos are skipped
BACKGROUND = (255, 255, 255)  # transparent areas are filled with the page background


def small_path(path):
    return os.path.splitext(path)[0] + "_small.jpg"


def make_small(src, dst, max_width, quality):
    im = Image.open(src).convert("RGBA")
    flat = Image.new("RGB", im.size, BACKGROUND)
    flat.paste(im, mask=im.getchannel("A"))
    if flat.width > max_width:
        height = round(flat.height * max_width / flat.width)
        flat = flat.resize((max_width, height), Image.LANCZOS)
    flat.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)


def main():
    force = "--force" in sys.argv
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    before = after = 0
    for pattern, max_width, quality in IMAGE_TYPES:
        for src in sorted(glob.glob(os.path.join(root, "projects", "*", pattern))):
            if src.endswith("_small.jpg") or not src.lower().endswith(IMAGE_EXTENSIONS):
                continue
            dst = small_path(src)
            if not force and os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
                continue
            make_small(src, dst, max_width, quality)
            before += os.path.getsize(src)
            after += os.path.getsize(dst)
            print(f"{os.path.relpath(dst, root)}: {os.path.getsize(src) // 1024} KB -> {os.path.getsize(dst) // 1024} KB")
    if before:
        print(f"Total: {before / 2**20:.1f} MB -> {after / 2**20:.1f} MB")
    else:
        print("All images are up to date.")


if __name__ == "__main__":
    main()
