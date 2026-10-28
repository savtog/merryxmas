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
An animated christmas card for the terminal.

Snow falls on a blinking tree, a deer brings a sleigh with a bag of
presents, the bag opens and a rocket flies out of it. The rocket explodes
into a salute and the greetings appear, while "Jingle Bells" is playing.

The scene is drawn with curses and refreshed once per tick
(``TICK_TENTHS`` tenths of a second). Every object of the scene has an
``update()`` method drawing its next frame.

Coordinates in this module are always given as ``x`` (column) first and
``y`` (row) second; only curses itself takes them the other way round, see
``_addstr`` and ``_inch``.

Trees and deer are pictures in ``.tre`` and ``.der`` files, see
``parse_dot_obj`` for the format.
"""

import curses
import itertools
import math
import os
import random
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Final, TextIO

try:
    import pyglet
except ImportError:
    raise ImportError(
        'no pyglet, see <https://PyPI.org/project/pyglet>') from None


# --- settings --------------------------------------------------------------

#: One animation tick in tenths of a second (see curses.halfdelay).
TICK_TENTHS: Final = 2

#: Ticks of snow only, before the deer appears.
DEER_DELAY_TICKS: Final = 50

#: The music played with the card.
MUSIC_FILE: Final = Path(__file__).resolve().parent / 'jingle_bells.mp3'

#: Directories with tree and deer files, can be changed by the TREEPATH and
#: DEERPATH environment variables.
TREE_DIR: Final = Path(os.getenv('TREEPATH')
                       or Path(__file__).resolve().parent / 'trees')
DEER_DIR: Final = Path(os.getenv('DEERPATH')
                       or Path(__file__).resolve().parent / 'deers')

#: Colors of the salute bursts, curses color pairs 1, 2, ...
SALUTE_COLORS: Final = (curses.COLOR_RED, curses.COLOR_YELLOW,
                        curses.COLOR_GREEN, curses.COLOR_CYAN,
                        curses.COLOR_MAGENTA, curses.COLOR_WHITE)

#: A color pair with the default colors. It does not change how the
#: greetings look, it only marks their letters for snowflakes to fall
#: through, see _is_free.
GREETINGS_PAIR: Final = len(SALUTE_COLORS) + 1


@dataclass
class Option:
    """How the deer looks: both strings are 2 chars wide."""

    #: Drawn in place of the 'EE' mark of the deer picture.
    eyes: str = 'oo'
    #: Drawn in place of the 'TT' mark of the deer picture.
    tongue: str = '  '


#: Deer looks selected by the -b, -d, -g, -p, -s, -t, -w, -y options.
DEER_OPTIONS: Final[dict[str, Option]] = {
    'b': Option(eyes='=='),               # Borg
    'd': Option(eyes='XX', tongue='U '),  # dead
    'g': Option(eyes='$$'),               # greedy
    'p': Option(eyes='@@'),               # paranoid
    's': Option(eyes='**', tongue='U '),  # stoned
    't': Option(eyes='--'),               # tired
    'w': Option(eyes='OO'),               # wired
    'y': Option(eyes='..'),               # young
}


# --- tree and deer files ---------------------------------------------------

def list_trees(tree_dir: str | PathLike[str] = TREE_DIR) -> list[str]:
    """Returns the sorted names of all trees (.tre files) in tree_dir."""
    return sorted(tree.stem for tree in Path(tree_dir).glob('*.tre'))


def list_deers(deer_dir: str | PathLike[str] = DEER_DIR) -> list[str]:
    """Returns the sorted names of all deer (.der files) in deer_dir."""
    return sorted(deer.stem for deer in Path(deer_dir).glob('*.der'))


def parse_dot_obj(text: str) -> list[str]:
    """
    Parses the text of a .tre or .der file into the picture lines.

    Lines starting with '##' are comments. The picture follows the line
    consisting of a single '@'; without such a line the whole file except
    comments is the picture. Characters are taken as is, no escaping.
    Blank lines around the picture are dropped, all lines are padded with
    spaces to the same width.

    In a tree every 'o' is a blinking toy. In a deer 'EE' marks the eyes,
    'TT' marks the tongue and '\\&/' marks the tied bag with the rocket.

    :param text: The file text
    :return: The picture lines, top to bottom
    :raises ValueError: if the file contains no picture
    """
    lines = text.splitlines()
    if '@' in lines:
        lines = lines[lines.index('@') + 1:]
    else:
        lines = [line for line in lines if not line.startswith('##')]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        raise ValueError('no picture')
    width = max(len(line) for line in lines)
    return [line.ljust(width) for line in lines]


def read_dot_obj(f: TextIO) -> list[str]:
    """
    Reads and parses a .tre or .der file, see parse_dot_obj.

    :raises ValueError: if the file contains no picture
    """
    try:
        return parse_dot_obj(f.read())
    except ValueError:
        raise ValueError(f'no picture in {f.name}') from None


def get_dot_obj(name: str, directory: str | PathLike[str], suffix: str,
                kind: str,
                list_names: Callable[[str | PathLike[str]], list[str]]
                ) -> list[str]:
    """
    Reads the picture with the given name from a file in directory.

    :param name: The file name without suffix
    :param directory: The directory with the files
    :param suffix: The file suffix, '.tre' or '.der'
    :param kind: What is read, for the error message: 'tree' or 'deer'
    :param list_names: Lists the available names, for the error message
    :return: The picture lines, top to bottom
    :raises FileNotFoundError: if there is no such file
    :raises ValueError: if the file contains no picture
    """
    file = Path(directory) / f'{name}{suffix}'
    if not file.is_file():
        available = ', '.join(list_names(directory))
        raise FileNotFoundError(
            f'no {kind} {name!r} in {directory}, available: {available}')
    with open(file) as f:
        return read_dot_obj(f)


def get_tree(tree: str) -> list[str]:
    """Returns the picture lines of the tree with the given name."""
    return get_dot_obj(tree, TREE_DIR, '.tre', 'tree', list_trees)


def get_deer(deer: str) -> list[str]:
    """Returns the picture lines of the deer with the given name."""
    return get_dot_obj(deer, DEER_DIR, '.der', 'deer', list_deers)


# --- drawing helpers -------------------------------------------------------

def _addstr(screen: curses.window, x: int, y: int, text: str,
            attr: int = 0) -> None:
    """
    Draws text at column x, row y with the curses attributes attr.

    Parts that do not fit on the screen are silently skipped.
    """
    try:
        screen.addstr(y, x, text, attr)  # curses takes y first
    except curses.error:
        pass


def _inch(screen: curses.window, x: int, y: int) -> int:
    """Returns the char with its attributes at column x, row y."""
    return screen.inch(y, x)  # curses takes y first


def _is_free(cell: int) -> bool:
    """
    Whether a snowflake can fall into a cell, given its _inch() value.

    A cell is free if it is empty, a salute spark (sparks are bold) or
    a letter of the greetings (see GREETINGS_PAIR).
    """
    return (chr(cell & curses.A_CHARTEXT) == ' '
            or bool(cell & curses.A_BOLD)
            or curses.pair_number(cell) == GREETINGS_PAIR)


# --- the scene -------------------------------------------------------------

class Snowflake:
    """A snowflake falling from the top, it stops on anything in its way."""

    def __init__(self, screen: curses.window) -> None:
        self._screen = screen
        self._height_window, self._width_window = screen.getmaxyx()
        self._x = random.randint(0, self._width_window - 1)
        self._y = 0
        _addstr(self._screen, self._x, self._y, '*')

    def update(self) -> bool:
        """
        Moves the snowflake one row down, drifting it a column aside.

        :return: False once the snowflake has landed: it stays drawn,
            but needs no more updates
        """
        _addstr(self._screen, self._x, self._y, ' ')
        self._x += random.randint(-1, 1)
        self._x = min(max(self._x, 0), self._width_window - 1)
        self._y += 1
        # a flake lands on anything right below it or below on the left
        below_left = _inch(self._screen, max(self._x - 1, 0), self._y)
        below = _inch(self._screen, self._x, self._y)
        if not _is_free(below_left) or not _is_free(below):
            return False
        _addstr(self._screen, self._x, self._y, '*')
        return self._y < self._height_window - 1


class XmasTree:
    """A tree in the bottom right corner, every 'o' in it is a blinking toy."""

    _TOYS: Final = ('&', '*', '+', 'o')
    #: Ticks between repaints with new toys.
    _REPAINT_TICKS: Final = 5

    def __init__(self, screen: curses.window, picture: list[str]) -> None:
        self._screen = screen
        height_window, width_window = screen.getmaxyx()
        self._picture = picture
        self._x = width_window - len(picture[0]) - 1
        self._y = height_window - len(picture)
        self._ticks_to_repaint = self._REPAINT_TICKS
        self._paint()

    def update(self) -> None:
        """Repaints the tree with new toys every few ticks."""
        self._ticks_to_repaint -= 1
        if self._ticks_to_repaint == 0:
            self._paint()
            self._ticks_to_repaint = self._REPAINT_TICKS

    def _paint(self) -> None:
        """Draws the tree, the toys of each line get a random look."""
        for row, line in enumerate(self._picture):
            toy = random.choice(self._TOYS)
            _addstr(self._screen, self._x, self._y + row,
                    line.replace('o', toy))


class XmasDeer:
    """
    A deer with a sleigh: it rolls in from the left edge, stops and opens
    the bag with the rocket, blinking all the time.

    In the picture 'EE' marks the eyes, 'TT' marks the tongue and '\\&/'
    marks the tied bag the rocket starts from. Without the marks the deer
    does not blink, its bag does not open and the rocket starts from its
    left top corner.
    """

    #: The bag stages: from how many ticks of standing on, which part of
    #: the picture line with the bag is replaced and by what.
    _BAG_STAGES: Final = (
        (20, r'\&/', r'\|/'),      # the knot is untied
        (24, r'\&/', r'\_/'),      # the bag opens
        (28, r' \&/ ', r'\   /'),  # the bag is open
    )
    #: The rocket starts after this many ticks of standing.
    _LAUNCH_TICK: Final = 32

    #: The eyes are open from 20 to 40 ticks, then closed for 2 ticks.
    _OPEN_EYES_TICKS: Final = (20, 40)
    _CLOSED_EYES_TICKS: Final = 2

    def __init__(self, screen: curses.window, picture: list[str],
                 opts: Option) -> None:
        self._screen = screen
        self._height_window, self._width_window = screen.getmaxyx()
        # eyes and tongue are always 2 chars wide, as their marks
        eyes = (opts.eyes + '  ')[:2]
        tongue = (opts.tongue + '  ')[:2]
        self._eyes_pos = self._find(picture, 'EE')
        self._bag_pos = self._find(picture, r'\&/', offset=1)
        self._picture = [line.replace('EE', eyes).replace('TT', tongue)
                         for line in picture]
        self._width = len(picture[0])
        self._height = len(picture)

        # the deer moves by its right edge: the column right after it
        # starts at 0, so the deer rolls in from behind the left edge
        self._right = 0
        # stops at about the middle of the screen, an even column
        self._stop_right = max(self._width + 2, self._width_window // 4 * 2)
        self._bottom = self._height_window - 1  # the row below the deer
        self._standing_ticks = 0  # ticks since the deer stopped
        self._rocket_start = (0, 0)
        self._blink_timer = self._new_blink_timer()

    @staticmethod
    def _find(picture: list[str], mark: str,
              offset: int = 0) -> tuple[int, int] | None:
        """
        Returns (column, row) of the first mark in the picture plus
        offset columns, or None if there is no mark.
        """
        for row, line in enumerate(picture):
            if mark in line:
                return line.index(mark) + offset, row
        return None

    def _new_blink_timer(self) -> int:
        """Returns the ticks until the eyes open after the next blink."""
        return random.randint(*self._OPEN_EYES_TICKS) \
            + self._CLOSED_EYES_TICKS

    def rocket_start(self) -> tuple[int, int] | None:
        """
        Returns (x, y) the rocket starts from once the bag is open,
        otherwise None.
        """
        if self._standing_ticks < self._LAUNCH_TICK:
            return None
        return self._rocket_start

    def update(self) -> None:
        """Draws the deer and moves it one column right or opens the bag."""
        picture = list(self._picture)
        self._open_bag(picture)
        self._blink(picture)

        # cut the columns behind the left and the right edge of the screen
        left = self._right - self._width
        first = max(0, -left)
        last = min(self._width, self._width_window - left)
        top = self._bottom - self._height
        for row, line in enumerate(picture):
            _addstr(self._screen, left + first, top + row, line[first:last])

        if self._right < self._stop_right:
            self._right += 1
            if self._right == self._stop_right:
                bag_x = self._bag_pos[0] if self._bag_pos is not None else 0
                self._rocket_start = (left + bag_x, top)
        else:
            self._standing_ticks += 1

    def _open_bag(self, picture: list[str]) -> None:
        """Draws the bag in picture according to the standing time."""
        if self._bag_pos is None:
            return
        row = self._bag_pos[1]
        for since_tick, tied, opened in reversed(self._BAG_STAGES):
            if self._standing_ticks >= since_tick:
                picture[row] = picture[row].replace(tied, opened)
                break

    def _blink(self, picture: list[str]) -> None:
        """Closes the eyes in picture while the deer blinks."""
        self._blink_timer -= 1
        if self._blink_timer < self._CLOSED_EYES_TICKS and \
                self._eyes_pos is not None:
            column, row = self._eyes_pos
            picture[row] = (picture[row][:column] + '--'
                            + picture[row][column + 2:])
        if self._blink_timer == 0:
            self._blink_timer = self._new_blink_timer()


class Firework:
    """One burst of the salute: sparks fly out of the centre and fade away."""

    #: Spark chars by the burst age, the burst lives as many ticks.
    _SPARKS: Final = ('*', '*', '*', '+', '+', '.', '.')
    #: How fast the sparks fall down, in rows per tick squared.
    _GRAVITY: Final = 0.08

    def __init__(self, screen: curses.window, x: int, y: int) -> None:
        self._screen = screen
        self._x = x
        self._y = y
        # sparks fly evenly around, each with a slightly different speed
        count = random.randint(10, 16)
        turn = random.uniform(0, 2 * math.pi)
        self._directions = [(turn + 2 * math.pi * k / count,
                             random.uniform(0.8, 1.2))
                            for k in range(count)]
        self._attr = curses.A_BOLD
        if curses.has_colors():
            self._attr |= curses.color_pair(
                random.randint(1, len(SALUTE_COLORS)))
        self._age = 0
        self._cells: list[tuple[int, int]] = []  # (x, y) of drawn sparks

    def erase(self) -> None:
        """Erases the sparks drawn last."""
        for x, y in self._cells:
            _addstr(self._screen, x, y, ' ')
        self._cells = []

    def draw(self) -> bool:
        """
        Draws the next frame, the previous one must be erased first.

        :return: False when the burst is over
        """
        if self._age >= len(self._SPARKS):
            return False
        if self._age == 0:
            self._cells = [(self._x, self._y)]
        else:
            fall = self._GRAVITY * self._age ** 2
            # terminal chars are about twice as high as wide
            self._cells = [
                (self._x + round(self._age * speed * math.cos(angle)),
                 self._y + round(self._age * speed * math.sin(angle) / 2
                                 + fall))
                for angle, speed in self._directions]
        for x, y in self._cells:
            _addstr(self._screen, x, y, self._SPARKS[self._age], self._attr)
        self._age += 1
        return True


class Rocket:
    """
    A rocket from the deer's bag: it flies up to the right, explodes into
    a salute and shows the greetings on the left.
    """

    _PICTURE: Final = (r' ^ ', r'| |', '/|\\')
    _BLANK: Final = ('   ',) * 3
    #: The rocket moves one column right and one row up every _FLY_TICKS.
    _FLY_TICKS: Final = 2
    #: The rocket explodes when its top reaches this row.
    _EXPLODE_ROW: Final = 3
    #: Ticks between salute bursts, random in this range.
    _BURST_TICKS: Final = (2, 6)
    #: How far sparks of a burst fly, in columns.
    _BURST_RADIUS: Final = 8
    #: The top left corner of the greetings.
    _GREETINGS_X: Final = 1
    _GREETINGS_Y: Final = 1

    _XMAS_GREETINGS: Final = '''
         **   **     **     ******  ******  **    **
         **   **    ****    **   ** **   **  **  **
         *******   **  **   ******  ******    ****
         **   **  ********  **      **         **
         **   ** **      ** **      **         **

      ***    **    **    ** ******     **     *******
      ** *   **     **  **  **        ****    **   **
      **  *  **      ****   ******   **  **   *******
      **   * **       **    **      ********  **  **
      **    *** *     **    ****** **      ** **   **

                  **     ***    ** ******
                 ****    ** *   ** **   **
                **  **   **  *  ** **    **
               ********  **   * ** **   **
              **      ** **    *** ******

    ***    ***     **   ** ***    ***     **     ******
    ** *  * **      ** **  ** *  * **    ****    **
    **  **  **       ***   **  **  **   **  **   ******
    **      **      ** **  **      **  ********      **
    **      ** *   **   ** **      ** **      ** ******
'''

    def __init__(self, screen: curses.window, x: int, y: int) -> None:
        self._screen = screen
        self._height_window, self._width_window = screen.getmaxyx()
        self._x = x
        self._y = y
        self._ticks_to_move = self._FLY_TICKS
        self._greetings = self._XMAS_GREETINGS.splitlines()
        self._exploded = False
        self._fireworks: list[Firework] = []
        self._ticks_to_burst = 0

    def update(self) -> None:
        """Draws the next frame: the flying rocket or the salute."""
        for firework in self._fireworks:
            firework.erase()

        if self._y > self._EXPLODE_ROW:
            self._fly()
            return

        if not self._exploded:
            # the rocket explodes into the first burst of the salute
            self._draw(self._BLANK)
            self._exploded = True
            self._fireworks.append(
                Firework(self._screen, self._x + 1, self._y))
            self._ticks_to_burst = random.randint(*self._BURST_TICKS)

        self._draw_greetings()

        self._ticks_to_burst -= 1
        if self._ticks_to_burst <= 0:
            self._add_burst()
            self._ticks_to_burst = random.randint(*self._BURST_TICKS)
        self._fireworks = [firework for firework in self._fireworks
                           if firework.draw()]

    def _fly(self) -> None:
        """Draws the rocket, moving it up to the right every few ticks."""
        self._ticks_to_move -= 1
        if self._ticks_to_move == 0:
            self._ticks_to_move = self._FLY_TICKS
            self._draw(self._BLANK)
            self._x += 1
            self._y -= 1
        self._draw(self._PICTURE)

    def _draw(self, picture: Iterable[str]) -> None:
        """Draws picture lines with the top left corner at the rocket."""
        for row, line in enumerate(picture):
            _addstr(self._screen, self._x, self._y + row, line)

    def _draw_greetings(self) -> None:
        """
        Draws the letters of the greetings only, so that snowflakes are
        seen between them; the letters are marked to let snowflakes fall
        through them.
        """
        attr = (curses.color_pair(GREETINGS_PAIR) if curses.has_colors()
                else curses.A_BOLD)
        for row, line in enumerate(self._greetings):
            for word in re.finditer(r'\S+', line):
                _addstr(self._screen, self._GREETINGS_X + word.start(),
                        self._GREETINGS_Y + row, word.group(), attr)

    def _add_burst(self) -> None:
        """Starts a burst at a random place in the sky right of greetings."""
        radius = self._BURST_RADIUS
        greetings_width = max(len(line) for line in self._greetings)
        left = self._GREETINGS_X + greetings_width + 1 + radius
        right = self._width_window - 1 - radius
        if left > right:
            # no room right of the greetings: anywhere across the screen
            left, right = radius, max(radius, right)
        top = self._EXPLODE_ROW + 1
        bottom = max(top, self._height_window // 2 - 2)
        self._fireworks.append(Firework(self._screen,
                                        random.randint(left, right),
                                        random.randint(top, bottom)))


# --- running the card ------------------------------------------------------

def _init_colors() -> None:
    """Creates the color pairs of the salute and the greetings."""
    curses.use_default_colors()
    if curses.has_colors():
        for pair, color in enumerate(SALUTE_COLORS, 1):
            curses.init_pair(pair, color, -1)
        curses.init_pair(GREETINGS_PAIR, -1, -1)


def _play_music() -> 'pyglet.media.Player | None':
    """
    Starts the music, returns its player or None if it cannot be played:
    there is no audio device or no MP3 decoder (FFmpeg or GStreamer).
    """
    try:
        return pyglet.media.load(str(MUSIC_FILE)).play()
    except Exception:
        return None


def _play_scene(screen: curses.window, tree_picture: list[str],
                deer_picture: list[str], opts: Option) -> bool:
    """
    Plays the scene from the beginning on a clear screen.

    :return: True if the terminal was resized and the scene must restart,
        False when 'q' is pressed
    """
    screen.clear()
    tree = XmasTree(screen, tree_picture)
    deer = XmasDeer(screen, deer_picture, opts)
    rocket: Rocket | None = None
    snow: list[Snowflake] = []

    for tick in itertools.count(1):
        tree.update()
        snow = [snowflake for snowflake in snow if snowflake.update()]
        snow.append(Snowflake(screen))

        if tick >= DEER_DELAY_TICKS:
            deer.update()
            if rocket is not None:
                rocket.update()
            else:
                rocket_start = deer.rocket_start()
                if rocket_start is not None:
                    rocket = Rocket(screen, *rocket_start)

        # waits for a key at most one tick (curses.halfdelay)
        try:
            key = screen.getkey()
        except curses.error:
            continue
        if key == 'q':
            return False
        if key == 'KEY_RESIZE':
            return True
    raise AssertionError('unreachable')  # itertools.count is endless


def run(screen: curses.window, tree_picture: list[str],
        deer_picture: list[str], opts: Option) -> None:
    """
    Shows the card on the curses screen with music until 'q' is pressed.

    :param screen: The curses screen, as curses.wrapper passes it
    :param tree_picture: The tree picture lines, see parse_dot_obj
    :param deer_picture: The deer picture lines, see parse_dot_obj
    :param opts: How the deer looks
    """
    _init_colors()
    curses.curs_set(0)
    curses.halfdelay(TICK_TENTHS)

    player = _play_music()
    while _play_scene(screen, tree_picture, deer_picture, opts):
        pass
    if player is not None:
        player.pause()


def merryxmas(tree: str = 'default',
              deer: str = 'default',
              preset: str | None = None,
              eyes: str = Option.eyes,
              tongue: str = Option.tongue,
              treefile: str | None = None,
              deerfile: str | None = None) -> None:
    """
    Shows the christmas card in the terminal until 'q' is pressed.

    Parameters are listed with their corresponding options in the merryxmas
    command.

    :param tree: --tree, the available trees can be found by calling
        list_trees
    :param deer: --deer, the available deer can be found by calling
        list_deers
    :param preset: -[bdgpstwy], one of DEER_OPTIONS; eyes and tongue are
        ignored if it is given
    :param eyes: -E, the eye string
    :param tongue: -T, the tongue string
    :param treefile: the tree file text (see parse_dot_obj); if it is
        given, the tree parameter is ignored
    :param deerfile: the deer file text (see parse_dot_obj); if it is
        given, the deer parameter is ignored
    :raises FileNotFoundError: if there is no such tree or deer
    :raises ValueError: if a tree or deer file contains no picture
    """
    # load the pictures before curses takes the terminal, so that errors
    # are printed normally
    tree_picture = (get_tree(tree) if treefile is None
                    else parse_dot_obj(treefile))
    deer_picture = (get_deer(deer) if deerfile is None
                    else parse_dot_obj(deerfile))

    opts = DEER_OPTIONS.get(preset or '', Option(eyes=eyes, tongue=tongue))
    curses.wrapper(run, tree_picture, deer_picture, opts)
