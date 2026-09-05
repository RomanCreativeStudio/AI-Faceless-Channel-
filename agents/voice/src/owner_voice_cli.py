"""CLI: python -m agents.voice.src.owner_voice_cli [--check]

Reports whether the owner-authorized voice provider is actually usable
right now, reading configuration from the OWNER_VOICE_* environment
variables (see agents/voice/src/owner_voice.py). Never generates audio,
never prints a credential value or the sample file's contents — only
identifiers, presence/absence, and a human-readable reason. Safe to run
at any time, including with nothing configured.
"""
from __future__ import annotations

import argparse
import json
import sys

from .owner_voice import OwnerVoiceConfig, check_owner_voice_availability, registered_engine_names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check owner-voice provider availability")
    parser.add_argument(
        "--check", action="store_true",
        help="present for clarity in scripts/CI; this command always just checks",
    )
    parser.parse_args(argv)

    config = OwnerVoiceConfig.from_env()
    availability = check_owner_voice_availability(config)

    payload = {
        "status": availability.status.value,
        "available": availability.available,
        "reason": availability.reason,
        "configuration": config.redacted_summary(),
        "registered_engines": registered_engine_names(),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if availability.available else 1


if __name__ == "__main__":
    sys.exit(main())
