"""
PDF builder.

Pipeline:
    1. Pandoc converts markdown → intermediate LaTeX via book.tex template
    2. pdf_filter.lua handles divs, scene breaks, matter transitions
    3. Post-process LaTeX (regex fixups easier here than in Lua)
    4. XeLaTeX compiles to PDF (two passes for TOC/headers)
"""

import os
import re
import subprocess

from booklib.builders.base import BaseBuilder


class PdfBuilder(BaseBuilder):
    format_name = "PDF"
    extension = ".pdf"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keep_tex = kwargs.get("keep_tex", False)

    @property
    def output_file(self):
        """PDF uses a custom job name with suffix."""
        suffix = self.config.pdf.get("job_suffix", "_print_6x9")
        return os.path.join(self.output_dir, f"{self.config.prefix}{suffix}.pdf")

    @property
    def job_name(self):
        suffix = self.config.pdf.get("job_suffix", "_print_6x9")
        return f"{self.config.prefix}{suffix}"

    @property
    def intermediate_tex(self):
        return os.path.join(self.output_dir, f"{self.config.prefix}_print.tex")

    def build(self):
        self.header()

        pdf = self.config.pdf
        engine = pdf.get("engine", "xelatex")

        # ── Resolve template and filter ────────────────────
        template = self.resolve(pdf.get("template"))
        if not template:
            print(f"  ✗ Template '{pdf.get('template')}' not found in artifacts/")
            return False

        lua_filter = self.resolve(pdf.get("filter"))
        if lua_filter:
            self.log(f"  Filter: {lua_filter}")

        self.log(f"  Template: {template}")
        self.log(f"  Input:    {len(self.input_files)} files")

        # ── Check for xelatex ─────────────────────────────
        if not self.check_tool(engine):
            print("  Install TeX Live or MacTeX:")
            print("    macOS:  brew install --cask mactex")
            print("    Ubuntu: sudo apt install texlive-xetex texlive-fonts-extra")
            return False

        # ── Step 1: Pandoc → intermediate LaTeX ───────────
        self.log("  Generating LaTeX...")

        extra = [
            f"--template={template}",
            f"--pdf-engine={engine}",
            "-o",
            self.intermediate_tex,
        ]

        if self.config.get("series"):
            extra.extend(["--metadata", f"series={self.config.series}"])

        cmd = self.run_pandoc(extra)

        # Add PDF-specific lua filter (in addition to shared filters)
        if lua_filter:
            cmd.extend(["--lua-filter", lua_filter])

        cmd.extend(self.input_files)

        if not self.exec_cmd(cmd, "LaTeX generation"):
            return False

        self.log(f"  ✓ Generated {self.intermediate_tex}")

        # ── Step 2: Post-process LaTeX ────────────────────
        try:
            with open(self.intermediate_tex, "r", encoding="utf-8") as f:
                tex = f.read()

            # Fix leftover pandoc horizontal rules the filter missed
            tex = re.sub(
                r"\\begin\{center\}\\rule\{0\.5\\linewidth\}\{0\.5pt\}\\end\{center\}",
                r"\\scenebreak",
                tex,
            )

            with open(self.intermediate_tex, "w", encoding="utf-8") as f:
                f.write(tex)
        except Exception as e:
            print(f"  Warning: Post-processing failed: {e}")

        # ── Step 3: XeLaTeX (two passes) ──────────────────
        compile_cmd = [
            engine,
            "-interaction=nonstopmode",
            f"-output-directory={self.output_dir}",
            f"-jobname={self.job_name}",
            self.intermediate_tex,
        ]

        for pass_num in [1, 2]:
            self.log(f"  {engine} pass {pass_num}...")
            try:
                result = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print(f"  ✗ {engine} pass {pass_num} failed")
                    self._report_tex_errors()
                    return False
            except FileNotFoundError:
                print(f"  ✗ {engine} not found")
                return False

        print(f"  ✓ {self.output_file}")

        # ── Step 4: Cleanup / page count ──────────────────
        self._report_page_count()
        self._cleanup()

        return True

    def _report_tex_errors(self):
        """Extract useful errors from the XeLaTeX log file."""
        log_file = os.path.join(self.output_dir, f"{self.job_name}.log")
        if not os.path.exists(log_file):
            return

        with open(log_file, "r", errors="replace") as f:
            log_content = f.read()

        errors = [
            line
            for line in log_content.splitlines()
            if line.startswith("!") or "Error" in line
        ]

        if errors:
            print(f"  Errors from {self.job_name}.log:")
            for err in errors[:10]:
                print(f"    {err}")
        else:
            print(f"  Last lines of {self.job_name}.log:")
            for line in log_content.splitlines()[-20:]:
                print(f"    {line}")

    def _report_page_count(self):
        """Quick page count from the PDF structure."""
        try:
            result = subprocess.run(
                ["strings", self.output_file],
                capture_output=True,
                text=True,
            )
            counts = re.findall(r"/Count\s+(\d+)", result.stdout)
            if counts:
                pages = max(int(c) for c in counts)
                print(f"  Pages: ~{pages}")
        except Exception:
            pass

    def _cleanup(self):
        """Remove intermediate files unless --keep-tex."""
        if self.keep_tex:
            self.log(f"  Kept intermediate: {self.intermediate_tex}")
            log_file = os.path.join(self.output_dir, f"{self.job_name}.log")
            self.log(f"  Kept log: {log_file}")
            return

        for ext in [".aux", ".log", ".toc", ".out"]:
            path = os.path.join(self.output_dir, f"{self.job_name}{ext}")
            if os.path.exists(path):
                os.remove(path)
        if os.path.exists(self.intermediate_tex):
            os.remove(self.intermediate_tex)
        self.log("  Cleaned up intermediate files")
