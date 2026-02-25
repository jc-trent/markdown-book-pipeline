from booklib.builders.epub import EpubBuilder
from booklib.builders.docx import DocxBuilder
from booklib.builders.markdown import MarkdownBuilder
from booklib.builders.pdf import PdfBuilder

BUILDERS = {
    "epub": EpubBuilder,
    "docx": DocxBuilder,
    "md": MarkdownBuilder,
    "pdf": PdfBuilder,
}

# --all builds these (PDF excluded — requires xelatex, opt-in with --pdf)
DEFAULT_FORMATS = ["epub", "docx", "md"]
