"""Check the website's content for mistakes before pushing.

Checks every project page in projects/ (YAML, referenced files, compressed images, affiliation
numbers, links, videos, BibTeX), the publication list in _data/publications.yml, and the file
paths used on the teaching, art and team pages.

Usage (requires PyYAML and Pillow):
    python _scripts/check_site.py          # offline checks
    python _scripts/check_site.py --links  # also check that external links load (slower)

Exits with status 1 if there are errors. Warnings are printed but don't fail the check.
"""
import concurrent.futures
import glob
import hashlib
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict

import yaml
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

REQUIRED_FIELDS = ["layout", "title", "venue", "authors", "thumbnail", "teaser", "paper", "abstract", "bibtex"]
OPTIONAL_FIELDS = ["award", "affiliations", "author_note", "teaser_width", "paper_label", "links", "videos"]
LINK_GROUPS = {"Code", "Webpage", "Preprint", "Media"}  # groups with an icon in _includes/icon.html
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

# Files that intentionally don't follow the naming conventions (renaming would break outside links).
KNOWN_NAME_EXCEPTIONS = {"LearnToMove_2021.pdf", "2019-MIG-symmetry.mp4", "SymLoco_2018.pdf", "GenLoco_2023.pdf"}
FOLDERS_WITHOUT_PAGE = {"MimicKit"}
UNLISTED_PROJECTS = {"PhD_Thesis", "MSc_Thesis"}

errors = defaultdict(list)
warnings = defaultdict(list)


def read_front_matter(path):
    text = open(path, encoding="utf-8").read()
    if not text.startswith("---\n"):
        raise ValueError("file does not start with ---")
    _, front_matter, body = text.split("---\n", 2)
    return yaml.safe_load(front_matter), body.strip()


def as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def author_name(author):
    return author.split(" (")[0].replace("*", "").replace("†", "").strip()


def check_image(name, folder, file):
    path = os.path.join(ROOT, "projects", folder, file)
    small = os.path.splitext(path)[0] + "_small.jpg"
    if not os.path.exists(small):
        warnings[name].append(f"no compressed copy of {file} (run _scripts/make_small_images.py)")
    elif os.path.getmtime(small) < os.path.getmtime(path):
        warnings[name].append(f"compressed copy of {file} is out of date (run _scripts/make_small_images.py)")
    try:
        Image.open(path).verify()
    except Exception as e:
        errors[name].append(f"cannot open image {file}: {e}")
    return os.path.basename(small)


def check_authors(name, page):
    authors = page.get("authors") or []
    affiliations = page.get("affiliations") or []
    numbers = set()
    for author in authors:
        match = re.fullmatch(r"[^()]+?(?: \(([\d, ]+)\))?", str(author))
        if not match:
            errors[name].append(f"author not in 'Name (1, 2)' format: {author!r}")
        elif match.group(1):
            numbers |= {int(n) for n in match.group(1).split(",")}

    if len(affiliations) > 1:
        if numbers != set(range(1, len(affiliations) + 1)):
            errors[name].append(f"affiliation numbers used {sorted(numbers)} don't match {len(affiliations)} affiliations")
        unnumbered = [a for a in authors if "(" not in a]
        if unnumbered:
            errors[name].append(f"authors without affiliation numbers: {unnumbered}")
    elif numbers - {1}:
        errors[name].append(f"affiliation numbers {sorted(numbers)} but only {len(affiliations)} affiliation(s)")

    note = page.get("author_note") or ""
    for mark in "*†":
        marked = any(mark in a for a in authors)
        if marked and mark not in note:
            warnings[name].append(f"{mark} used on an author but not explained in author_note")
        if mark in note and not marked:
            warnings[name].append(f"author_note mentions {mark} but no author is marked")


def check_links(name, page):
    urls = []
    for group, links in (page.get("links") or {}).items():
        if group not in LINK_GROUPS:
            warnings[name].append(f"link group {group!r} has no icon (use one of {sorted(LINK_GROUPS)})")
        if not isinstance(links, dict):
            errors[name].append(f"link group {group} should be 'text: url' entries")
            continue
        for text, url in links.items():
            if not str(url).startswith("https://"):
                warnings[name].append(f"link {group}/{text} is not an https:// URL: {url}")
            urls.append((name, f"{group}/{text}", url))

    for video in page.get("videos") or []:
        if "youtube" in video and not re.fullmatch(r"https://www\.youtube\.com/embed/[\w-]{11}", video):
            errors[name].append(f"YouTube video should be https://www.youtube.com/embed/<11-character id>: {video}")
        elif "://" in video and "youtube" not in video and not video.lower().endswith(".mp4"):
            warnings[name].append(f"video is neither a YouTube embed nor an .mp4: {video}")
        if "://" in video:
            urls.append((name, "video", video))
    return urls


def check_text(name, page):
    abstract = " ".join(as_list(page.get("abstract")))
    for field, value in [("title", page.get("title", "")), ("venue", page.get("venue", "")), ("abstract", abstract)]:
        if re.search(r"Ã.|â€|�", value):
            errors[name].append(f"{field} contains garbled characters")
        if "  " in value or value != value.strip():
            warnings[name].append(f"{field} has extra spaces")

    bibtex = page.get("bibtex") or ""
    if not re.match(r"\s*@\w+\s*\{", bibtex):
        errors[name].append("bibtex should start with @type{")
    if bibtex.count("{") != bibtex.count("}"):
        errors[name].append("bibtex braces are unbalanced")
    match = re.search(r"\btitle\s*=\s*[{\"]+(.*?)[}\"]+\s*,?\s*$", bibtex, re.M | re.I)
    simplify = lambda s: re.sub(r"\W", "", s.lower())
    if match and simplify(match.group(1)) != simplify(page.get("title", "")):
        warnings[name].append(f"bibtex title differs from page title: {match.group(1)[:70]!r}")


def check_project(folder, listed_year, highlight_author, seen):
    name = f"projects/{folder}"
    directory = os.path.join(ROOT, "projects", folder)
    files = set(os.listdir(directory))

    for file in files:
        if file.startswith(".") or file in ("Thumbs.db", "desktop.ini"):
            warnings[name].append(f"junk file: {file}")
    if "index.html" not in files:
        if folder not in FOLDERS_WITHOUT_PAGE:
            errors[name].append("no index.html")
        return []

    try:
        page, body = read_front_matter(os.path.join(directory, "index.html"))
    except yaml.MarkedYAMLError as e:
        line = e.problem_mark.line + 2 if e.problem_mark else "?"
        errors[name].append(f"YAML error in index.html at line {line}: {e.problem} (check indentation)")
        return []
    except Exception as e:
        errors[name].append(f"cannot read index.html: {e}")
        return []
    if body:
        errors[name].append("index.html has content after the closing ---")
    if page.get("layout") != "project":
        return []

    for field in REQUIRED_FIELDS:
        if not page.get(field):
            errors[name].append(f"missing field: {field}")
    for field in page:
        if field not in REQUIRED_FIELDS + OPTIONAL_FIELDS:
            errors[name].append(f"unknown field (typo?): {field}")

    if folder not in UNLISTED_PROJECTS and listed_year is None:
        errors[name].append("not listed in _data/publications.yml")

    is_thesis = page.get("paper_label") == "Thesis"
    used = {"index.html"}
    referenced = [("thumbnail", page.get("thumbnail")), ("paper", page.get("paper"))]
    referenced += [("teaser", t) for t in as_list(page.get("teaser"))]
    referenced += [("video", v) for v in page.get("videos") or [] if "://" not in v]
    for kind, file in referenced:
        if not file:
            continue
        used.add(file)
        if file not in files:
            errors[name].append(f"{kind} file not found: {file}")
            continue
        if kind in ("thumbnail", "teaser") and file.lower().endswith(IMAGE_EXTENSIONS):
            used.add(check_image(name, folder, file))
            digest = hashlib.md5(open(os.path.join(directory, file), "rb").read()).hexdigest()
            seen["image"][digest].append(f"{folder}/{file}")

    for file in sorted(files - used):
        warnings[name].append(f"unused file: {file}")
    for file in sorted(files - {"index.html"} - KNOWN_NAME_EXCEPTIONS):
        if not file.startswith(folder + "_") and not is_thesis:
            warnings[name].append(f"file name doesn't start with the folder name: {file}")

    paper_year = re.fullmatch(re.escape(folder) + r"_(\d{4})\.pdf", page.get("paper") or "")
    if paper_year and listed_year and int(paper_year.group(1)) != listed_year and page.get("paper") not in KNOWN_NAME_EXCEPTIONS:
        warnings[name].append(f"PDF is named for {paper_year.group(1)} but listed under {listed_year}")

    check_authors(name, page)
    if not any(author_name(a) == highlight_author for a in page.get("authors") or []):
        warnings[name].append(f"{highlight_author} is not in the author list")
    check_text(name, page)

    seen["title"][page.get("title", "").lower()].append(folder)
    seen["abstract"][" ".join(as_list(page.get("abstract")))[:200]].append(folder)
    return check_links(name, page)


def check_listed_pages():
    for page_path, key, fields in [
        ("teaching/cpsc_532i/index.html", "schedule", None),
        ("art/index.html", "artworks", ("image", "thumb")),
        ("team/index.html", None, None),
    ]:
        page, _ = read_front_matter(os.path.join(ROOT, page_path))
        base = os.path.dirname(os.path.join(ROOT, page_path))
        paths = []
        if key == "schedule":
            for lecture in page.get("schedule") or []:
                for slide in lecture.get("slides") or []:
                    paths += [slide.get("thumb")] + ([slide["file"]] if slide.get("file") else [])
        elif key == "artworks":
            for art in page.get("artworks") or []:
                paths += [art.get(f) for f in fields]
        else:
            for person in (page.get("students") or []) + (page.get("alumni") or []):
                paths.append(person.get("photo"))
        for path in paths:
            full = os.path.join(ROOT, path.lstrip("/")) if path and path.startswith("/") else os.path.join(base, path or "")
            if not path or not os.path.exists(full):
                errors[page_path].append(f"file not found: {path}")


def check_urls(urls):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

    def status(url):
        for method in ("HEAD", "GET"):
            try:
                return urllib.request.urlopen(urllib.request.Request(url, headers=headers, method=method), timeout=25).status
            except urllib.error.HTTPError as e:
                if method == "GET":
                    return e.code
            except Exception as e:
                if method == "GET":
                    return type(e).__name__

    with concurrent.futures.ThreadPoolExecutor(16) as pool:
        results = pool.map(lambda item: (*item, status(item[2])), urls)
        for name, label, url, code in results:
            if code != 200:
                warnings[name].append(f"link {label} returned {code}: {url}")


def main():
    publications = yaml.safe_load(open(os.path.join(ROOT, "_data", "publications.yml")))
    listed = Counter(n for group in publications["years"] for n in group["projects"])
    year_of = {n: group["year"] for group in publications["years"] for n in group["projects"]}
    for project, count in listed.items():
        if count > 1:
            errors["_data/publications.yml"].append(f"{project} is listed {count} times")
        if not os.path.isfile(os.path.join(ROOT, "projects", project, "index.html")):
            errors["_data/publications.yml"].append(f"{project} is listed but projects/{project}/index.html doesn't exist")

    seen = {"title": defaultdict(list), "abstract": defaultdict(list), "image": defaultdict(list)}
    folders = sorted(f for f in os.listdir(os.path.join(ROOT, "projects")) if os.path.isdir(os.path.join(ROOT, "projects", f)))
    urls = []
    for folder in folders:
        urls += check_project(folder, year_of.get(folder), publications["highlight_author"], seen)
    for kind, groups in seen.items():
        for projects in groups.values():
            if len(projects) > 1:
                errors["projects"].append(f"same {kind} in {projects} (copied from another project?)")

    check_listed_pages()
    if "--links" in sys.argv:
        print(f"Checking {len(urls)} external links...")
        check_urls(urls)

    for title, found in [("ERRORS", errors), ("WARNINGS", warnings)]:
        if found:
            print(f"\n{title}")
            for name in sorted(found):
                print(f"  {name}")
                for message in found[name]:
                    print(f"    - {message}")
    error_count = sum(len(v) for v in errors.values())
    warning_count = sum(len(v) for v in warnings.values())
    print(f"\nChecked {len(folders)} project folders: {error_count} errors, {warning_count} warnings.")
    sys.exit(1 if error_count else 0)


if __name__ == "__main__":
    main()
