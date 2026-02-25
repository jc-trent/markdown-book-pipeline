"""
Book configuration: load, validate, and provide defaults for book.yaml.
"""

import os
import sys

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


# Fields required in every book.yaml
REQUIRED_FIELDS = ["title", "author", "prefix"]

# Defaults applied if missing
DEFAULTS = {
    "lang": "en-US",
    "date": "",
    "markdown_extensions": "fenced_divs+native_divs",
    "filters": [],
    "epub": {},
    "docx": {},
    "pdf": {},
}

# Defaults within format sub-configs
EPUB_DEFAULTS = {
    "toc": True,
    "toc_depth": 1,
    "css": "epub.css",
    "cover": "cover.jpg",
}

DOCX_DEFAULTS = {
    "toc": True,
    "toc_depth": 1,
    "reference": "reference.docx",
}

PDF_DEFAULTS = {
    "template": "book.tex",
    "filter": "pdf_filter.lua",
    "engine": "xelatex",
    "scene_break_macro": r"\scenebreak{}",
    "job_suffix": "_print_6x9",
}


class ConfigError(Exception):
    """Raised when book.yaml is missing or invalid."""
    pass


class BookConfig:
    """
    Loaded, validated book configuration.

    Usage:
        config = BookConfig.load(book_dir)
        config.title          # "The Trench Mage"
        config.epub["css"]    # "epub.css"
        config.get("series")  # None if not set
    """

    def __init__(self, data, book_dir):
        self._data = data
        self.book_dir = book_dir

    @classmethod
    def load(cls, book_dir):
        """Load and validate book.yaml from a book directory."""
        yaml_path = os.path.join(book_dir, "book.yaml")
        if not os.path.exists(yaml_path):
            raise ConfigError(f"No book.yaml found in {book_dir}")

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ConfigError(f"book.yaml must be a YAML mapping, got {type(data).__name__}")

        # Validate required fields
        missing = [key for key in REQUIRED_FIELDS if not data.get(key)]
        if missing:
            raise ConfigError(
                f"book.yaml missing required fields: {', '.join(missing)}"
            )

        # Apply top-level defaults
        for key, default in DEFAULTS.items():
            data.setdefault(key, default if not isinstance(default, (list, dict)) else type(default)(default))

        # Apply format-section defaults
        for key, default in EPUB_DEFAULTS.items():
            data["epub"].setdefault(key, default)
        for key, default in DOCX_DEFAULTS.items():
            data["docx"].setdefault(key, default)
        for key, default in PDF_DEFAULTS.items():
            data["pdf"].setdefault(key, default)

        return cls(data, book_dir)

    # ── Attribute access ───────────────────────────────────

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"BookConfig has no field '{name}'")

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    # ── Convenience ────────────────────────────────────────

    @property
    def from_str(self):
        """The pandoc --from string including extensions."""
        return f"markdown+smart+{self.markdown_extensions}"

    def metadata_args(self):
        """Build pandoc --metadata arguments list."""
        args = []
        for key in ["title", "author", "lang", "date"]:
            value = self.get(key)
            if value:
                args.extend(["--metadata", f"{key}={value}"])
        return args

    def summary(self):
        """Print a short config summary."""
        print(f"\n  Book:   {self.title}")
        print(f"  Author: {self.author}")
        print(f"  Source: {self.book_dir}")
        if self.get("series"):
            print(f"  Series: {self.series}")
