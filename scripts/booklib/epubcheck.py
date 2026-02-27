"""
EPUB validation via epubcheck.

Locates epubcheck (env var, PATH, tools/ dir, or ~/),
runs it, and parses the output summary.
"""

import os
import re
import shutil
import subprocess


def find_epubcheck():
    """
    Locate epubcheck. Checks in order:
        1. EPUBCHECK_JAR environment variable
        2. epubcheck command on PATH (brew/apt install)
        3. tools/epubcheck*/epubcheck.jar (relative to project root)
        4. ~/epubcheck*/epubcheck.jar

    Returns: (mode, path) where mode is 'jar' or 'cmd', or (None, None).
    """
    # 1. Environment variable
    env_jar = os.environ.get("EPUBCHECK_JAR")
    if env_jar and os.path.exists(env_jar):
        return ("jar", env_jar)

    # 2. System install
    if shutil.which("epubcheck"):
        return ("cmd", "epubcheck")

    # 3. tools/ directory relative to this package, or home directory
    package_dir = os.path.dirname(os.path.abspath(__file__))
    # Walk up to find project root (scripts/booklib/ → scripts/ → project root)
    project_root = os.path.dirname(os.path.dirname(package_dir))

    for search_root in [
        os.path.join(project_root, "tools"),
        os.path.join(project_root, "scripts", "tools"),
        os.path.expanduser("~"),
    ]:
        if os.path.isdir(search_root):
            for entry in sorted(os.listdir(search_root), reverse=True):
                if entry.startswith("epubcheck"):
                    jar = os.path.join(search_root, entry, "epubcheck.jar")
                    if os.path.exists(jar):
                        return ("jar", jar)

    return (None, None)


def validate_epub(epub_path, verbose=False, json_report=None):
    """
    Run epubcheck on an epub file.

    Args:
        epub_path:   Path to the .epub file
        verbose:     Show individual issues
        json_report: Path for JSON report, or True for auto-naming

    Returns:
        True if valid, False if errors, None if epubcheck unavailable.
    """
    mode, path = find_epubcheck()

    if mode is None:
        if verbose:
            print("  Skipping validation: epubcheck not found")
            print("  Install: brew install epubcheck")
            print("     or:   bash scripts/setup_epubcheck.sh")
        return None

    cmd = ["java", "-jar", path, epub_path] if mode == "jar" else [path, epub_path]

    if json_report:
        if json_report is True:
            json_report = epub_path.rsplit(".", 1)[0] + "_epubcheck.json"
        cmd.extend(["--json", json_report])

    if verbose:
        print("  Validating with epubcheck...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr

        summary = re.search(
            r"Messages:\s*(\d+)\s*fatal.*?(\d+)\s*error.*?(\d+)\s*warn",
            output,
        )

        if summary:
            fatals = int(summary.group(1))
            errors = int(summary.group(2))
            warnings = int(summary.group(3))

            if fatals == 0 and errors == 0 and warnings == 0:
                print("  ✓ epubcheck: valid (no errors, no warnings)")
            elif fatals == 0 and errors == 0:
                print(f"  ⚠ epubcheck: valid with {warnings} warning(s)")
            else:
                print(
                    f"  ✗ epubcheck: {fatals} fatal, {errors} error(s), {warnings} warning(s)"
                )
        elif result.returncode == 0:
            print("  ✓ epubcheck: valid")
        else:
            print(f"  ✗ epubcheck: failed (exit code {result.returncode})")

        if verbose or result.returncode != 0:
            for line in output.splitlines():
                if any(line.startswith(s) for s in ["ERROR", "WARNING", "FATAL"]):
                    print(f"    {line}")

        if json_report and os.path.exists(json_report):
            print(f"  Report: {json_report}")

        return result.returncode == 0

    except FileNotFoundError:
        print("  Warning: Could not run epubcheck (java not found?)")
        return None
    except Exception as e:
        if verbose:
            print(f"  Warning: epubcheck failed: {e}")
        return None
