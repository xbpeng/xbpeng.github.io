"""Create small, compressed copies of the project thumbnails for the home page.

For every projects/<Name>/*_thumb.<ext> image, writes projects/<Name>/*_thumb_small.jpg
(at most MAX_WIDTH pixels wide, JPEG). Originals are left untouched. The home page
automatically uses the _small.jpg version when it exists, and falls back to the original.

Usage (from the repository root, requires Pillow):
    python _scripts/make_thumbnails.py          # only new or changed thumbnails
    python _scripts/make_thumbnails.py --force  # regenerate all
"""
import glob
import os
import sys

from PIL import Image

MAX_WIDTH = 480   # displayed at 200px on desktop and up to 320px on phones
QUALITY = 82
BACKGROUND = (255, 255, 255)  # transparent areas are filled with the page background


def small_path(path):
    return os.path.splitext(path)[0] + "_small.jpg"


def make_small(src, dst):
    im = Image.open(src)
    im.seek(0)  # first frame of animated images
    im = im.convert("RGBA")
    flat = Image.new("RGB", im.size, BACKGROUND)
    flat.paste(im, mask=im.getchannel("A"))
    if flat.width > MAX_WIDTH:
        height = round(flat.height * MAX_WIDTH / flat.width)
        flat = flat.resize((MAX_WIDTH, height), Image.LANCZOS)
    flat.save(dst, "JPEG", quality=QUALITY, optimize=True, progressive=True)


def main():
    force = "--force" in sys.argv
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    sources = [p for p in glob.glob(os.path.join(root, "projects", "*", "*_thumb.*"))
               if not p.endswith("_small.jpg")]
    before = after = 0
    for src in sorted(sources):
        dst = small_path(src)
        if not force and os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            continue
        make_small(src, dst)
        before += os.path.getsize(src)
        after += os.path.getsize(dst)
        print(f"{os.path.relpath(dst, root)}: {os.path.getsize(src) // 1024} KB -> {os.path.getsize(dst) // 1024} KB")
    if before:
        print(f"Total: {before / 2**20:.1f} MB -> {after / 2**20:.1f} MB")
    else:
        print("All thumbnails are up to date.")


if __name__ == "__main__":
    main()
