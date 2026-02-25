"""
Markdown builder.

Produces a single merged markdown file with formatting artifacts stripped.
Useful for word counts, sharing with editors, or feeding into other tools.
"""

from booklib.builders.base import BaseBuilder


class MarkdownBuilder(BaseBuilder):
    format_name = "Markdown"
    extension = ".md"

    def build(self):
        self.header()

        extra = [
            "--standalone",
            "--wrap=none",
            "--to", "markdown",
            "-o", self.output_file,
        ]

        # Strip formatting filter (removes epub/pdf scaffolding)
        strip_filter = self.resolve("strip_formatting.lua")
        if strip_filter:
            extra.extend(["--lua-filter", strip_filter])
            self.log(f"  Filter: strip_formatting.lua")

        cmd = self.run_pandoc(extra)
        cmd.extend(self.input_files)

        self.log(f"  Input: {len(self.input_files)} files")

        if not self.exec_cmd(cmd, "Markdown merge"):
            return False

        print(f"  ✓ {self.output_file}")
        return True
