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
from distutils.util import strtobool
import sys
# from argparse import ArgumentParser, SUPPRESS
import typer
from pathlib import Path
import xml.etree.ElementTree as ET
from loguru import logger
from specific_import import import_file
from rich.console import Console

# Paths:
PWCODE_DIR = Path(__file__).resolve().parents[2]
LIB_DIR = Path(PWCODE_DIR, 'bin', 'common')
TMP_DIR = Path(PWCODE_DIR, 'config', 'tmp')
paths = [PWCODE_DIR, LIB_DIR, TMP_DIR]

# Local Library Imports
pw_log = import_file(str(Path(LIB_DIR, 'log.py')))
pw_file = import_file(str(Path(LIB_DIR, 'file.py')))
pw_ddl = import_file(str(Path(LIB_DIR, 'ddl.py')))

# Initialize:
console = Console()


def get_columns(table_defs, schema, empty_tables, quote):
    ddl_columns = {}

    for table_def in table_defs:
        table_schema = table_def.find('table-schema')
        if table_schema is not None:
            if table_schema.text is not None and len(schema) > 0:
                if table_schema.text != schema:
                    continue

        table_name = table_def.find("table-name")
        if table_name.text in empty_tables:
            continue

        ddl_columns_list = []
        column_defs = table_def.findall("column-def")
        column_defs[:] = sorted(column_defs, key=lambda elem: int(elem.findtext('dbms-position')))
        for column_def in column_defs:
            column_name = column_def.find('column-name')
            if quote:
                ddl_columns_list.append('"' + column_name.text + '",')
            else:
                ddl_columns_list.append(column_name.text + ',')
        ddl_columns[table_name.text] = ''.join(ddl_columns_list)

    return ddl_columns


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

    required.add_argument('-p', dest='path', type=str, help='Path of metadata.xml file', required=True)
    required.add_argument('-t', dest='target', type=str, help='SQL Workbench/J target profile', required=True)
    optional.add_argument('-q', dest='quote', choices=[True, False],  type=lambda x: bool(strtobool(x)), help='Quote table/fields in source query (default: %(default)s)', default='True')
    optional.add_argument('-s', dest='sql_type', choices=['sqlite', 'h2', 'iso'], help='SQL dialect (default: %(default)s)', default='iso')
    optional.add_argument('-l', dest='table_list', type=str, help='Path of file with list of tables to include.')

    return parser.parse_args()


def main(argv):
    args = parse_arguments(argv)
    for a in args.__dict__:
        print(str(a) + ": " + str(args.__dict__[a]))

    metadata_file = args.path
    dir_path = Path(metadata_file).resolve().parents[0]

    if not Path(metadata_file).is_file():
        return "No 'metada.xml' file in script-directory. Exiting..."

    # WAIT: Håndtere table list for flere skjema?
    include_tables = []
    if args.table_list:
        with open(args.table_list) as file:
            include_tables = file.read().splitlines()

    tree = ET.parse(metadata_file)
    table_defs = tree.findall("table-def")
    schemas = set()
    for table_def in table_defs:
        table_schema = table_def.find('table-schema')
        schema = table_schema.text
        schemas.add(schema)

    msg = ''
    log_file = pw_file.uniquify(Path(TMP_DIR, Path(__file__).stem + '.log'))
    pw_log.configure_logging(log_file)

    for schema in schemas:
        if not schema:
            file_name = 'wbcopy.sql'
        else:
            file_name = schema + '_wbcopy.sql'

        wbcopy_file = str(Path(dir_path, file_name))
        empty_tables = pw_ddl.get_empty_tables(table_defs, schema, include_tables)
        columns = get_columns(table_defs, schema, empty_tables, args.quote)

        with open(wbcopy_file, "w") as file:
            if schema:
                file.write("-- DDL for schema '" + schema + "': \n")

        for table_def in table_defs:
            table_schema = table_def.find('table-schema')
            if table_schema is not None:
                if table_schema.text is not None and len(schema) > 0:
                    if table_schema.text != schema:
                        continue

            table_name = table_def.find("table-name")
            if table_name.text in empty_tables:
                continue

            tbl = table_name.text
            if args.quote:
                tbl = '"' + tbl + '"'

            source_query = ' '.join((
                'SELECT',
                columns[table_name.text][:-1],
                'FROM',
                tbl,
            ))

            params = '-mode=INSERT -ignoreIdentityColumns=false -removeDefaults=true -commitEvery=10000 '
            if args.sql_type == 'sqlite':
                params = params + '-preTableStatement="PRAGMA foreign_keys=OFF;PRAGMA journal_mode=OFF;PRAGMA synchronous=0;PRAGMA locking_mode=EXCLUSIVE;PRAGMA temp_store=MEMORY;" '
            copy_data_str = 'WbCopy ' + params + '-targetProfile=' + args.target + ' -targetTable="' + table_name.text + '" -sourceQuery=' + source_query + ';'

            with open(wbcopy_file, "a") as file:
                file.write("\n" + copy_data_str)

        msg = msg + "\nDDL written to '" + wbcopy_file + "'"

    return msg[1:]


# if __name__ == '__main__':
#     print(main(sys.argv))

if __name__ == "__main__":
    typer.run(main)
