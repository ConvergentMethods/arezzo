"""Arezzo CLI entry point.

Usage:
    arezzo               Run the MCP server (stdio transport, default)
    arezzo serve         Run the MCP server (explicit)
    arezzo init          Set up authentication and generate platform configs
    arezzo version       Print version
"""

from __future__ import annotations

import sys


def _cmd_serve():
    from arezzo.server import main
    main()


def _cmd_init():
    from arezzo.setup import run_init
    run_init()


def _cmd_version():
    from importlib.metadata import version, PackageNotFoundError
    try:
        v = version("arezzo")
    except PackageNotFoundError:
        v = "0.1.0 (dev)"
    print(f"arezzo {v}")


def main():
    args = sys.argv[1:]

    if not args or args[0] == "serve":
        _cmd_serve()
    elif args[0] == "init":
        _cmd_init()
    elif args[0] == "version" or args[0] in ("-V", "--version"):
        _cmd_version()
    else:
        print(f"arezzo: unknown command '{args[0]}'", file=sys.stderr)
        print("Usage: arezzo [serve|init|version]", file=sys.stderr)
        sys.exit(1)
