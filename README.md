# merryxmas

An animated Christmas and New Year card for the terminal.

Snow falls on a blinking Christmas tree while "Jingle Bells" plays.
A deer pulls a sleigh in, stops and opens its bag of presents. A rocket
flies out of the bag and explodes into a colorful salute, and the greetings
appear on the left.

```
                                \    /                          |
                     *\          \__/                          /&\
       \&/           __\________/(oo)                         //|\\
      /   \        _/  (        /(__)                        o//o\\o
  ___(_____)______/    ||-----||                            //*/|\*\\
  \______________/     ||     ||                           +//+/|\+\\+
* * *  ** * *** *  *  * * *  ** * ** *   * ** *** * * *   //o///o\\\o\\
```

## Requirements

- Python 3.10 or newer
- A terminal with curses support (Linux, macOS, other POSIX systems)
- [pyglet](https://pypi.org/project/pyglet/) for the music, installed
  automatically
- FFmpeg or GStreamer to decode the MP3 file. Without them the card runs
  silently.

A terminal of at least 100 × 32 characters gives the best result. Smaller
terminals work too, but parts of the scene may overlap or be cut off.

## Installation

The package is published on [PyPI](https://pypi.org/project/merryxmas/).
The easiest way to install the `merryxmas` command is
[pipx](https://pipx.pypa.io/):

```sh
pipx install merryxmas
```

or pip in a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/pip install merryxmas
```

To install from the source:

```sh
git clone https://codeberg.org/savtog/merryxmas.git
cd merryxmas
python3 -m venv .venv
.venv/bin/pip install .
```

For development, install in editable mode so that changes in `src/` take
effect without reinstalling:

```sh
.venv/bin/pip install -e .
```

## Repositories

The main repository is on Codeberg, please report issues and send pull
requests there:

- <https://codeberg.org/savtog/merryxmas> (main)
- <https://gitlab.com/savtog/merryxmas> (mirror)
- <https://github.com/savtog/merryxmas> (mirror)

## Usage

```sh
merryxmas                          # the default tree and deer
merryxmas --tree palmtree -s       # a palm tree and a stoned deer
merryxmas --tree cactus --deer cow
merryxmas --random                 # a random tree and deer
merryxmas -l                       # list the available trees and deer
```

Press `q` to quit. When the terminal is resized, the scene starts over.

You can also run the card from the source tree without installing it,
with a Python that has pyglet installed:

```sh
cd src && ../.venv/bin/python -m merryxmas
```

### Options

| Option | Description |
|---|---|
| `-l` | List all trees and deer, then exit |
| `--tree NAME_OR_PATH` | A tree name from the tree directory, or a path to a `.tre` file (a path must contain `/`) |
| `--deer NAME_OR_PATH` | A deer name from the deer directory, or a path to a `.der` file (a path must contain `/`) |
| `--random` | Pick a random tree and deer; `--tree` and `--deer` take precedence |
| `-E EYES` | The deer's eyes, 2 characters, for example `-E '^^'` |
| `-T TONGUE` | The deer's tongue, 2 characters, for example `-T 'U '` |

Modes change how the deer looks. They override `-E` and `-T`. If several
are given, the last one in this list wins.

| Mode | Look | Eyes | Tongue |
|---|---|---|---|
| `-b` | Borg | `==` | |
| `-d` | dead | `XX` | `U` |
| `-g` | greedy | `$$` | |
| `-p` | paranoid | `@@` | |
| `-s` | stoned | `**` | `U` |
| `-t` | tired | `--` | |
| `-w` | wired | `OO` | |
| `-y` | young | `..` | |

### Environment variables

| Variable | Description |
|---|---|
| `TREEPATH` | A directory with `.tre` files to use instead of the built-in trees |
| `DEERPATH` | A directory with `.der` files to use instead of the built-in deer |

## Bundled pictures

| Trees | Deer |
|---|---|
| `default`: a Christmas tree | `default`: a deer with a sleigh |
| `palmtree`: a palm tree with coconuts | `cow`: a cow with a sleigh |
| `cactus`: a cactus in bloom | `dog`: a husky with a sleigh |
| `oak`: an oak with acorns | `snowman`: a snowman with a sleigh |

## Drawing your own tree or deer

Trees are `.tre` files and deer are `.der` files. Lines starting with `##`
are comments. The picture follows a line containing just `@`. Characters
are taken as is, so backslashes need no escaping.

```
##
## A small tree
##
@
   /o\
  /o/o\
 /o/o/o\
   |||
```

In a **tree**, every `o` is a blinking toy. The tree stands in the
bottom right corner.

A **deer** comes in from the left. Its picture may contain marks that
make it move:

| Mark | Meaning |
|---|---|
| `EE` | The eyes: replaced by `-E` or a mode, they blink |
| `TT` | The tongue: replaced by `-T` or a mode, blank by default |
| `\&/` | The tied bag: it opens and the rocket starts from it |

```
##
## A deer with a sleigh and a bag of presents
##
@
                               \    /
                    *\          \__/
      \&/           __\________/(EE)
     /   \        _/  (        /(__)
 ___(_____)______/    ||-----||  TT
 \______________/     ||     ||
```

The marks are optional: without `EE` the deer does not blink, and without
`\&/` the rocket starts from the picture's top left corner.

Put your files into `src/merryxmas/trees/` or `src/merryxmas/deers/` to
make them available by name. You can also point `TREEPATH` or `DEERPATH`
to your own directory, or pass a path:

```sh
merryxmas --tree ./my.tre --deer ./my.der
```

## Project layout

```
pyproject.toml           package metadata and the merryxmas command
src/merryxmas/
    __init__.py          the scene: snow, tree, deer, rocket and salute
    __main__.py          the command line
    trees/*.tre          tree pictures
    deers/*.der          deer pictures
    jingle_bells.mp3     the music, see Music
```

## Music

`jingle_bells.mp3` is a cheerful "Jingle Bells" song with funny lyrics
("…ride on a cannon mounted sleigh"), downloaded from zvuki.top ("Jingle
bells — весёлая песня"). Its performer and license are unknown; the rights
belong to their owners. If you own them and object to its use, please open
an issue and it will be replaced.

## Acknowledgements

Based on [python-cowsay](https://codeberg.org/jamesansley/cowsay),
Copyright (C) 2025 python-cowsay contributors, licensed under the GNU
General Public License version 3 or later. The command line, the deer
modes and the picture file format come from it.

## License

Copyright (C) 2026 Aleksandr Senkevich

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the Free
Software Foundation, version 3 of the License. See
[LICENSE](https://codeberg.org/savtog/merryxmas/src/branch/main/LICENSE).
