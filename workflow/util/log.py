from __future__ import annotations

import os
import sys


_USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code: str, s: str) -> str:
    return f"\x1b[{code}m{s}\x1b[0m" if _USE_COLOR else s


class color:
    dim    = staticmethod(lambda s: _c("2", s))
    bold   = staticmethod(lambda s: _c("1", s))
    red    = staticmethod(lambda s: _c("31", s))
    green  = staticmethod(lambda s: _c("32", s))
    yellow = staticmethod(lambda s: _c("33", s))
    blue   = staticmethod(lambda s: _c("34", s))
    cyan   = staticmethod(lambda s: _c("36", s))


def info(msg: str) -> None:
    sys.stdout.write(f"{msg}\n")


def ok(msg: str) -> None:
    sys.stdout.write(f"{color.green('✓')} {msg}\n")


def warn(msg: str) -> None:
    sys.stderr.write(f"{color.yellow('!')} {msg}\n")


def fail(msg: str) -> None:
    sys.stderr.write(f"{color.red('✗')} {msg}\n")


def step(msg: str) -> None:
    sys.stdout.write(f"{color.cyan('›')} {msg}\n")


def fatal(msg: str) -> None:
    """Abort the current CLI command with `msg` as the error text."""
    import click
    raise click.ClickException(msg)
