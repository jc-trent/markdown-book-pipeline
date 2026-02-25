-- strip_formatting.lua
--
-- Pandoc Lua filter for clean merged markdown output.
-- Removes formatting artifacts that don't belong in a plain
-- markdown merge (fenced div markers, heading attributes, etc).

-- Remove fenced div wrappers, keep content
function Div(el)
  return el.content
end

-- Strip heading attributes (like {.unnumbered .unlisted})
function Header(el)
  el.attributes = {}
  el.classes = {}
  return el
end
