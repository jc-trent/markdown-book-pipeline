"""
Base builder class for all output formats.

Subclasses implement `build()` and set `format_name` / `extension`.
Shared logic (pandoc invocation, logging, artifact resolution) lives here.
"""

import os
import subprocess
import shutil
from abc import ABC, abstractmethod

from booklib.resolve import resolve_artifact, resolve_filters


class BaseBuilder(ABC):
    """
    Abstract base for format builders.

    Subclasses must define:
        format_name:  str   — human-readable name ("EPUB", "PDF", etc.)
        extension:    str   — output file extension (".epub", ".pdf", etc.)
        build():      method — the actual build logic
    """

    format_name = None  # Override in subclass
    extension = None    # Override in subclass

    def __init__(self, config, book_dir, input_files, output_dir, verbose=False, **kwargs):
        self.config = config
        self.book_dir = book_dir
        self.input_files = input_files
        self.output_dir = output_dir
        self.verbose = verbose
        self.kwargs = kwargs

    # ── Output path ────────────────────────────────────────

    @property
    def output_file(self):
        return os.path.join(self.output_dir, f"{self.config.prefix}{self.extension}")

    # ── Logging ────────────────────────────────────────────

    def log(self, msg):
        if self.verbose:
            print(msg)

    def header(self):
        print(f"\n{'─' * 60}")
        print(f"  Building {self.format_name}: {self.config.title}")
        print(f"{'─' * 60}")

    # ── Artifact resolution (delegates to shared module) ───

    def resolve(self, filename):
        """Resolve an artifact filename for this book."""
        return resolve_artifact(self.book_dir, filename)

    def get_filters(self):
        """Resolve Lua filters listed in config."""
        return resolve_filters(self.book_dir, self.config.get("filters"))

    # ── Pandoc invocation ──────────────────────────────────

    def run_pandoc(self, extra_args=None):
        """
        Run pandoc with standard arguments plus any extras.

        Returns True on success, False on failure.
        """
        cmd = ["pandoc"]
        cmd.extend(self.config.metadata_args())
        cmd.extend([
            "--top-level-division=chapter",
            "--from", self.config.from_str,
        ])

        if extra_args:
            cmd.extend(extra_args)

        # Lua filters from config
        for f in self.get_filters():
            cmd.extend(["--lua-filter", f])

        return cmd

    def exec_cmd(self, cmd, label="Command"):
        """Execute a command, handle errors consistently."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=not self.verbose,
                text=True,
            )
            if result.returncode != 0:
                print(f"  ✗ {label} failed (exit {result.returncode})")
                if result.stderr:
                    for line in result.stderr.strip().splitlines()[:20]:
                        print(f"    {line}")
                return False
            return True
        except FileNotFoundError:
            print(f"  ✗ {cmd[0]} not found")
            return False

    def check_tool(self, name):
        """Check that a required external tool is on PATH."""
        if not shutil.which(name):
            print(f"  ✗ {name} not found on PATH")
            return False
        return True

    # ── Abstract interface ─────────────────────────────────

    @abstractmethod
    def build(self):
        """
        Execute the build. Returns True on success, False on failure.
        """
        ...
