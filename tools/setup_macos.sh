#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# setup_macos.sh — Bootstrap the markdown-book-pipeline on macOS
# ─────────────────────────────────────────────────────────────────────────────
#
# ⚠️  READ THIS SCRIPT BEFORE YOU RUN IT.
#
# This script installs software on your machine. Running shell scripts from
# the internet without reading them is a bad habit. This one is short on
# purpose — read every line, understand what it does, then decide if you
# want to run it.
#
# What this script does:
#   1. Checks for Homebrew (does NOT install it — that's your call)
#   2. Installs pandoc via Homebrew (the format conversion engine)
#   3. Installs BasicTeX via Homebrew cask (smaller alternative to MacTeX, ~100MB vs ~5GB)
#   4. Installs uv via Homebrew (Python package/venv manager)
#   5. Creates a local .venv in the repo and installs Python dependencies
#   6. Downloads epubcheck into tools/ (no system install, gitignored)
#
# What this script does NOT do:
#   - Install Homebrew (see https://brew.sh)
#   - Install the full MacTeX distribution (see below if you want it)
#   - Modify your shell profile or PATH permanently
#   - Run with sudo (if something asks for your password, stop and read why)
#
# Prerequisites:
#   - macOS
#   - Homebrew (https://brew.sh)
#
# Usage:
#   cd markdown-book-pipeline
#   bash tools/setup_macos.sh
#
# If you want full MacTeX instead of BasicTeX (5GB+ download):
#   brew install --cask mactex
#
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EPUBCHECK_VERSION="5.1.0"
EPUBCHECK_URL="https://github.com/w3c/epubcheck/releases/download/v${EPUBCHECK_VERSION}/epubcheck-${EPUBCHECK_VERSION}.zip"

# ── Colors (if terminal supports them) ──────────────────────────────────────
if [ -t 1 ]; then
    BOLD="\033[1m"
    GREEN="\033[32m"
    YELLOW="\033[33m"
    RED="\033[31m"
    RESET="\033[0m"
else
    BOLD="" GREEN="" YELLOW="" RED="" RESET=""
fi

info()  { echo -e "${GREEN}[✓]${RESET} $*"; }
warn()  { echo -e "${YELLOW}[!]${RESET} $*"; }
fail()  { echo -e "${RED}[✗]${RESET} $*"; exit 1; }
step()  { echo -e "\n${BOLD}── $* ──${RESET}"; }

# ── Preflight ────────────────────────────────────────────────────────────────

step "Checking prerequisites"

if [ "$(uname)" != "Darwin" ]; then
    fail "This script is for macOS only."
fi

if ! command -v brew &>/dev/null; then
    fail "Homebrew not found. Install it first: https://brew.sh"
fi

info "Homebrew found: $(brew --prefix)"

# ── Pandoc ───────────────────────────────────────────────────────────────────

step "Pandoc"

if command -v pandoc &>/dev/null; then
    info "pandoc already installed: $(pandoc --version | head -1)"
else
    warn "Installing pandoc via Homebrew..."
    brew install pandoc
    info "pandoc installed: $(pandoc --version | head -1)"
fi

# ── LaTeX (BasicTeX) ────────────────────────────────────────────────────────

step "LaTeX (BasicTeX)"

if command -v xelatex &>/dev/null; then
    info "xelatex already available: $(xelatex --version | head -1)"
else
    warn "Installing BasicTeX via Homebrew (this may take a few minutes)..."
    brew install --cask basictex

    # BasicTeX puts binaries in /Library/TeX/texbin — add to PATH for this session
    export PATH="/Library/TeX/texbin:$PATH"

    if command -v xelatex &>/dev/null; then
        info "BasicTeX installed. xelatex available."
    else
        warn "BasicTeX installed but xelatex not on PATH yet."
        warn "You may need to restart your terminal, or add to your shell profile:"
        warn '  export PATH="/Library/TeX/texbin:$PATH"'
    fi
fi

# ── uv + Python venv ────────────────────────────────────────────────────────

step "uv and Python environment"

if command -v uv &>/dev/null; then
    info "uv already installed: $(uv --version)"
else
    warn "Installing uv via Homebrew..."
    brew install uv
    info "uv installed: $(uv --version)"
fi

cd "$REPO_ROOT"

if [ -d ".venv" ]; then
    info ".venv already exists"
else
    warn "Creating .venv..."
    uv venv
    info ".venv created"
fi

warn "Installing Python dependencies..."
uv pip install -r pyproject.toml
info "Python dependencies installed"

# ── epubcheck (local, not system-level) ──────────────────────────────────────

step "epubcheck (optional, local install)"

EPUBCHECK_DIR="${REPO_ROOT}/tools/epubcheck-${EPUBCHECK_VERSION}"

if [ -f "${EPUBCHECK_DIR}/epubcheck.jar" ]; then
    info "epubcheck ${EPUBCHECK_VERSION} already present in tools/"
else
    if ! command -v java &>/dev/null; then
        warn "Java not found — skipping epubcheck download."
        warn "epubcheck requires Java. Install it if you want EPUB validation:"
        warn "  brew install --cask temurin"
    else
        warn "Downloading epubcheck ${EPUBCHECK_VERSION}..."
        TMPZIP="$(mktemp)"
        curl -fsSL "$EPUBCHECK_URL" -o "$TMPZIP"
        unzip -qo "$TMPZIP" -d "${REPO_ROOT}/tools/"
        rm -f "$TMPZIP"
        info "epubcheck ${EPUBCHECK_VERSION} installed to tools/"
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────────────

step "Done"

echo ""
echo "  To activate the virtual environment:"
echo "    source .venv/bin/activate"
echo ""
echo "  Or run commands directly through uv:"
echo "    uv run python scripts/build.py example --all --verbose"
echo ""
echo "  For PDF builds, make sure xelatex is on your PATH:"
echo '    export PATH="/Library/TeX/texbin:$PATH"'
echo ""
