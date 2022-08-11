#!/usr/bin/python3
# Don't change shebang

# Copyright(C) 2022 Morten Eek

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Python Library Imports
from specific_import import import_file
from pathlib import Path
from loguru import logger
import sys
from argparse import ArgumentParser, SUPPRESS
from cprint import *

# Local Library Imports
LIB_PATH = str(Path(Path(__file__).resolve().parents[2], 'bin', 'common'))
pw_log = import_file(str(Path(LIB_PATH, 'log.py')))
pw_convert = import_file(str(Path(LIB_PATH, 'convert.py')))
pw_file = import_file(str(Path(LIB_PATH, 'file.py')))
# pw_print = import_file(str(Path(LIB_PATH, 'print.py')))


def make_unique_dir(directory):
    counter = 0
    while True:
        counter += 1
        path = Path(str(directory) + str(counter))
        if not path.exists():
            path.mkdir()
            return str(path)


def parse_arguments(argv):
    if len(argv) == 1:
        argv.append('-h')

    parser = ArgumentParser(add_help=False)
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    optional.add_argument(
        '-h',
        action='help',
        default=SUPPRESS,
        help='show this help message and exit'
    )

    required.add_argument('-s', dest='source_dir', type=str, help='Directory path', required=True)

    return parser.parse_args()


def main(argv):
    log_file = pw_file.uniquify(Path(Path(__file__).resolve().parents[1], 'tmp', Path(__file__).stem + '.log'))
    pw_log.configure_logging(log_file)
    msg = ''

    # pw_print.cprint('tekst', 'RED')
    cprint.ok('test')		
    # print(Style.RESET_ALL)
    # def print(*args, level="INFO"):
    #     message = " ".join(map(str, args))
    #     logger.opt(depth=1).log(level, message)

    # print('test')

    # logger.level("PWINFO", no=38, color="<yellow>")
    # logger.log("PWINFO", "Here we go!", format="{message}")
    # TODO: Fiks så kan bruke msg med farge kun

    # print('')
    args = parse_arguments(argv)
    for a in args.__dict__:
        if str(a) == 'source_dir':
            args.__dict__[a] = Path(args.__dict__[a])
        print(str(a) + ": " + str(args.__dict__[a]))

    source_dir = str(args.source_dir)
    if not Path(source_dir).is_dir():
        return "'" + source_dir + "' is not a directory. Exiting..."

    pwcode_dir = Path(__file__).resolve().parents[2]

    tmp_dir = str(Path(pwcode_dir, 'config', 'tmp'))
    print('tmp_dir:    ' + tmp_dir)

    target_dir = make_unique_dir(Path(pwcode_dir, 'projects', 'convert_project'))
    print('target_dir: ' + target_dir)

    msg, file_count, errors, originals = pw_convert.convert_folder(source_dir, target_dir, tmp_dir, merge=False, keep_file_name=True)
    logger.success('Done')
    return msg


if __name__ == '__main__':
    print(main(sys.argv))
