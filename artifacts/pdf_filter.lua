-- pdf_filter.lua
--
-- Pandoc Lua filter for PDF builds.
-- Transforms markdown constructs into LaTeX-friendly equivalents.
--
-- Applied automatically when building PDF via the pipeline.

-- Scene breaks: *** becomes \scenebreak{}
-- (The actual substitution happens post-pandoc via regex in the
-- build script, but this filter handles edge cases where pandoc
-- doesn't produce the expected horizontal rule.)

-- Fenced divs: transform custom div classes into LaTeX environments
-- Add your own div classes here as needed.

function Div(el)
  -- .letter → italicized block with left rule
  if el.classes:includes("letter") then
    local blocks = el.content
    table.insert(blocks, 1, pandoc.RawBlock("latex", "\\begin{quote}\\itshape"))
    table.insert(blocks, pandoc.RawBlock("latex", "\\end{quote}"))
    return blocks
  end

  -- .epigraph → epigraph formatting
  if el.classes:includes("epigraph") then
    local blocks = el.content
    table.insert(blocks, 1, pandoc.RawBlock("latex", "\\begin{quote}"))
    table.insert(blocks, pandoc.RawBlock("latex", "\\end{quote}"))
    return blocks
  end

  -- Add more div classes here:
  -- if el.classes:includes("yourclass") then ... end
end

-- Ensure images have proper sizing
function Image(el)
  -- Limit image width to text width
  if not el.attributes.width then
    el.attributes.width = "\\textwidth"
  end
  return el
end
