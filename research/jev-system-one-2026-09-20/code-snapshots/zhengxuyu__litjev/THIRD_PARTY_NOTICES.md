# Third-party code and assets

## jevlike examples

- Upstream: https://github.com/vinnylarouge/jevlike
- Pinned source: `94f5fd1b0b11d52bbdfdf4e0ee6aa96b568f8452`
- Original copyright: Copyright (c) 2026 Minimal Labs
- License: MIT, reproduced in [THIRD_PARTY_LICENSES/jevlike-MIT.txt](THIRD_PARTY_LICENSES/jevlike-MIT.txt)

Ported/adapted files:

| Upstream | LitJev | Changes |
| --- | --- | --- |
| `examples/chess/keys.py` | `src/litjev/games/chess/controller.py` | Relative imports; remove standalone test entry point |
| `examples/chess/render.py` | `src/litjev/games/chess/rendering.py` | Keep pixel rendering; remove training observation/standalone helpers |
| `examples/doom/environment.py` | `src/litjev/games/doom.py` | Gymnasium lifecycle; RGB-only observation; remove training helpers |
| `examples/film/build-film.mjs` | `src/litjev/games/film.py` | Port self-contained trace embedding to Python and new trace schema |
| `examples/film/film.html` | `src/litjev/static/film.html` | Redesign for actual Qwen logits, probabilities and timing, not option-head activations |
| `examples/film/render-film.mjs` | `examples/film/render-film.mjs` | Explicit input/output, wait for image decode, bounded capture and cleanup |

The adapted MIT files retain their upstream notices. Original LitJev integration
code is Apache-2.0. Both licenses are included in built distributions. Upstream
weights, datasets, training scripts, architecture SVG, and soundtrack are **not**
included. No upstream results are presented as LitJev results.

## Runtime dependencies

Dependencies retain their own licenses, including the chess rules library, ViZDoom
and its scenario assets, Gymnasium, Pillow, Playwright, and FFmpeg. They are installed
separately, not relicensed as Apache-2.0 by this repository. In particular, review
the chess library's GPL terms and the terms of any Doom WADs/engine or FFmpeg build
you redistribute. Use the scenarios supplied by your ViZDoom installation; this
repository does not redistribute commercial Doom assets.
