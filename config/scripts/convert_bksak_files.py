
# from defs import file_convert  # .defs.py
import sys
from argparse import ArgumentParser, SUPPRESS
# import shutil
from loguru import logger
# import os
from pathlib import Path
from specific_import import import_file
# import xml.etree.ElementTree as ET
# import subprocess
# import csv
# from common.xml_settings import XMLSettings
# from common.convert import convert_folder
# from distutils.util import strtobool
# from petl import extendheader, rename, appendtsv

# WAIT: Lage egen plugin.py som setter paths mm så slipper å repetere i plugin kode
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))


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
    # TODO: Endre gui-kode til å lese fra config-fil og så kjøre kommando med args så likt uansett om fra gui eller cli?
    pwcode_dir = Path(__file__).resolve().parents[2]

    args = parse_arguments(argv)
    for a in args.__dict__:
        if str(a) == 'source_dir':
            args.__dict__[a] = Path(args.__dict__[a])
        print(str(a) + ": " + str(args.__dict__[a]))

    source_dir = str(args.source_dir)
    if not Path(source_dir).is_dir():
        return "'" + source_dir + "' is not a directory. Exiting..."

    tmp_dir = str(Path(pwcode_dir, 'config', 'tmp'))
    print('tmp_dir:    ' + tmp_dir)

    target_dir = make_unique_dir(Path(pwcode_dir, 'projects', 'convert_project'))
    print('target_dir: ' + target_dir)

    convert = import_file(str(Path(pwcode_dir, 'bin', 'common', 'convert.py')))
    msg, file_count, errors, originals = convert.convert_folder(source_dir, target_dir, tmp_dir, merge=False, keep_file_name=True)
    print(msg)


if __name__ == '__main__':
    print(main(sys.argv))
