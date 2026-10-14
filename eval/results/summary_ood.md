# Eval summary: `ood`

15 cases (5 labelled contestable, 5 labelled valid, 5 moratorium edge). Same prompt, renderer, parser and temperature 0 for every model.

| Metric | Base Qwen3.5-4B | Fine-tuned |
| --- | ---: | ---: |
| Valid JSON rate | 100.0% (15/15) | 100.0% (15/15) |
| Category accuracy | 93.3% (14/15) | 100.0% (15/15) |
| Verdict accuracy | 66.7% (10/15) | 93.3% (14/15) |
| **Contestable recall** (catches fightable claims) | 60.0% (3/5) | 80.0% (4/5) |
| **Over-optimism rate** (not contestable, called contestable; lower is better) | 20.0% (2/10) | 0.0% (0/10) |
| False hope rate (valid, called contestable; lower is better) | 0.0% (0/5) | 0.0% (0/5) |
| Moratorium edge accuracy | 60.0% (3/5) | 100.0% (5/5) |
| Fact accuracy | 88.3% (91/103) | 98.1% (101/103) |
| Months-of-cover fact accuracy | 33.3% (5/15) | 93.3% (14/15) |

## Verdict confusion matrix: Base Qwen3.5-4B

| gold \ predicted | likely_contestable | worth_asking | likely_valid | unparsed |
| --- | ---: | ---: | ---: | ---: |
| **likely_contestable** | 3 | 0 | 2 | 0 |
| **worth_asking** | 2 | 2 | 1 | 0 |
| **likely_valid** | 0 | 0 | 5 | 0 |

## Verdict confusion matrix: Fine-tuned

| gold \ predicted | likely_contestable | worth_asking | likely_valid | unparsed |
| --- | ---: | ---: | ---: | ---: |
| **likely_contestable** | 4 | 1 | 0 | 0 |
| **worth_asking** | 0 | 5 | 0 | 0 |
| **likely_valid** | 0 | 0 | 5 | 0 |

## Verdict accuracy by category

| Category | Base Qwen3.5-4B | Fine-tuned |
| --- | ---: | ---: |
| documents_or_late_intimation | 0.0% (0/1) | 100.0% (1/1) |
| no_hospitalisation_needed | 100.0% (1/1) | 0.0% (0/1) |
| non_disclosure_ped | 60.0% (3/5) | 100.0% (5/5) |
| other | 100.0% (1/1) | 100.0% (1/1) |
| permanent_exclusion | 100.0% (1/1) | 100.0% (1/1) |
| policy_lapsed | 100.0% (1/1) | 100.0% (1/1) |
| room_rent_proportionate | 100.0% (1/1) | 100.0% (1/1) |
| sum_insured_exhausted | 100.0% (1/1) | 100.0% (1/1) |
| waiting_period | 33.3% (1/3) | 100.0% (3/3) |

## Cases where base and fine-tuned disagree

| Case | Category / scenario | Gold | Base | Fine-tuned |
| --- | --- | --- | --- | --- |
| ood-0000 | non_disclosure_ped / moratorium | likely_contestable | likely_valid | likely_contestable |
| ood-0005 | waiting_period / served | likely_contestable | likely_valid | likely_contestable |
| ood-0009 | no_hospitalisation_needed / long_stay | likely_contestable | likely_contestable | worth_asking |
| ood-0011 | documents_or_late_intimation / late_intimation | worth_asking | likely_contestable | worth_asking |
| ood-0004 | non_disclosure_ped / unrelated | worth_asking | likely_contestable | worth_asking |
