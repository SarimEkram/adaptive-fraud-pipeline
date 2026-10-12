"""Command-line entrypoint: mlp <command>."""

import argparse

from ml_platform import drift, evaluate, promote, replay, train

COMMANDS = {
    "replay": replay.run,
    "train": train.run,
    "evaluate": evaluate.run,
    "drift": drift.run,
    "promote": promote.run,
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="mlp")
    parser.add_argument("command", choices=COMMANDS)
    args, rest = parser.parse_known_args()
    COMMANDS[args.command](rest)


if __name__ == "__main__":
    main()
