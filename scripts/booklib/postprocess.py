"""
Post-process a pandoc-generated EPUB for retailer compliance.

Fixes:
    1. Cover image alt text (epubcheck warning)
    2. Accessibility metadata in OPF (EU Accessibility Act)
    3. Dublin Core / series metadata gaps
    4. Empty alt attributes on non-cover images

Can be called as a library function from EpubBuilder,
or standalone via: python -m booklib.postprocess book.epub --config book.yaml
"""

import os
import re
import sys
import zipfile
import tempfile
import shutil
import argparse

try:
    import yaml
except ImportError:
    yaml = None


def patch_epub(epub_path, config, verbose=False):
    """
    Unzip epub, patch OPF and cover XHTML, rezip.

    Args:
        epub_path: Path to the .epub file
        config:    BookConfig instance or dict with epub/accessibility keys
        verbose:   Print details

    Returns True on success.
    """
    # Support both BookConfig and raw dict
    if hasattr(config, "get"):
        epub_config = (
            config.get("epub", {}) if isinstance(config.get("epub"), dict) else {}
        )
        title = config.get("title", "book")
        series = config.get("series")
        series_number = config.get("series_number")
    else:
        epub_config = {}
        title = "book"
        series = None
        series_number = None

    accessibility = epub_config.get("accessibility", {})
    cover_alt = epub_config.get("cover_alt", f"Cover image for {title}")

    if not os.path.exists(epub_path):
        print(f"  Error: {epub_path} not found")
        return False

    tmpdir = tempfile.mkdtemp(prefix="epub_patch_")

    try:
        # ── Unzip ──────────────────────────────────────────
        with zipfile.ZipFile(epub_path, "r") as zin:
            zin.extractall(tmpdir)

        # ── Find OPF ──────────────────────────────────────
        opf_path = _find_file(tmpdir, ".opf")
        if not opf_path:
            print("  Error: No OPF file found in epub")
            return False

        # ── Patch OPF ─────────────────────────────────────
        _patch_opf(opf_path, accessibility, series, series_number, verbose)

        # ── Patch cover alt text ──────────────────────────
        _patch_cover(tmpdir, cover_alt, verbose)

        # ── Patch empty alt attrs ─────────────────────────
        _patch_empty_alts(tmpdir, verbose)

        # ── Rezip ─────────────────────────────────────────
        _rezip_epub(tmpdir, epub_path)

        return True

    except Exception as e:
        print(f"  Error during post-processing: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── Internal helpers ───────────────────────────────────────────────────


def _find_file(root_dir, extension):
    """Find first file with given extension under root_dir."""
    for root, dirs, files in os.walk(root_dir):
        for f in files:
            if f.endswith(extension):
                return os.path.join(root, f)
    return None


def _patch_opf(opf_path, accessibility, series, series_number, verbose):
    """Inject accessibility and series metadata into the OPF."""
    with open(opf_path, "r", encoding="utf-8") as f:
        opf = f.read()

    meta_lines = []

    # Accessibility metadata
    for prop in ["accessMode", "accessModeSufficient"]:
        val = accessibility.get(prop)
        if val:
            meta_lines.append(f'    <meta property="schema:{prop}">{val}</meta>')

    for feat in accessibility.get("accessibilityFeature", []):
        meta_lines.append(
            f'    <meta property="schema:accessibilityFeature">{feat}</meta>'
        )

    for prop in ["accessibilityHazard", "accessibilitySummary"]:
        val = accessibility.get(prop)
        if val:
            val = val.replace("\n", " ").strip()
            meta_lines.append(f'    <meta property="schema:{prop}">{val}</meta>')

    # Series metadata
    if series and "belongs-to-collection" not in opf:
        meta_lines.append(
            f'    <meta property="belongs-to-collection" id="series">{series}</meta>'
        )
        meta_lines.append(
            '    <meta refines="#series" property="collection-type">series</meta>'
        )
        if series_number:
            meta_lines.append(
                f'    <meta refines="#series" property="group-position">{series_number}</meta>'
            )

    if meta_lines and "</metadata>" in opf and "schema:accessMode" not in opf:
        meta_block = "\n".join(meta_lines)
        opf = opf.replace("</metadata>", f"{meta_block}\n  </metadata>")
        if verbose:
            print(f"  Injected {len(meta_lines)} metadata entries")

    with open(opf_path, "w", encoding="utf-8") as f:
        f.write(opf)


def _patch_cover(tmpdir, cover_alt, verbose):
    """Fix cover image alt text in XHTML files."""
    for root, dirs, files in os.walk(tmpdir):
        for fname in files:
            if not fname.endswith((".xhtml", ".html")):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            is_cover = "cover" in fname.lower() or (
                "cover" in content.lower()
                and ("<img" in content or "<image" in content or "<svg" in content)
            )
            if not is_cover:
                continue

            new_content = content

            # SVG <image> (pandoc 3.x): add <title> for accessibility
            if "<svg" in new_content and "<image" in new_content:
                if "<title>" not in new_content:
                    new_content = re.sub(
                        r"(<svg[^>]*>)",
                        rf"\1\n<title>{cover_alt}</title>",
                        new_content,
                    )
                if 'role="img"' not in new_content:
                    new_content = re.sub(
                        r"<svg(?![^>]*role=)",
                        '<svg role="img" ',
                        new_content,
                    )

            # HTML <img>: fix empty/missing alt
            if "<img" in new_content:
                new_content = re.sub(
                    r'(<img[^>]*?)alt=""',
                    rf'\1alt="{cover_alt}"',
                    new_content,
                )
                new_content = re.sub(
                    r"(<img(?![^>]*alt=)[^>]*?)(\/?>)",
                    rf'\1 alt="{cover_alt}" \2',
                    new_content,
                )

            if new_content != content:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                if verbose:
                    print(f"  Patched cover alt text in {fname}")


def _patch_empty_alts(tmpdir, verbose):
    """Replace any remaining alt="" with alt="decorative"."""
    for root, dirs, files in os.walk(tmpdir):
        for fname in files:
            if not fname.endswith((".xhtml", ".html")):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            new_content = content.replace('alt=""', 'alt="decorative"')
            if new_content != content:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                if verbose:
                    print(f"  Fixed empty alt text in {fname}")


def _rezip_epub(source_dir, output_path):
    """Rezip an unpacked epub. Mimetype must be first and uncompressed."""
    if os.path.exists(output_path):
        os.remove(output_path)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
        mimetype_path = os.path.join(source_dir, "mimetype")
        if os.path.exists(mimetype_path):
            zout.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)

        for root, dirs, files in os.walk(source_dir):
            for fname in sorted(files):
                if fname == "mimetype" and root == source_dir:
                    continue
                full_path = os.path.join(root, fname)
                arc_name = os.path.relpath(full_path, source_dir)
                zout.write(full_path, arc_name)


# ── Standalone CLI ─────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Post-process epub for compliance")
    parser.add_argument("epub", help="Path to epub file")
    parser.add_argument("--config", required=True, help="Path to book.yaml")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if not yaml:
        print("Error: PyYAML required. pip install pyyaml")
        sys.exit(1)

    with open(args.config) as f:
        config = yaml.safe_load(f)

    print(f"  Post-processing: {args.epub}")
    if patch_epub(args.epub, config, verbose=args.verbose):
        print("  Done.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
