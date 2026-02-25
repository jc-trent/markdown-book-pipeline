"""
Manuscript linter.

Scans markdown source for encoding issues, typography problems,
structural errors, and pandoc-specific formatting concerns.

Can be invoked from the unified build.py CLI or standalone.
"""

import os
import re
import sys

from booklib.resolve import section_for_path


# ── Lint Patterns ──────────────────────────────────────────────────────
#
# Each: (description, compiled regex, replacement, severity)
#   replacement = None → report only (manual review)
#   replacement = str  → auto-fixable with --fix
#   severity: "error" | "warning" | "info"

ENCODING_PATTERNS = [
    ("Single-character ellipsis (use '...' instead)",
     re.compile(r"\u2026"), "...", "warning"),
    ("Unicode en-dash (use '--' instead)",
     re.compile(r"\u2013"), "--", "warning"),
    ("Unicode em-dash (use '---' instead)",
     re.compile(r"\u2014"), "---", "warning"),
    ("Curly double quote (use straight quotes)",
     re.compile(r"[\u201C\u201D]"), '"', "warning"),
    ("Curly single quote/apostrophe (use straight quotes)",
     re.compile(r"[\u2018\u2019]"), "'", "warning"),
    ("Non-breaking space",
     re.compile(r"\u00A0"), " ", "error"),
    ("Zero-width space/joiner",
     re.compile(r"[\u200B-\u200D\uFEFF]"), "", "error"),
    ("Soft hyphen",
     re.compile(r"\u00AD"), "", "error"),
    ("Directional mark (LTR/RTL)",
     re.compile(r"[\u200E\u200F]"), "", "error"),
]

WHITESPACE_PATTERNS = [
    ("Tab character (use spaces)",
     re.compile(r"\t"), "    ", "warning"),
    ("Multiple spaces (not in indent)",
     re.compile(r"(?<=\S)  +"), " ", "warning"),
    ("Trailing whitespace",
     re.compile(r" +$", re.MULTILINE), "", "warning"),
    ("Carriage return (Windows line ending)",
     re.compile(r"\r"), "", "error"),
    ("Three or more consecutive blank lines",
     re.compile(r"\n{4,}"), "\n\n\n", "warning"),
]

PUNCTUATION_PATTERNS = [
    ("Multiple exclamation marks",
     re.compile(r"!!+"), None, "info"),
    ("Multiple question marks",
     re.compile(r"\?\?+"), None, "info"),
    ("Repeated comma",
     re.compile(r",,+"), None, "warning"),
    ("Four+ dots (check if intentional)",
     re.compile(r"\.{4,}"), None, "info"),
    ("Space before punctuation",
     re.compile(r"(?<=\w) +(?=[,;:!?](?:\s|$))"), None, "info"),
]

STRUCTURE_PATTERNS = [
    ("Scene break using --- (use *** instead)",
     re.compile(r"^\n---\n", re.MULTILINE), "\n***\n", "warning"),
    ("Scene break missing blank line before",
     re.compile(r"([^\n])\n\*\*\*\n"), None, "error"),
    ("Scene break missing blank line after",
     re.compile(r"\n\*\*\*\n([^\n])"), None, "error"),
    ("Missing space after heading hash",
     re.compile(r"^(#{1,6})[^ #\n{]", re.MULTILINE), None, "error"),
    ("Trailing hash on heading",
     re.compile(r"^(#{1,6})\s+.+\s+#+\s*$", re.MULTILINE), None, "warning"),
    ("Fenced div missing space after :::",
     re.compile(r"^:::\{", re.MULTILINE), "::: {", "error"),
    ("Raw LaTeX block (won't render in epub/docx)",
     re.compile(r"```\{=latex\}"), None, "error"),
]

ALL_PATTERNS = ENCODING_PATTERNS + WHITESPACE_PATTERNS + PUNCTUATION_PATTERNS + STRUCTURE_PATTERNS


# ── Severity display ───────────────────────────────────────────────────

SEVERITY_COLOR = {
    "error":   "\033[31m✗\033[0m",
    "warning": "\033[33m!\033[0m",
    "info":    "\033[36m·\033[0m",
}

SEVERITY_PLAIN = {
    "error":   "[ERROR]",
    "warning": "[WARN]",
    "info":    "[INFO]",
}


# ── Linter class ───────────────────────────────────────────────────────


class Linter:
    """
    Manuscript linter.

    Usage:
        linter = Linter(book_dir, files, fix=False, color=True)
        success = linter.run()
    """

    def __init__(self, book_dir, files, fix=False, verbose=False, color=True):
        self.book_dir = book_dir
        self.files = files
        self.fix = fix
        self.verbose = verbose
        self.symbols = SEVERITY_COLOR if color else SEVERITY_PLAIN
        self.total_counts = {"error": 0, "warning": 0, "info": 0}
        self.total_fixes = 0
        self.files_with_issues = 0

    def run(self):
        """Lint all files. Returns True if no errors found."""
        for filepath in self.files:
            section = section_for_path(filepath, self.book_dir)
            rel_path = os.path.relpath(filepath, self.book_dir)

            findings, fixes, counts = self._lint_file(filepath, section)
            self.total_fixes += fixes

            for sev in self.total_counts:
                self.total_counts[sev] += counts[sev]

            if findings:
                self.files_with_issues += 1
                print(f"  {rel_path}")
                for f in findings:
                    print(f)
                print()
            elif self.verbose:
                print(f"  {rel_path} — clean")

        self._summary()
        return self.total_counts["error"] == 0

    def _lint_file(self, filepath, section):
        """Scan a single file. Returns (findings, fix_count, severity_counts)."""
        findings = []
        fixes_applied = 0
        counts = {"error": 0, "warning": 0, "info": 0}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            original = content
        except UnicodeDecodeError:
            return (
                [f"  {self.symbols['error']} Cannot read (encoding error)"],
                0,
                {"error": 1, "warning": 0, "info": 0},
            )

        # ── Regex patterns ─────────────────────────────────
        for description, pattern, replacement, severity in ALL_PATTERNS:
            matches = list(pattern.finditer(content))
            if not matches:
                continue

            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                counts[severity] += 1

                matched = match.group(0)
                display = (
                    repr(matched)
                    if len(matched) <= 1 and ord(matched[0]) > 127
                    else f"'{matched[:30]}'"
                )

                if replacement is not None and self.fix:
                    findings.append(
                        f"  {self.symbols[severity]} :{line_num} Fixed: {description}"
                    )
                else:
                    label = "Found" if replacement is None else "Fixable"
                    findings.append(
                        f"  {self.symbols[severity]} :{line_num} {label}: {description} ({display})"
                    )

            if self.fix and replacement is not None:
                new = pattern.sub(replacement, content)
                if new != content:
                    fixes_applied += len(matches)
                    content = new

        # ── Structural checks ──────────────────────────────
        for sfindings in self._check_structure(filepath, content, section):
            _, line_num, severity, message = sfindings
            counts[severity] += 1
            ref = f":{line_num}" if line_num > 0 else ""
            findings.append(f"  {self.symbols[severity]} {ref} {message}")

        # ── Write back ─────────────────────────────────────
        if self.fix and content != original:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        return findings, fixes_applied, counts

    def _check_structure(self, filepath, content, section):
        """Structural checks beyond regex."""
        findings = []
        lines = content.split("\n")

        # Chapter files should start with a heading
        if section == "chapters":
            for line in lines:
                if line.strip():
                    if not line.strip().startswith("#"):
                        findings.append((
                            filepath, 1, "error",
                            f"Chapter file does not start with a heading: '{line.strip()[:40]}...'"
                        ))
                    break

        # Front matter headings need .unnumbered .unlisted
        if section == "front":
            for i, line in enumerate(lines, 1):
                if line.startswith("# ") and ".unnumbered" not in line:
                    findings.append((
                        filepath, i, "warning",
                        "Front matter heading missing {.unnumbered .unlisted}"
                    ))
                    break

        # Unclosed fenced divs
        div_count = content.count("\n:::")
        if content.startswith(":::"):
            div_count += 1
        if div_count % 2 != 0:
            findings.append((
                filepath, 0, "error",
                f"Possibly unclosed fenced div ({div_count} ':::' markers, expected even)"
            ))

        # BOM
        if content.startswith("\ufeff"):
            findings.append((filepath, 1, "error", "File starts with UTF-8 BOM"))

        # Trailing newline
        if content and not content.endswith("\n"):
            findings.append((
                filepath, len(lines), "warning",
                "File does not end with a newline"
            ))

        return findings

    def _summary(self):
        """Print the summary line."""
        total = sum(self.total_counts.values())

        print(f"{'─' * 50}")

        if total == 0:
            print(f"  No issues found across {len(self.files)} files.")
            return

        parts = []
        if self.total_counts["error"]:
            parts.append(f"{self.total_counts['error']} errors")
        if self.total_counts["warning"]:
            parts.append(f"{self.total_counts['warning']} warnings")
        if self.total_counts["info"]:
            parts.append(f"{self.total_counts['info']} info")

        print(f"  {', '.join(parts)} across {self.files_with_issues}/{len(self.files)} files")

        if self.fix:
            print(f"  Applied {self.total_fixes} fixes")
            remaining = total - self.total_fixes
            if remaining > 0:
                print(f"  {remaining} issues require manual review")

        if not self.fix and (self.total_counts["error"] or self.total_counts["warning"]):
            print(f"  Run with --fix to auto-correct fixable issues")
