# Report: blackboard, fanout, hybrid, mapstate, mapstate_routes, react, rounds

> Development result (dev seeds). Must not be reported.

Runs: 20261031-221233-react+mapstate+mapstate_routes+hybrid+fanout+rounds+blackboard · model openai:gpt-6-luna · temperature provider default · reasoning provider default · token cap 2,000,000 · max output 4,096 · prompt ff9afb3b9f66 · seeds dev 1000 · repeats 1

| Arch | Level | Episodes | Success | Efficiency (median) | Invalid / ep | Budget hit | Token cap hit | Output limit hit | Calls (median) | Input tokens (median) | Output tokens (median) | Latency (median) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blackboard | L1 | 1 | 100% | 0.29 | 0.0 | 0% | 0% | 0% | 14 | 13,913 | 1,882 | 34.0s |
| blackboard | L2 | 1 | 100% | 0.24 | 0.0 | 0% | 0% | 0% | 43 | 49,489 | 6,764 | 117.0s |
| blackboard | L3 | 1 | 100% | 0.20 | 0.0 | 0% | 0% | 0% | 91 | 112,902 | 16,364 | 341.3s |
| fanout | L1 | 1 | 100% | 0.44 | 0.0 | 0% | 0% | 0% | 10 | 8,670 | 833 | 20.1s |
| fanout | L2 | 1 | 100% | 0.26 | 0.0 | 0% | 0% | 0% | 41 | 39,756 | 2,554 | 44.2s |
| fanout | L3 | 1 | 0% | — | 0.0 | 100% | 0% | 0% | 109 | 117,721 | 9,638 | 214.4s |
| hybrid | L1 | 1 | 100% | 0.50 | 0.0 | 0% | 0% | 0% | 8 | 3,474 | 216 | 9.5s |
| hybrid | L2 | 1 | 100% | 0.71 | 0.0 | 0% | 0% | 0% | 11 | 5,374 | 452 | 11.7s |
| hybrid | L3 | 1 | 100% | 0.50 | 0.0 | 0% | 0% | 0% | 25 | 15,376 | 1,043 | 27.0s |
| mapstate | L1 | 1 | 100% | 1.00 | 0.0 | 0% | 0% | 0% | 4 | 2,932 | 108 | 7.2s |
| mapstate | L2 | 1 | 100% | 0.53 | 0.0 | 0% | 0% | 0% | 19 | 16,353 | 659 | 29.5s |
| mapstate | L3 | 1 | 100% | 0.39 | 1.0 | 0% | 0% | 0% | 46 | 44,281 | 2,110 | 79.5s |
| mapstate_routes | L1 | 1 | 100% | 0.50 | 0.0 | 0% | 0% | 0% | 8 | 6,205 | 177 | 11.1s |
| mapstate_routes | L2 | 1 | 100% | 0.56 | 0.0 | 0% | 0% | 0% | 17 | 15,613 | 610 | 26.3s |
| mapstate_routes | L3 | 1 | 100% | 0.38 | 0.0 | 0% | 0% | 0% | 46 | 48,094 | 1,961 | 74.0s |
| react | L1 | 1 | 100% | 0.80 | 0.0 | 0% | 0% | 0% | 5 | 3,605 | 134 | 8.6s |
| react | L2 | 1 | 100% | 0.83 | 0.0 | 0% | 0% | 0% | 12 | 13,338 | 371 | 21.3s |
| react | L3 | 1 | 100% | 0.56 | 0.0 | 0% | 0% | 0% | 32 | 71,360 | 985 | 57.4s |
| rounds | L1 | 1 | 100% | 0.50 | 0.0 | 0% | 0% | 0% | 11 | 8,584 | 745 | 19.4s |
| rounds | L2 | 1 | 100% | 0.39 | 0.0 | 0% | 0% | 0% | 37 | 31,818 | 3,950 | 68.3s |
| rounds | L3 | 1 | 100% | 0.26 | 0.0 | 0% | 0% | 0% | 91 | 87,625 | 7,074 | 197.0s |

## Comparison

> Development result (dev seeds). Must not be reported.

Seeds 1000, 1 repeat. Differences are against the reference architecture in the last column.

### L1

| Arch | Success | Efficiency | Steps | Tokens | Calls: orch / scouts | Latency | Scouts | Δ success | Δ efficiency | Reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| react | 100% | 0.80 | 5 | 3,739 | 0 / 5 | 8.6s | 1 | — | — | — |
| mapstate | 100% | 1.00 | 4 | 3,040 | 0 / 4 | 7.2s | 1 | +0 pp | +0.20 | react |
| mapstate_routes | 100% | 0.50 | 8 | 6,382 | 0 / 8 | 11.1s | 1 | +0 pp | −0.50 | mapstate |
| hybrid | 100% | 0.50 | 8 | 3,690 | 0 / 8 | 9.5s | 1 | +0 pp | +0.00 | mapstate_routes |
| fanout | 100% | 0.44 | 9 | 9,503 | 1 / 9 | 20.1s | 1 | +0 pp | −0.56 | mapstate |
| rounds | 100% | 0.50 | 8 | 9,329 | 2 / 9 | 19.4s | 1 | +0 pp | −0.50 | mapstate |
| blackboard | 100% | 0.29 | 14 | 15,795 | 0 / 14 | 34.0s | 4 | +0 pp | −0.71 | mapstate |

### L2

| Arch | Success | Efficiency | Steps | Tokens | Calls: orch / scouts | Latency | Scouts | Δ success | Δ efficiency | Reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| react | 100% | 0.83 | 12 | 13,709 | 0 / 12 | 21.3s | 1 | — | — | — |
| mapstate | 100% | 0.53 | 19 | 17,012 | 0 / 19 | 29.5s | 1 | +0 pp | −0.31 | react |
| mapstate_routes | 100% | 0.56 | 18 | 16,223 | 0 / 17 | 26.3s | 1 | +0 pp | +0.03 | mapstate |
| hybrid | 100% | 0.71 | 14 | 5,826 | 0 / 11 | 11.7s | 1 | +0 pp | +0.16 | mapstate_routes |
| fanout | 100% | 0.26 | 39 | 42,310 | 1 / 40 | 44.2s | 2 | +0 pp | −0.27 | mapstate |
| rounds | 100% | 0.39 | 26 | 35,768 | 8 / 29 | 68.3s | 2 | +0 pp | −0.14 | mapstate |
| blackboard | 100% | 0.24 | 42 | 56,253 | 0 / 43 | 117.0s | 4 | +0 pp | −0.29 | mapstate |

### L3

| Arch | Success | Efficiency | Steps | Tokens | Calls: orch / scouts | Latency | Scouts | Δ success | Δ efficiency | Reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| react | 100% | 0.56 | 32 | 72,345 | 0 / 32 | 57.4s | 1 | — | — | — |
| mapstate | 100% | 0.39 | 46 | 46,391 | 0 / 46 | 79.5s | 1 | +0 pp | −0.17 | react |
| mapstate_routes | 100% | 0.38 | 47 | 50,055 | 0 / 46 | 74.0s | 1 | +0 pp | −0.01 | mapstate |
| hybrid | 100% | 0.50 | 36 | 16,419 | 0 / 25 | 27.0s | 1 | +0 pp | +0.12 | mapstate_routes |
| fanout | 0% | — | 108 | 127,359 | 1 / 108 | 214.4s | 2 | −100 pp | — | mapstate |
| rounds | 100% | 0.26 | 70 | 94,699 | 13 / 78 | 197.0s | 2 | +0 pp | −0.13 | mapstate |
| blackboard | 100% | 0.20 | 89 | 129,266 | 0 / 91 | 341.3s | 4 | +0 pp | −0.19 | mapstate |
