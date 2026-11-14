"""Evaluate SeaShield on held-out data with injected, labelled attacks (Phase 6).

Reports (all numbers from real runs, nothing invented):
  - precision, recall, F1, false-positive rate (especially during real storms)
  - detection rate vs. attack magnitude (+10 %, +50 %, +200 % ...)
  - detection latency, per-message processing time
  - ablation: crypto -> +physics -> +AI -> +neighbours
  - unprotected vs SeaShield: fake alerts issued, real alerts missed
Writes docs/evaluation.md and plots to docs/assets/.
"""


def main() -> None:
    # TODO Phase 6
    raise NotImplementedError


if __name__ == "__main__":
    main()
