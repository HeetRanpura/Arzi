# Eval summary: `synth`

117 cases (36 labelled contestable, 37 labelled valid, 26 moratorium edge). Same prompt, renderer, parser and temperature 0 for every model.

| Metric | Base Qwen3.5-4B | Fine-tuned |
| --- | ---: | ---: |
| Valid JSON rate | 100.0% (117/117) | 100.0% (117/117) |
| Category accuracy | 96.6% (113/117) | 99.1% (116/117) |
| Verdict accuracy | 43.6% (51/117) | 97.4% (114/117) |
| **Contestable recall** (catches fightable claims) | 36.1% (13/36) | 97.2% (35/36) |
| **Over-optimism rate** (not contestable, called contestable; lower is better) | 28.4% (23/81) | 1.2% (1/81) |
| False hope rate (valid, called contestable; lower is better) | 13.5% (5/37) | 2.7% (1/37) |
| Moratorium edge accuracy | 34.6% (9/26) | 92.3% (24/26) |
| Fact accuracy | 85.3% (675/791) | 98.7% (781/791) |
| Months-of-cover fact accuracy | 12.0% (14/117) | 95.7% (112/117) |

## Verdict confusion matrix: Base Qwen3.5-4B

| gold \ predicted | likely_contestable | worth_asking | likely_valid | unparsed |
| --- | ---: | ---: | ---: | ---: |
| **likely_contestable** | 13 | 1 | 22 | 0 |
| **worth_asking** | 18 | 6 | 20 | 0 |
| **likely_valid** | 5 | 0 | 32 | 0 |

## Verdict confusion matrix: Fine-tuned

| gold \ predicted | likely_contestable | worth_asking | likely_valid | unparsed |
| --- | ---: | ---: | ---: | ---: |
| **likely_contestable** | 35 | 0 | 1 | 0 |
| **worth_asking** | 0 | 43 | 1 | 0 |
| **likely_valid** | 1 | 0 | 36 | 0 |

## Verdict accuracy by category

| Category | Base Qwen3.5-4B | Fine-tuned |
| --- | ---: | ---: |
| documents_or_late_intimation | 25.0% (3/12) | 100.0% (12/12) |
| no_hospitalisation_needed | 30.0% (3/10) | 100.0% (10/10) |
| non_disclosure_ped | 39.3% (11/28) | 92.9% (26/28) |
| other | 0.0% (0/6) | 100.0% (6/6) |
| permanent_exclusion | 50.0% (6/12) | 100.0% (12/12) |
| policy_lapsed | 57.1% (4/7) | 85.7% (6/7) |
| room_rent_proportionate | 18.2% (2/11) | 100.0% (11/11) |
| sum_insured_exhausted | 85.7% (6/7) | 100.0% (7/7) |
| waiting_period | 66.7% (16/24) | 100.0% (24/24) |

## Cases where base and fine-tuned disagree

| Case | Category / scenario | Gold | Base | Fine-tuned |
| --- | --- | --- | --- | --- |
| eval_synth-0001 | other / non_network | worth_asking | likely_contestable | worth_asking |
| eval_synth-0003 | waiting_period / accident_initial | likely_contestable | likely_valid | likely_contestable |
| eval_synth-0005 | documents_or_late_intimation / late_intimation | worth_asking | likely_contestable | worth_asking |
| eval_synth-0006 | non_disclosure_ped / disclosure_unknown | worth_asking | likely_contestable | worth_asking |
| eval_synth-0017 | no_hospitalisation_needed / short_stay | worth_asking | likely_valid | worth_asking |
