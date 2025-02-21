"""Command-line interface for BuildBot."""

import os
import sys
import argparse
from .shell import BuildBotShell

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="BuildBot - An AI-powered troubleshooting assistant"
    )
    parser.add_argument(
        "--config",
        help="Path to configuration directory",
        default=os.path.expanduser("~/.buildbot")
    )
    parser.add_argument(
        "--model",
        help="Path to LLM model file",
        default=None
    )
    parser.add_argument(
        "--debug",
        help="Enable debug logging",
        action="store_true"
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="Command to run (default: start shell)",
        default="shell"
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Command arguments"
    )
    return parser.parse_args()

def setup_environment(args):
    """Set up the BuildBot environment."""
    # Create config directory if it doesn't exist
    os.makedirs(args.config, exist_ok=True)

    # Set environment variables
    os.environ["BUILDBOT_CONFIG_DIR"] = args.config
    os.environ["BUILDBOT_MODEL_DIR"] = os.path.join(args.config, "models")
    os.environ["BUILDBOT_PROMPT_DIR"] = os.path.join(args.config, "prompts")

    if args.model:
        os.environ["BUILDBOT_MODEL_PATH"] = args.model

    if args.debug:
        os.environ["BUILDBOT_DEBUG"] = "1"

def main():
    """Main entry point for the buildbot command."""
    try:
        args = parse_args()
        setup_environment(args)

        if args.command == "shell":
            # Start interactive shell
            BuildBotShell().cmdloop()
        else:
            # Execute single command
            shell = BuildBotShell()
            cmd_method = getattr(shell, f"do_{args.command}", None)
            if cmd_method:
                cmd_method(" ".join(args.args))
            else:
                print(f"Unknown command: {args.command}")
                sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        if os.getenv("BUILDBOT_DEBUG"):
            raise
        sys.exit(1)

if __name__ == "__main__":
    main() 