"""
Book resolution, file assembly, and artifact lookup.

Every script that needs to find a book directory, gather its markdown
files, or locate shared/per-book artifacts imports from here.
"""

import os
import re
import glob

try:
    import yaml
except ImportError:
    yaml = None


def natural_sort_key(s):
    """Sort strings with embedded numbers naturally (2.md before 10.md)."""
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", s)
    ]


def find_book_dir(identifier, project_root):
    """
    Resolve a book identifier to its manuscript directory.

    Accepts:
        - Direct path:  manuscript/1_the_trench_mage
        - Number:       1         (matches "1_..." prefix)
        - Keyword:      trench    (matches dir name or YAML title)

    Returns: absolute path to the book directory, or None.
    """
    manuscript_root = os.path.join(project_root, "manuscript")

    # Direct path (absolute or relative)
    for candidate in [identifier, os.path.join(project_root, identifier)]:
        if os.path.isdir(candidate) and os.path.exists(
            os.path.join(candidate, "book.yaml")
        ):
            return os.path.abspath(candidate)

    if not os.path.isdir(manuscript_root):
        return None

    identifier_lower = identifier.lower()

    for entry in sorted(os.listdir(manuscript_root)):
        book_path = os.path.join(manuscript_root, entry)
        if not os.path.isdir(book_path):
            continue

        # Match by number prefix: "1" matches "1_the_trench_mage"
        match = re.match(r"^(\d+)_", entry)
        if match and match.group(1) == identifier:
            return book_path

        # Match by keyword in directory name
        if identifier_lower in entry.lower():
            return book_path

        # Match by keyword in YAML title
        if yaml:
            yaml_path = os.path.join(book_path, "book.yaml")
            if os.path.exists(yaml_path):
                try:
                    with open(yaml_path) as f:
                        cfg = yaml.safe_load(f)
                    if identifier_lower in cfg.get("title", "").lower():
                        return book_path
                except Exception:
                    pass

    return None


def get_section_files(book_dir, section):
    """Get sorted markdown files from a section subdirectory."""
    section_dir = os.path.join(book_dir, section)
    if not os.path.isdir(section_dir):
        return []
    files = glob.glob(os.path.join(section_dir, "*.md"))
    files.sort(key=natural_sort_key)
    return files


def assemble_inputs(book_dir, manuscript_only=False):
    """
    Assemble input files in section order: front → chapters → back.

    If manuscript_only, only chapters/ are included (for editor submissions).
    Falls back to *.md in book root if no subdirectories exist.
    """
    if manuscript_only:
        files = get_section_files(book_dir, "chapters")
    else:
        files = (
            get_section_files(book_dir, "front")
            + get_section_files(book_dir, "chapters")
            + get_section_files(book_dir, "back")
        )

    # Fallback: flat layout
    if not files:
        files = glob.glob(os.path.join(book_dir, "*.md"))
        files.sort(key=natural_sort_key)

    return files


def resolve_artifact(book_dir, filename):
    """
    Resolve an artifact filename to its full path.

    Search order (first match wins):
        1. book artifacts/    (per-book overrides, e.g. cover.jpg, reference.docx)
        2. repo artifacts/    (shared across all books, e.g. epub.css, book.tex)
        3. scripts/           (legacy fallback)

    Returns: absolute path or None.
    """
    if not filename:
        return None

    # 1. Per-book artifacts/
    path = os.path.join(book_dir, "artifacts", filename)
    if os.path.exists(path):
        return os.path.abspath(path)

    # 2. Repo-level artifacts/ (up from manuscript/<book>)
    repo_root = os.path.dirname(os.path.dirname(book_dir))
    path = os.path.join(repo_root, "artifacts", filename)
    if os.path.exists(path):
        return os.path.abspath(path)

    # 3. Script directory (legacy)
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(script_dir, "scripts", filename)
    if os.path.exists(path):
        return os.path.abspath(path)

    return None


def resolve_filters(book_dir, filter_names):
    """Resolve a list of Lua filter filenames to paths. Warns on missing."""
    filters = []
    for name in (filter_names or []):
        path = resolve_artifact(book_dir, name)
        if path:
            filters.append(path)
        else:
            print(f"  Warning: filter '{name}' not found in artifacts/")
    return filters


def section_for_path(filepath, book_dir):
    """Determine which section (front/chapters/back) a file belongs to."""
    rel = os.path.relpath(filepath, book_dir)
    parts = rel.split(os.sep)
    return parts[0] if len(parts) > 1 else "chapters"
