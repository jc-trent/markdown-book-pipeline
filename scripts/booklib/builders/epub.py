"""
EPUB builder.

Pipeline: pandoc → epub → postprocess (accessibility) → epubcheck validation.
"""

from booklib.builders.base import BaseBuilder
from booklib.postprocess import patch_epub
from booklib.epubcheck import validate_epub


class EpubBuilder(BaseBuilder):
    format_name = "EPUB"
    extension = ".epub"

    def build(self):
        self.header()

        epub = self.config.epub
        skip_validate = self.kwargs.get("no_validate", False)
        json_report = self.kwargs.get("json_report", None)

        # ── Pandoc command ─────────────────────────────────
        extra = [
            "--epub-title-page=false",
            "-o",
            self.output_file,
        ]

        # TOC
        if epub.get("toc", True):
            extra.append("--toc")
            extra.extend(["--toc-depth", str(epub.get("toc_depth", 1))])

        # CSS (shared artifact)
        css_path = self.resolve(epub.get("css"))
        if css_path:
            extra.extend(["--css", css_path])
            self.log(f"  CSS:   {css_path}")
        else:
            print("  Warning: No epub CSS found")

        # Cover (per-book artifact)
        cover_path = self.resolve(epub.get("cover"))
        if cover_path:
            extra.extend(["--epub-cover-image", cover_path])
            self.log(f"  Cover: {cover_path}")
        else:
            print("  Warning: No cover image found")

        # Build pandoc command
        cmd = self.run_pandoc(extra)
        cmd.extend(self.input_files)

        self.log(f"  Input: {len(self.input_files)} files")

        if not self.exec_cmd(cmd, "EPUB generation"):
            return False

        print(f"  ✓ {self.output_file}")

        # ── Post-process for accessibility ─────────────────
        self.log("  Running epub post-processor...")
        try:
            if patch_epub(self.output_file, self.config, verbose=self.verbose):
                self.log("  ✓ Post-processing complete")
        except Exception as e:
            print(f"  Warning: Post-processing failed: {e}")
            print("  (epub was generated but may have compliance issues)")

        # ── Validate ───────────────────────────────────────
        if not skip_validate:
            validate_epub(
                self.output_file,
                verbose=self.verbose,
                json_report=json_report,
            )

        return True
