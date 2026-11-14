"""Attacker service (Phase 3+). Clearly a SIMULATION for the demo.

Planned:
  python -m seashield.attacker --scenario spike --buoy SS-B01   # one-shot from the CLI
  python -m seashield.attacker --serve                          # small HTTP API the dashboard calls
"""

import argparse

SCENARIOS = ["tamper", "replay", "spike", "false_wind", "suppress", "drift"]


def main() -> None:
    parser = argparse.ArgumentParser(description="SeaShield SIMULATED attacker")
    parser.add_argument("--scenario", choices=SCENARIOS)
    parser.add_argument("--buoy", default="SS-B01")
    parser.add_argument("--serve", action="store_true", help="expose scenarios to the dashboard")
    args = parser.parse_args()
    # TODO Phase 3: subscribe to the target buoy topic, capture a message,
    # apply seashield.attacker.scenarios.<scenario>, publish it on the same topic.
    raise SystemExit(f"attacker not implemented yet (args: {args})")


if __name__ == "__main__":
    main()
