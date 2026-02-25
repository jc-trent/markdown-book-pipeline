"""
DOCX builder.

Pipeline: pandoc → docx using a reference document for styling.
The reference.docx is per-book (since headers contain the book title).
"""

from booklib.builders.base import BaseBuilder


class DocxBuilder(BaseBuilder):
    format_name = "DOCX"
    extension = ".docx"

    def build(self):
        self.header()

        docx = self.config.docx

        extra = ["-o", self.output_file]

        # TOC
        if docx.get("toc", True):
            extra.append("--toc")
            extra.extend(["--toc-depth", str(docx.get("toc_depth", 1))])

        # Reference document (per-book: controls fonts, margins, headers)
        ref_path = self.resolve(docx.get("reference"))
        if ref_path:
            extra.append(f"--reference-doc={ref_path}")
            self.log(f"  Reference: {ref_path}")

        # Build command
        cmd = self.run_pandoc(extra)
        cmd.extend(self.input_files)

        self.log(f"  Input: {len(self.input_files)} files")

        if not self.exec_cmd(cmd, "DOCX generation"):
            return False

        print(f"  ✓ {self.output_file}")
        return True
