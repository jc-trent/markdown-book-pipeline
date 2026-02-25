Per-book artifacts go here. These override the shared artifacts/ at the repo root.

Required:
  - cover.jpg    — EPUB/ebook cover image (2560×1600px minimum for Amazon KDP)

Optional:
  - reference.docx — DOCX styling reference document. To create one:
    1. Build a DOCX: python scripts/build.py example --docx
    2. Open the output DOCX in Word
    3. Modify the styles (fonts, spacing, headers)
    4. Save it here as reference.docx
    5. Future DOCX builds will use these styles

  Any file here with the same name as a shared artifact will take priority.
  For example, a custom epub.css here overrides the shared one for this book only.
