# Eval summary: `pilot`

38 cases (11 labelled contestable, 13 labelled valid, 2 moratorium edge). Same prompt, renderer, parser and temperature 0 for every model.

| Metric | Base Qwen3.5-4B |
| --- | ---: |
| Valid JSON rate | 100.0% (38/38) |
| Category accuracy | 94.7% (36/38) |
| Verdict accuracy | 47.4% (18/38) |
| **Contestable recall** (catches fightable claims) | 27.3% (3/11) |
| **Over-optimism rate** (not contestable, called contestable; lower is better) | 25.9% (7/27) |
| False hope rate (valid, called contestable; lower is better) | 0.0% (0/13) |
| Moratorium edge accuracy | 100.0% (2/2) |
| Fact accuracy | 87.2% (224/257) |
