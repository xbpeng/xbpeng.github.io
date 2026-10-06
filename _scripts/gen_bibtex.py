"""Collect the BibTeX of every project into a single publications.bib file.

Entries follow the order of _data/publications.yml. Projects not listed there (e.g. the theses)
are added at the end, and projects without BibTeX are skipped. Raises an error if two entries
share a citation key. The .bib file is written next to this script.

Usage (requires PyYAML):
    python _scripts/gen_bibtex.py
"""
import os
import re

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(SCRIPT_DIR, "..")
OUTPUT = os.path.join(SCRIPT_DIR, "publications.bib")


def read_bibtex(project):
    text = open(os.path.join(ROOT, "projects", project, "index.html"), encoding="utf-8").read()
    page = yaml.safe_load(text.split("---\n")[1])
    return page.get("bibtex", "").strip()


def citation_key(bibtex):
    match = re.match(r"@\w+\s*\{\s*([^,\s]+)\s*,", bibtex)
    return match.group(1) if match else None


def main():
    publications = yaml.safe_load(open(os.path.join(ROOT, "_data", "publications.yml")))
    listed = [project for group in publications["years"] for project in group["projects"]]

    projects_dir = os.path.join(ROOT, "projects")
    with_pages = sorted(
        folder for folder in os.listdir(projects_dir)
        if os.path.isfile(os.path.join(projects_dir, folder, "index.html"))
    )
    order = listed + [p for p in with_pages if p not in listed]

    entries, keys = [], {}
    for project in order:
        bibtex = read_bibtex(project)
        if not bibtex:
            continue
        key = citation_key(bibtex)
        if key in keys:
            raise ValueError(f"Citation key '{key}' is used by both {keys[key]} and {project}")
        keys[key] = project
        entries.append(bibtex)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n\n".join(entries) + "\n")
    print(f"Wrote {len(entries)} entries to {os.path.relpath(OUTPUT, ROOT)}")


if __name__ == "__main__":
    main()
