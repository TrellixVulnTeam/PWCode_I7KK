
import sys
from argparse import ArgumentParser, SUPPRESS
from loguru import logger
from pathlib import Path
from specific_import import import_file
pw_convert = import_file(str(Path(Path(__file__).resolve().parents[2], 'bin', 'common', 'convert.py')))


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
    return msg


if __name__ == '__main__':
    print(main(sys.argv))
