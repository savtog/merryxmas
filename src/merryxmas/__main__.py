# Copyright (C) 2026 Aleksandr Senkevich <savtog@mail.ru>
# Based on python-cowsay, Copyright (C) 2025 python-cowsay contributors
# <https://codeberg.org/jamesansley/cowsay>, modified for merryxmas.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
The merryxmas command: parses the command line and shows the card.

Can be run as the installed ``merryxmas`` command, as ``python -m merryxmas``
or as a plain script.
"""

import argparse
import os
import random
import sys

if not __package__:
    # run as a plain script (python src/merryxmas/__main__.py):
    # make the relative import below resolve to the merryxmas package
    sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    __package__ = 'merryxmas'

from . import (  # noqa: E402 (the import must follow the path fix)
    merryxmas as _merryxmas, Option, list_trees, list_deers)


parser = argparse.ArgumentParser(
    prog="merryxmas",
    description="Generates an ASCII video clip with congratulations on "
                "New Year and Christmas.",
)

parser.add_argument(
    "-l", action="store_true",
    help="Lists all christmas trees and deers in the tree and deer paths "
         "and exits",
)
parser.add_argument(
    "--tree", type=str, metavar="treefile",
    help="Either the name of a tree specified in the TREEPATH, "
         "or a path to a treefile (if provided as a path, the path must "
         "contain at least one path separator)",
)
parser.add_argument(
    "--deer", type=str, metavar="deerfile",
    help="Either the name of a deer specified in the DEERPATH, "
         "or a path to a deerfile (if provided as a path, the path must "
         "contain at least one path separator)",
)
parser.add_argument(
    "-E", type=str, dest="eyes",
    help="An eye string. This is ignored if a preset mode is given",
    default=Option.eyes, metavar="eye_string",
)
parser.add_argument(
    "-T", type=str, dest="tongue",
    help="A tongue string. This is ignored if a preset mode is given",
    default=Option.tongue, metavar="tongue_string",
)
parser.add_argument(
    "--random", action="store_true",
    help="If provided, picks a random tree and deer from the TREEPATH "
         "and DEERPATH. Is superseded by the --tree and --deer option",
)

group = parser.add_argument_group(
    title="Mode",
    description="There are several out of the box modes "
                "which change the appearance of the deer. "
                "If multiple modes are given, the one furthest "
                "down this list is selected",
)
group.add_argument("-b", action="store_const", const="b", help="Borg")
group.add_argument("-d", action="store_const", const="d", help="dead")
group.add_argument("-g", action="store_const", const="g", help="greedy")
group.add_argument("-p", action="store_const", const="p", help="paranoid")
group.add_argument("-s", action="store_const", const="s", help="stoned")
group.add_argument("-t", action="store_const", const="t", help="tired")
group.add_argument("-w", action="store_const", const="w", help="wired")
group.add_argument("-y", action="store_const", const="y", help="young")


def get_file(name_or_path: str | None) -> str | None:
    """
    Returns the text of the file if --tree or --deer is a path (contains
    a path separator), otherwise None: then it is a name to look up.
    """
    if name_or_path is None or os.sep not in name_or_path:
        return None
    with open(name_or_path) as f:
        return f.read()


def get_preset(args: argparse.Namespace) -> str | None:
    """Returns the selected mode, the one furthest down the list wins."""
    return (args.y or args.w or args.t or args.s
            or args.p or args.g or args.d or args.b)


def merryxmas() -> None:
    """
    The entry point of the merryxmas command: parses the command line and
    shows the card with the selected tree, deer and deer look; prints the
    list of trees and deer instead with -l.
    """
    args = parser.parse_args()

    if args.l:
        print("Lists all tree file names:")
        print("-", "\n- ".join(list_trees()))
        print("Lists all deer file names:")
        print("-", "\n- ".join(list_deers()))
        return

    if args.random:
        tree = args.tree or random.choice(list_trees())
        deer = args.deer or random.choice(list_deers())
    else:
        tree = args.tree or "default"
        deer = args.deer or "default"

    try:
        _merryxmas(
            tree=tree,
            deer=deer,
            preset=get_preset(args),
            eyes=args.eyes,
            tongue=args.tongue,
            treefile=get_file(args.tree),
            deerfile=get_file(args.deer),
        )
    except (OSError, ValueError) as e:
        parser.error(str(e))


if __name__ == '__main__':
    merryxmas()
