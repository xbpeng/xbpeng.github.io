# xbpeng.github.io

Personal website, built by GitHub Pages with Jekyll. Pushing to `master` publishes the site
(it takes a minute or two to update).

## Where things are

| Path | What it contains |
|---|---|
| `index.html` | Home page: bio, codebase, publication list, thesis |
| `_data/publications.yml` | Which publications appear on the home page, grouped by year, in display order |
| `projects/<Name>/index.html` | All info for one publication (YAML only), plus its PDF and images |
| `_layouts/project.html` | Template for every project page |
| `_includes/publication.html` | Template for one publication entry on the home page |
| `_includes/meta.html` | Search, link-preview, and Google Scholar tags (generated automatically) |
| `_includes/small_image.html` | Picks the compressed `_small.jpg` copy of an image when it exists |
| `_includes/icon.html` | Icons for the project page buttons |
| `_layouts/default.html` | Shared page frame: navigation bar, fonts, analytics |
| `css/main.css` | All styling. Colors and fonts are variables at the top |
| `_scripts/make_small_images.py` | Makes compressed copies of thumbnails and teasers |
| `teaching/cpsc_532i/index.html` | Course page. The lecture schedule is YAML at the top of the file |

## Adding a new publication

1. Copy an existing project folder, e.g. `projects/DeepMimic`, to `projects/<Name>`, and replace the
   PDF and images with the new ones.
2. Edit the YAML in `projects/<Name>/index.html` (see the field reference below).
3. Add `<Name>` to `_data/publications.yml` under the right year, at the position where it
   should appear on the home page.
4. Make compressed copies of the thumbnail and teaser:
   ```
   python _scripts/make_small_images.py
   ```
   This creates `*_small.jpg` files next to the originals; commit them too. If you skip this
   step, the site still works but uses the full-size images.
5. Preview locally (see below), then commit and push.

## Project page fields

```yaml
---
layout: project                          # required

title: "Paper Title"

venue: "ACM Transactions on Graphics (Proc. SIGGRAPH 2026)"   # shown on the project page and home page

award: "Best Paper Award"                # optional

# Numbers in parentheses refer to the affiliations list. Leave them out if there is only one
# affiliation. Mark joint authors with * or †. The home page strips the numbers and markers.
authors:
  - "First Author* (1)"
  - "Second Author* (2)"
  - "Xue Bin Peng (1, 2)"

affiliations:                            # optional; numbered automatically when there are several
  - "Simon Fraser University"
  - "NVIDIA"

author_note: "*Joint first authors."     # optional

thumbnail: "Name_thumb.png"              # image on the home page

teaser: "Name_teaser.png"                # one image or .mp4 video, or a list of them
teaser_width: "49%"                      # optional, default 100% (e.g. for two images side by side)

paper: "Name_2026.pdf"                   # the "Paper: PDF" link, and [Paper] on the home page
paper_label: "Thesis"                    # optional, default "Paper"

# Optional extra links, shown as buttons in this order. The group name (Code, Webpage, Preprint,
# Media) picks the button's icon, and the link text is the button's label ("Link" shows the group
# name instead, and "GitHub" shows "Code").
links:
  Code:
    GitHub: "https://github.com/..."
  Webpage:
    Link: "https://..."
  Preprint:
    arXiv: "https://arxiv.org/abs/..."

# Optional. Each entry is an embed URL (e.g. https://www.youtube.com/embed/<id>, not the
# normal youtube.com/watch link) or an .mp4 file.
videos:
  - "https://www.youtube.com/embed/<id>"

abstract: >-
  Abstract text. Lines are joined with spaces, so it can be wrapped freely.
  For several paragraphs, use a list instead, with one "- >-" entry per paragraph.

bibtex: |
  @inproceedings{
  	key,
  	title={Paper Title},
  	author={Author, First and Peng, Xue Bin},
  	booktitle={...},
  	year={2026}
  }
---
```

YAML tips:
- Every line inside `abstract:` and `bibtex:` must be indented by at least 2 spaces, including
  the closing `}` of the bibtex. Otherwise the page fails to load and the home page shows a red
  "Missing project page" entry.
- Put text containing `:` or `#` in double quotes.

## Previewing locally

With Docker installed, run from the repository root:

```
docker run --rm -it -p 4001:4000 -v "$PWD":/site -w /site ruby:3.2 \
  bash -c "gem install github-pages webrick --no-document -q && jekyll serve --safe --host 0.0.0.0 -d /tmp/_site"
```

Then open http://localhost:4001. Startup takes about a minute; after that, saved changes are
rebuilt automatically (refresh the browser). Changes to `_config.yml` need a restart.
