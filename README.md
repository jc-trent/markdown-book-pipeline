# markdown-book-pipeline

A markdown-first build pipeline for self-publishing novels. Write in plain text, build to EPUB, DOCX, PDF, and merged markdown from the same source files.

This is a personal tool that I use to publish my own books. I'm sharing it because the information I needed to build it was scattered across dozens of docs, forums, and blog posts, and I figured someone else might save some time.

## What This Is

A set of Python scripts that:

- Assemble a novel from markdown chapter files (front matter → chapters → back matter)
- Call [pandoc](https://pandoc.org) to produce publication-ready **EPUB**, **DOCX**, **PDF**, and merged **Markdown**
- Lint your manuscript for encoding issues, structural problems, and formatting inconsistencies
- Post-process EPUBs for accessibility compliance and retailer requirements
- Validate EPUBs with [epubcheck](https://www.w3.org/publishing/epubcheck/)
- Run from a single CLI entry point with subcommands for building, linting, and validating

## What This Is Not

- Polished software. It works on my machine. It has rough edges.
- A replacement for learning your tools. If you don't understand what a command does, don't run it.
- A WYSIWYG editor, a writing app, or a Scrivener replacement.
- Tested on Windows. It might work. I have no idea. I develop on macOS.
- Accepting pull requests (see [Contributing](#contributing)).

## A Warning on Defaults (and Customization)

If you are just reading this repo to see how someone else solved the markdown-to-book problem, enjoy.

If you actually intend to clone this and use it to publish your own books, you need to understand that **this pipeline is highly opinionated.** The shared resources in the `artifacts/` directory are not generic, neutral templates. They are exactly what I use to publish my own dark military fantasy novels:
- `epub.css` contains my specific typography choices, margin preferences, and scene-break styling.
- `book.tex` is a LaTeX template hardcoded to produce a 6x9 trade paperback with my preferred header/footer layout, chapter drops, and font pairings.

**It will not look the way you want it to look out of the box.** The entire point of this pipeline is customization. If you don't like my fonts, you must open the CSS and change them. If you want a 5x8 paperback instead of a 6x9, you must modify the LaTeX geometry. You are taking ownership of the typesetting, which means you have to actually typeset.

## Who This Is For

You might like this if you:

- Write in plain text and want version control (git) over your manuscript
- Want reproducible, one-command builds across multiple output formats
- Don't mind a little tooling to get there
- Have some comfort with the command line and Python

You probably won't like this if you:

- Want to see formatting while you write
- Never want to open a terminal
- Want something that works out of the box with no setup

## A Note on Security

**Do not run commands you don't understand.** This applies to this repo and every other repo on the internet.

This project includes Python scripts, shell scripts, Lua filters, and LaTeX templates. Before you run any of them, read them. They're short. If you don't understand what a script does, don't execute it. That's not paranoia — that's how you're supposed to use software you downloaded from a stranger's GitHub.

If you took some Python classes and thought it was cool, you can read these scripts. If you've never written code before, this is a fine learning project — but learn what you're running before you run it.

## Requirements

| Tool | What it does | Install (macOS) |
|------|-------------|-----------------|
| [Homebrew](https://brew.sh) | macOS package manager | See [Setup on macOS](#setup-on-macos) |
| [Python 3.8+](https://www.python.org) | Build orchestration, linting, post-processing | Comes with macOS, or `brew install python` |
| [uv](https://docs.astral.sh/uv/) | Python virtual environment and package management | `brew install uv` |
| [pandoc](https://pandoc.org) | Converts markdown to EPUB, DOCX, LaTeX | `brew install pandoc` |
| [XeLaTeX](https://tug.org/xetex/) | PDF compilation (optional) | `brew install --cask basictex` |
| [epubcheck](https://www.w3.org/publishing/epubcheck/) | EPUB validation (optional) | Downloaded locally by setup script |
| [git](https://git-scm.com) | Version control | `brew install git` or [download](https://git-scm.com/downloads) |

## Setup on macOS

The fastest way to get running is with [Homebrew](https://brew.sh), the macOS package manager.

### Automated setup

There's a setup script at `tools/setup_macos.sh` that installs the dependencies listed above. **Read the script before you run it.** It's commented and explains every step.

```bash
# Read it first
cat tools/setup_macos.sh

# Then run it
bash tools/setup_macos.sh
```

The script installs pandoc, BasicTeX, and [uv](https://docs.astral.sh/uv/) via Homebrew, creates a local `.venv` in the repo, installs Python dependencies, and downloads epubcheck into `tools/`. Nothing is hidden. Nothing runs with `sudo`.

### Manual setup

If you'd rather do it yourself:

```bash
# Install the tools
brew install pandoc uv git

# For PDF support (pick one):
brew install --cask basictex      # ~100MB, just the essentials
brew install --cask mactex        # ~5GB, everything including the kitchen sink

# Clone the repo
git clone https://github.com/jc-trent/markdown-book-pipeline.git
cd markdown-book-pipeline

# Create a virtual environment and install dependencies
uv venv
uv pip install -r pyproject.toml

# Activate the venv
source .venv/bin/activate
```

### A note on BasicTeX vs MacTeX

- **BasicTeX** (~100MB) includes `xelatex` and enough to build PDFs with this pipeline. It's what the setup script installs.
- **MacTeX** (~5GB) is the full TeX Live distribution. You only need this if you're doing heavy LaTeX work beyond what this pipeline requires.

If you install BasicTeX, make sure `/Library/TeX/texbin` is on your `PATH`:

```bash
export PATH="/Library/TeX/texbin:$PATH"
```

Add that to your `~/.zshrc` (or `~/.bashrc`) to make it permanent.

### Why uv?

[uv](https://docs.astral.sh/uv/) is a fast Python package and project manager. It replaces `pip`, `venv`, and `pip-tools` with a single tool that's significantly faster. The pipeline uses it to:

- Create an isolated `.venv` inside the repo (gitignored, no system-level pollution)
- Install dependencies from `pyproject.toml`
- Run scripts without activating the venv: `uv run python scripts/build.py ...`

If you already have a Python workflow you prefer, that's fine — `pip install pyyaml` in any virtual environment still works. uv is a convenience, not a hard requirement.

## Project Structure

```
├── scripts/
│   ├── build.py                    ← single CLI entry point
│   └── booklib/
│       ├── config.py               ← book.yaml loading + validation
│       ├── resolve.py              ← book resolution, file assembly
│       ├── epubcheck.py            ← epubcheck runner
│       ├── postprocess.py          ← EPUB accessibility patching
│       ├── lint.py                 ← manuscript linter
│       └── builders/
│           ├── base.py             ← shared builder interface
│           ├── epub.py
│           ├── docx.py
│           ├── pdf.py
│           └── markdown.py
├── artifacts/                      ← shared across all books
│   ├── epub.css                    ← EPUB stylesheet
│   ├── book.tex                    ← LaTeX template for PDF
│   ├── pdf_filter.lua              ← pandoc filter for PDF builds
│   └── strip_formatting.lua        ← pandoc filter for clean markdown
├── manuscript/
│   └── 1_example_book/             ← one directory per book
│       ├── book.yaml               ← title, author, series, format settings
│       ├── front/
│       │   ├── 00_titlepage.md
│       │   ├── 01_copyright.md
│       │   └── 02_epigraph.md
│       ├── chapters/
│       │   ├── 01_Chapter_One.md
│       │   ├── 02_Chapter_Two.md
│       │   └── 03_Chapter_Three.md
│       ├── back/
│       │   └── 01_acknowledgments.md
│       └── artifacts/              ← per-book overrides
│           ├── cover.jpg
│           └── reference.docx
├── tools/
│   └── setup_macos.sh              ← macOS bootstrap script
├── output/                         ← build output (gitignored)
├── pyproject.toml                  ← Python dependencies
├── .gitignore
└── README.md
```

## Quick Start

```bash
# Clone the repo
git clone https://github.com/jc-trent/markdown-book-pipeline.git
cd markdown-book-pipeline

# Set up (macOS)
bash tools/setup_macos.sh

# Build all formats for the example book
uv run python scripts/build.py example --all --verbose

# Or activate the venv and run directly
source .venv/bin/activate
python scripts/build.py example --all --verbose

# Lint the manuscript
python scripts/build.py lint example

# Just the EPUB
python scripts/build.py example --epub

# Chapters-only DOCX for sending to an editor
python scripts/build.py example --docx --ms-only
```

Output goes to `output/`.

## Usage

### Building

```bash
python scripts/build.py <book> --epub --docx     # Specific formats
python scripts/build.py <book> --all              # EPUB + DOCX + Markdown
python scripts/build.py <book> --pdf              # PDF (requires XeLaTeX)
python scripts/build.py <book> --pdf --keep-tex   # PDF, keep intermediate files
python scripts/build.py <book> --docx --ms-only   # Chapters only (for editors)
```

The `<book>` identifier can be a number (`1`), a keyword from the directory name (`example`), or a direct path (`manuscript/1_example_book`).

### Linting

```bash
python scripts/build.py lint <book>               # Check for issues
python scripts/build.py lint <book> --fix          # Auto-fix what's fixable
python scripts/build.py lint <book> --chapters     # Chapters only
```

The linter catches encoding issues (curly quotes, non-breaking spaces, zero-width characters), structural problems (missing headings, unclosed fenced divs, malformed scene breaks), and formatting inconsistencies.

### Validating

```bash
python scripts/build.py validate <book>            # Run epubcheck
python scripts/build.py validate <book> --json-report
```

## book.yaml

Each book has a `book.yaml` that controls metadata and build settings:

```yaml
title: "Lorem Ipsum"
author: "A. N. Author"
prefix: "lorem_ipsum"             # Output filename prefix
lang: en-US
series: "Example Series"
series_number: 1

# Pandoc markdown extensions
markdown_extensions: "fenced_divs+native_divs"

# Shared Lua filters (resolved from artifacts/)
filters:
  - pdf_filter.lua

# Format-specific settings (all have sensible defaults)
epub:
  toc: true
  toc_depth: 1
  css: epub.css               # Resolved from artifacts/
  cover: cover.jpg            # Resolved from book's artifacts/
  cover_alt: "Cover image for Lorem Ipsum"
  accessibility:
    accessMode: textual
    accessModeSufficient: textual
    accessibilityFeature:
      - structuralNavigation
      - tableOfContents
      - readingOrder
      - alternativeText
    accessibilityHazard: none
    accessibilitySummary: >
      This publication meets WCAG 2.0 Level AA guidelines.

docx:
  toc: true
  toc_depth: 1
  reference: reference.docx   # Resolved from book's artifacts/

pdf:
  template: book.tex           # Resolved from artifacts/
  filter: pdf_filter.lua
  engine: xelatex
  scene_break_macro: "\\scenebreak{}"
  job_suffix: "_print_6x9"
```

Artifacts are resolved in order: book's `artifacts/` → repo-level `artifacts/` → fallback. This means you can override any shared resource on a per-book basis.

## Adding a New Book

1. Create a new directory under `manuscript/`:
   ```
   manuscript/2_your_next_book/
   ```

2. Add a `book.yaml` with at minimum `title`, `author`, and `prefix`.

3. Add markdown files to `front/`, `chapters/`, and `back/`. Files are assembled in natural sort order (so `02_` comes before `10_`).

4. Optionally add per-book artifacts (cover image, DOCX reference template) to `artifacts/`.

5. Build:
   ```bash
   python scripts/build.py 2 --all
   ```

## Writing Conventions

These are the conventions the pipeline expects. They're not mandatory — adjust to taste — but the linter and build scripts are tuned for them.

- **Scene breaks:** `***` on its own line, with a blank line before and after.
- **Chapter headings:** `# Chapter Title` (ATX-style, level 1).
- **Front/back matter headings:** `# Title {.unnumbered .unlisted}` to keep them out of the TOC.
- **Fenced divs:** `::: {.classname}` for special formatting (military documents, letters, etc.).
- **Smart punctuation:** Write straight quotes and `---` for em-dashes. Pandoc's `+smart` extension handles the typography at build time.
- **One file per chapter.** Name them with numeric prefixes for sort order: `01_Chapter_One.md`, `02_Chapter_Two.md`.

## My Workflow

For what it's worth, this is how I actually use it:

- **Draft** in [Obsidian](https://obsidian.md) — just write, don't think about formatting.
- **Edit** in [VS Code](https://code.visualstudio.com) — find-and-replace across 30 chapter files, run builds from the task runner.
- **Build** with one command — `python scripts/build.py trench --all --verbose`.
- **Send DOCX to editors** — `--docx --ms-only` gives them chapters without front/back matter.
- **Review in git** — `git diff` shows every prose change, line by line, across every file.
- **Professional editors** handle line editing, copy editing, proofreading, and cover art. The pipeline handles everything else.

## Contributing

**I'm not accepting pull requests.** This isn't a community project — it's a personal tool that I'm sharing because it might be useful. I don't have the bandwidth to review, test, or maintain other people's changes, especially for platforms I can't test on.

If you want to add Windows support, a GUI, plugin architecture, or anything else — that's awesome. **Fork it.** Make it yours. If you build something cool, let me know. I'd love to see it, and if your fork outgrows mine, I'll happily link to it.

**Bug reports are welcome** if you find something that's genuinely broken (not "it doesn't work on my machine" — I know it doesn't work on your machine, it works on mine). Open an issue with what you expected, what happened, and what your setup looks like.

## Tradeoffs

I want to be honest about what you're signing up for:

- **More setup than Scrivener.** Significantly more. You need pandoc, Python, and comfort with the command line. In exchange, you get version control, reproducible builds, and full control over every output format.
- **No WYSIWYG.** You write in plain text. You don't see formatting until you build. Some people love this. Some people hate it.
- **Pandoc is the engine.** When pandoc has a bug or limitation, so does this pipeline. The Lua filters work around some of them, but you'll occasionally hit something weird. The [pandoc manual](https://pandoc.org/MANUAL.html) is your best friend.
- **PDF builds are slow.** XeLaTeX does two compilation passes. On a 100k-word novel, expect 10–30 seconds. It will eat your CPU. It's worth it.

I haven't made anything better. I've traded one set of friction for a different set that I personally find more tolerable. If the tools you're already using work for you, keep using them.

## License

MIT. Do whatever you want with it. See [LICENSE](LICENSE).

## Links

- [uv documentation](https://docs.astral.sh/uv/) — Python package and project manager
- [Homebrew](https://brew.sh) — macOS package manager
- [pandoc User's Guide](https://pandoc.org/MANUAL.html)
- [pandoc Lua Filters](https://pandoc.org/lua-filters.html)
- [EPUBCheck](https://www.w3.org/publishing/epubcheck/)
- [git - the simple guide](https://rogerdudler.github.io/git-guide/) — if you're new to git, start here
- [Atlassian Git Tutorials](https://www.atlassian.com/git/tutorials) — structured, practical walkthroughs
