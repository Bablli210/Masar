# Masar logo morph

`masar-logo-morph.mp4` (1920×1080, 30 fps, 13 s, H.264 + AAC). The GET ED and Eshra7ly logos dissolve into particles that form the bilingual Masar lockup. GET ED cyan builds the م‑س of مسار, Eshra7ly navy and orange build the alef and the ر, and "Masar" builds from both. A blue path then draws beneath the lockup, followed by the tagline in English and Arabic.

- `make_morph.py` renders every frame (numpy + Pillow), writes the original ambient soundtrack (pad, whoosh, landing sparkles, arrival chime), and muxes them with ffmpeg. It needs `pip install numpy pillow imageio-ffmpeg`.
  - `python3 video/make_morph.py` writes the MP4 and a poster frame.
  - `python3 video/make_morph.py --preview` writes a few stills to `video/preview/`.
- Logos come from `site/assets/`. `fonts/` holds Montserrat and Alexandria, both under the SIL Open Font License.
- `masar-logo-morph-poster.png` is the end frame.
