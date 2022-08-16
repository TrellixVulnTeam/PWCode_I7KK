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
import sys
# from argparse import ArgumentParser, SUPPRESS
import typer
from pathlib import Path
from loguru import logger
from rich.console import Console
from specific_import import import_file
import jaydebeapi

# Paths:
PWCODE_DIR = Path(__file__).resolve().parents[2]
LIB_DIR = Path(PWCODE_DIR, 'bin', 'common')
JARS_DIR = Path(PWCODE_DIR, 'bin', 'vendor', 'jars')
TMP_DIR = Path(PWCODE_DIR, 'config', 'tmp')
paths = [PWCODE_DIR, LIB_DIR, JARS_DIR, TMP_DIR]

# Local Library Imports:
pw_log = import_file(str(Path(LIB_DIR, 'log.py')))
pw_file = import_file(str(Path(LIB_DIR, 'file.py')))

# Initialize:
console = Console()


def get_tables(conn, schema, driver_class):
    results = conn.jconn.getMetaData().getTables(None, schema, "%", None)
    table_reader_cursor = conn.cursor()
    table_reader_cursor._rs = results
    table_reader_cursor._meta = results.getMetaData()
    read_results = table_reader_cursor.fetchall()
    tables = [row[2] for row in read_results if row[3] == 'TABLE']

    for index, table in enumerate(tables):
        table_name = table
        if driver_class != 'interbase.interclient.Driver':
            table_name = '"' + table + '"'

        get_count = 'SELECT COUNT(*) from ' + table_name
        table_reader_cursor.execute(get_count)
        (row_count,) = table_reader_cursor.fetchone()
        tables[index] = table + ':' + str(row_count)

    return tables


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

    required.add_argument('-j', dest='jdbc_url', type=str, help='JDBC url', required=True)
    optional.add_argument('-s', dest='schema', type=str, help='Database schema', default='')
    optional.add_argument('-u', dest='user', type=str, help='Database username', default='')
    optional.add_argument('-p', dest='password', type=str, help='Database password', default='')

    return parser.parse_args()


def main(argv):
    args = parse_arguments(argv)
    for a in args.__dict__:
        print(str(a) + ": " + str(args.__dict__[a]))

    # TODO: lag grid med jar og class for div dbtyper -> se generate_ddl.py for lignende
    driver_jar = str(Path(JARS_DIR, 'h2.jar'))
    driver_class = 'org.h2.Driver'
    msg = ''
    log_file = pw_file.uniquify(Path(TMP_DIR, Path(__file__).stem + '.log'))
    pw_log.configure_logging(log_file)


    header = '\n'
    file_name = 'table_list.txt'
    if args.schema:
        file_name = args.schema + '_' + file_name
        header = "-- Tables for schema '" + args.schema + "': " + header

    table_file = str(Path(Path(__file__).resolve().parents[3], file_name))
    with open(table_file, "w") as file:
        file.write(header)

    tables = ''
    with jaydebeapi.connect(driver_class, args.jdbc_url, [args.user, args.password], driver_jar,) as conn:
        tables = get_tables(conn, args.schema, driver_class)

    for table in tables:
        with open(table_file, "a") as file:
            file.write(table + '\n')

    msg = msg + "\nTable list written to '" + table_file + "'"
    return msg[1:]


# if __name__ == '__main__':
#     print(main(sys.argv))

if __name__ == "__main__":
    typer.run(main)