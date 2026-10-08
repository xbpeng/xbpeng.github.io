"""Make compressed copies of thumbnails and teasers for the website.

For each *_thumb.* and *teaser*.* image in projects/<Name>/ and prospective_students/, writes a
"<name>_small.jpg" next to it. The site uses the small copy when it exists. Originals, GIFs and videos are left untouched.

Usage (requires Pillow):
    python _scripts/make_small_images.py          # only new or changed images
    python _scripts/make_small_images.py --force  # regenerate all
"""
import os
import sys
from glob import glob

from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# (filename pattern, max width in pixels, JPEG quality)
IMAGE_TYPES = [
    ("*_thumb.*", 480, 82),
    ("*teaser*.*", 1760, 85),
]
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
IMAGE_DIRS = ["projects/*", "prospective_students"]


def small_path(path):
    return os.path.splitext(path)[0] + "_small.jpg"


def is_up_to_date(src, dst):
    return os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src)


def make_small(src, dst, max_width, quality):
    image = Image.open(src).convert("RGBA")
    flat = Image.new("RGB", image.size, (255, 255, 255))
    flat.paste(image, mask=image.getchannel("A"))
    if flat.width > max_width:
        height = round(flat.height * max_width / flat.width)
        flat = flat.resize((max_width, height), Image.LANCZOS)
    flat.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)


def main():
    force = "--force" in sys.argv
    total_before = total_after = 0

    for pattern, max_width, quality in IMAGE_TYPES:
        sources = [src for folder in IMAGE_DIRS for src in glob(os.path.join(ROOT, folder, pattern))]
        for src in sorted(sources):
            if src.endswith("_small.jpg") or not src.lower().endswith(IMAGE_EXTENSIONS):
                continue
            dst = small_path(src)
            if not force and is_up_to_date(src, dst):
                continue

            make_small(src, dst, max_width, quality)
            before, after = os.path.getsize(src), os.path.getsize(dst)
            total_before += before
            total_after += after
            print(f"{os.path.relpath(dst, ROOT)}: {before // 1024} KB -> {after // 1024} KB")

    if total_before:
        print(f"Total: {total_before / 2**20:.1f} MB -> {total_after / 2**20:.1f} MB")
    else:
        print("All images are up to date.")


if __name__ == "__main__":
    main()
