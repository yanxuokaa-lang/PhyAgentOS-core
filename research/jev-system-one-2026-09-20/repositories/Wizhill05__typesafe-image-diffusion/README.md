# typesafe-image-diffusion

A diffusion style image model built out of a general classifier that was never meant to draw.

## The trick

Jev (via TypeSafe System One) is a judgment model. You give it state, ask multiple choice questions, and it picks answers with confidence scores. It classifies things. It does not draw things.

This experiment asks 256 parallel `Choice` questions, one per pixel on a 16x16 grid. Each pixel is told its row, column, and distance from the center, plus the prompt, and asked which of 16 palette colors it should be. Stitch the 256 answers together and you get pixel art. No diffusion weights, no training, just 256 tiny classifier decisions in a trench coat pretending to be an image model.

Refinement passes make it act a bit more like real diffusion. Each pixel is asked again, this time seeing its previous color and its 3x3 neighborhood, and it can stay or change to clean up holes and edges. The UI has a slider (0 to 5) for how many refinement rounds to run, and it animates each pass.

One lesson from building this: the first refinement design sent every pixel the full grid, and Jev answered with `400 max_tokens_exceeded`. Pass 0 alone uses around 57k input tokens. Slimming each pixel down to its local neighborhood (around 39k tokens) fixed it, and the results got better too.

## Best results

These were the best results I could get out of the model:

![A sunny beach with blue sky](best_beach.jpg)
![A lake in the middle of the green forest](best_lake.jpg)
![A rainbow gradient from left to right](best_rainbow.jpg)
![Colours of the Indian flag](best_flag.jpg)

## Run it

```bash
export TYPESAFE_API_KEY="your-key-here"
./start_server.sh
```

Open http://127.0.0.1:8000, type a prompt, move the slider, hit Generate. Or call the API:

```bash
curl -X POST http://127.0.0.1:8000/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"A red circle on a white background","refinement_passes":2}'
```

The response has `grid` (final image), `history` (every pass, for the animation), and `usage` (tokens, which grow with each pass since every refine is another 256 question call).

Built with TypeSafe System One (`jev-latest`) and FastAPI.
