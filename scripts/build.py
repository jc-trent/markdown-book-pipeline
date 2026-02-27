#!/usr/bin/env python3
"""
Unified build script for markdown-book-pipeline.

Combines building (epub, docx, pdf, markdown), linting, and
validation into a single entry point.

Usage:
    python build.py trench --epub --docx       Build epub + docx
    python build.py trench --all               Build all formats (except PDF)
    python build.py trench --pdf --keep-tex    Build PDF, keep intermediate files
    python build.py trench --docx --ms-only    Chapters only for editor submission
    python build.py lint trench                Lint manuscript source
    python build.py lint trench --fix          Lint and auto-fix
    python build.py validate trench            Run epubcheck on existing epub

Requires: pandoc, PyYAML
Optional: xelatex (PDF), java + epubcheck (validation)
"""

import os
import sys
import argparse
import traceback

# Ensure booklib is importable from the scripts/ directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from booklib.config import BookConfig, ConfigError
from booklib.resolve import find_book_dir, assemble_inputs, get_section_files
from booklib.builders import BUILDERS, DEFAULT_FORMATS
from booklib.lint import Linter
from booklib.epubcheck import validate_epub


# ── Resolve book ───────────────────────────────────────────────────────


def resolve_book(identifier):
    """Find book directory, load config. Exits on failure."""
    project_root = os.getcwd()
    book_dir = find_book_dir(identifier, project_root)

    if not book_dir:
        print(f"Error: Could not find book '{identifier}'")
        print(f"  Searched in: {os.path.join(project_root, 'manuscript')}")
        print("  Tip: Run from the project root, or pass a direct path.")
        sys.exit(1)

    try:
        config = BookConfig.load(book_dir)
    except ConfigError as e:
        print(f"Error: {e}")
        sys.exit(1)

    return book_dir, config


# ── Build command ──────────────────────────────────────────────────────


def cmd_build(args):
    """Build one or more output formats."""
    book_dir, config = resolve_book(args.book)

    # Determine which formats to build
    formats = []
    if args.all:
        formats = list(DEFAULT_FORMATS)
    else:
        for fmt in BUILDERS:
            if getattr(args, fmt, False):
                formats.append(fmt)

    # Default to --all if nothing specified
    if not formats:
        formats = list(DEFAULT_FORMATS)

    config.summary()
    if args.ms_only:
        print("  Mode:   manuscript-only (chapters/ only)")

    # Assemble input files
    input_files = assemble_inputs(book_dir, manuscript_only=args.ms_only)
    if not input_files:
        print(f"Error: No markdown files found in {book_dir}")
        sys.exit(1)

    # Output directory
    project_root = os.getcwd()
    output_dir = args.output_dir or os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    print(f"  Output: {output_dir}")

    # Suppress docx TOC for manuscript-only
    if args.ms_only:
        config._data.setdefault("docx", {})["toc"] = False

    # Build each format
    results = {}

    for fmt in formats:
        builder_cls = BUILDERS[fmt]

        # Collect format-specific kwargs
        kwargs = {
            "verbose": args.verbose,
            "no_validate": getattr(args, "no_validate", False),
            "json_report": getattr(args, "json_report", None),
            "keep_tex": getattr(args, "keep_tex", False),
        }

        builder = builder_cls(
            config=config,
            book_dir=book_dir,
            input_files=input_files,
            output_dir=output_dir,
            **kwargs,
        )
        results[fmt] = builder.build()

    # Summary
    print(f"\n{'─' * 60}")
    failed = [fmt for fmt, ok in results.items() if not ok]
    if failed:
        print(f"  Done with errors: {', '.join(failed)} failed")
        sys.exit(1)
    else:
        print(f"  Done. {len(results)} format(s) built successfully.")


# ── Lint command ───────────────────────────────────────────────────────


def cmd_lint(args):
    """Lint manuscript source files."""
    book_dir, config = resolve_book(args.book)

    color = not args.no_color and sys.stdout.isatty()

    print(f"\n  Linting: {config.title}")
    print(f"  Source:  {book_dir}")
    print(f"  Mode:    {'FIX' if args.fix else 'CHECK'}")
    print()

    # Gather files
    if args.chapters:
        files = get_section_files(book_dir, "chapters")
    else:
        files = (
            get_section_files(book_dir, "front")
            + get_section_files(book_dir, "chapters")
            + get_section_files(book_dir, "back")
        )

    if not files:
        # Flat layout fallback
        import glob
        from booklib.resolve import natural_sort_key

        files = sorted(
            glob.glob(os.path.join(book_dir, "*.md")),
            key=natural_sort_key,
        )

    if not files:
        print(f"  No markdown files found in {book_dir}")
        sys.exit(1)

    linter = Linter(
        book_dir=book_dir,
        files=files,
        fix=args.fix,
        verbose=args.verbose,
        color=color,
    )

    success = linter.run()
    sys.exit(0 if success else 1)


# ── Validate command ───────────────────────────────────────────────────


def cmd_validate(args):
    """Run epubcheck on an existing epub."""
    book_dir, config = resolve_book(args.book)

    project_root = os.getcwd()
    output_dir = args.output_dir or os.path.join(project_root, "output")
    epub_file = os.path.join(output_dir, f"{config.prefix}.epub")

    if not os.path.exists(epub_file):
        print(f"  Error: {epub_file} not found. Build with --epub first.")
        sys.exit(1)

    print(f"\n{'─' * 60}")
    print(f"  Validating: {epub_file}")
    print(f"{'─' * 60}")

    valid = validate_epub(
        epub_file,
        verbose=True,
        json_report=getattr(args, "json_report", None),
    )
    sys.exit(0 if valid else 1)


# ── Argument Parser ────────────────────────────────────────────────────


def build_parser():
    parser = argparse.ArgumentParser(
        description="Markdown book build pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s example --epub --docx      Build epub + docx
  %(prog)s example --all              Build epub, docx, and markdown
  %(prog)s example --pdf --keep-tex   Build PDF, keep .tex for debugging
  %(prog)s 1 --docx --ms-only        Editor submission (chapters only)
  %(prog)s lint example               Check for issues
  %(prog)s lint example --fix         Auto-fix what's fixable
  %(prog)s validate example           Run epubcheck on existing epub
        """,
    )

    sub = parser.add_subparsers(dest="command")

    # ── build (default when no subcommand) ─────────────────
    build_p = sub.add_parser("build", help="Build output formats (default)")
    _add_book_arg(build_p)
    _add_build_args(build_p)

    # ── lint ───────────────────────────────────────────────
    lint_p = sub.add_parser("lint", help="Lint manuscript source")
    _add_book_arg(lint_p)
    lint_p.add_argument("--fix", action="store_true", help="Auto-fix fixable issues")
    lint_p.add_argument("--chapters", action="store_true", help="Chapters only")
    lint_p.add_argument("--verbose", "-v", action="store_true")
    lint_p.add_argument("--no-color", action="store_true", help="Plain output")

    # ── validate ───────────────────────────────────────────
    val_p = sub.add_parser("validate", help="Run epubcheck on existing epub")
    _add_book_arg(val_p)
    val_p.add_argument("--output-dir", help="Override output directory")
    val_p.add_argument("--json-report", nargs="?", const=True, default=None)

    return parser


def _add_book_arg(parser):
    parser.add_argument("book", help="Book number, keyword, or path")


def _add_build_args(parser):
    """Add format flags and build options to a parser."""
    fmt = parser.add_argument_group("output formats")
    fmt.add_argument("--epub", action="store_true", help="Build EPUB")
    fmt.add_argument("--docx", action="store_true", help="Build DOCX")
    fmt.add_argument("--md", action="store_true", help="Build merged Markdown")
    fmt.add_argument("--pdf", action="store_true", help="Build PDF (requires xelatex)")
    fmt.add_argument("--all", action="store_true", help="Build epub + docx + md")

    opts = parser.add_argument_group("options")
    opts.add_argument(
        "--ms-only", action="store_true", help="Chapters only, no front/back matter"
    )
    opts.add_argument("--output-dir", help="Override output directory")
    opts.add_argument("--verbose", "-v", action="store_true")
    opts.add_argument(
        "--no-validate", action="store_true", help="Skip epubcheck after epub build"
    )
    opts.add_argument(
        "--json-report",
        nargs="?",
        const=True,
        default=None,
        help="Save epubcheck JSON report",
    )
    opts.add_argument(
        "--keep-tex",
        action="store_true",
        help="Keep intermediate .tex/.log for PDF debugging",
    )


# ── Main ───────────────────────────────────────────────────────────────


def main():
    parser = build_parser()

    # Allow bare "build.py trench --epub" without the "build" subcommand:
    # If the first positional arg isn't a known subcommand, prepend "build"
    # so argparse sees it as "build trench --epub".
    known_commands = {"build", "lint", "validate"}
    if (
        len(sys.argv) > 1
        and sys.argv[1] not in known_commands
        and not sys.argv[1].startswith("-")
    ):
        args = parser.parse_args(["build"] + sys.argv[1:])
    else:
        args = parser.parse_args()

    dispatch = {
        "build": cmd_build,
        "lint": cmd_lint,
        "validate": cmd_validate,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except Exception as e:
        log_path = "build_error.log"
        with open(log_path, "w") as f:
            traceback.print_exc(file=f)
        print(f"\nUnexpected error: {e}")
        print(f"Full traceback written to {log_path}")
        sys.exit(1)
