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

# Python Library Imports:
from loguru import logger
import typer
from pathlib import Path
from importlib.metadata import version
from platform import python_version
from specific_import import import_file
from rich.console import Console

# Paths:
PWCODE_DIR = Path(__file__).resolve().parents[2]
LIB_DIR = Path(PWCODE_DIR, 'bin', 'common')
PROJECT_DIR = Path(PWCODE_DIR, 'projects')
TMP_DIR = Path(PWCODE_DIR, 'config', 'tmp')

# Local Library Imports:
pw_log = import_file(str(Path(LIB_DIR, 'log.py')))
pw_file = import_file(str(Path(LIB_DIR, 'file.py')))

# Initialize:
console = Console()
log_file = pw_file.uniquify(Path(TMP_DIR, Path(__file__).stem + '.log'))
pw_log.configure_logging(log_file)


def main(name: str):
    msg = 'Done'


    # TODO: Kode som lager arkivpakkestruktur i PROJECT_DIR

    # console.print("Hello", "World!", style="bold red")
    # print(name + 3)
    console.print(version('typer'))



    # args = parse_arguments(argv)
    # print('\n'.join((('python version: ' + python_version(),
    #                     'loguru version: ' + version('loguru'),
    #                     ))))    
    # for a in args.__dict__:
    #     print(str(a) + ": " + str(args.__dict__[a]))

    console.print(msg)

if __name__ == "__main__":
    typer.run(main)
 
