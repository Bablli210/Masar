# Masar pitch site

A single-page, scroll-animated pitch for universities. It uses the copy from the GET ED × Eshra7ly proposal and follows `docs/style-guide.md`.

- `index.html` holds all the CSS and JS inline. There are no build steps and no dependencies apart from Google Fonts (Montserrat, Alexandria).
- The file has no `<!doctype>` or `<html>` wrapper, because the artifact host adds those. To view it locally, wrap it first:
  `(printf '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'; cat index.html) > _preview.html`
- `assets/` holds white GET ED, Eshra7ly and Masar logos (from the proposal PDF), shown on coloured tiles set by `--c-masar`, `--c-geted` and `--c-eshra7ly`. All pictures are inline SVG illustrations in the ink + oat style.

Motion: the blue chapter rail draws as you scroll, the illustrations sketch themselves in and have a hand-drawn "line boil", headline lines rise into view, and the foreword lights up word by word. Numbers count up, and the charts grow in. The four formats scroll sideways in a pinned section, and there's a "Do the maths" package planner. All motion turns off under `prefers-reduced-motion`.
