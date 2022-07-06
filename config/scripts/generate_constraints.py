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
import xml.etree.ElementTree as ET
import sys
from loguru import logger
from argparse import ArgumentParser, SUPPRESS
from pathlib import Path
from specific_import import import_file

# Local Library Imports
LIB_PATH = str(Path(Path(__file__).resolve().parents[2], 'bin', 'common'))
pw_ddl = import_file(str(Path(LIB_PATH, 'ddl.py')))


def add_unique(table_defs, schema, empty_tables):
    constraints = []
    unique_dict = {}

    for table_def in table_defs:
        if schema:
            table_schema = table_def.find('table-schema')
            if table_schema.text != schema:
                continue

        table_name = table_def.find('table-name')
        if table_name.text in empty_tables:
            continue

        index_defs = table_def.findall('index-def')

        for index_def in index_defs:
            unique = index_def.find('unique')
            primary_key = index_def.find('primary-key')

            unique_col_list = []
            if unique.text == 'true' and primary_key.text == 'false':
                index_name = index_def.find('name')
                index_column_names = index_def.findall('column-list/column')
                for index_column_name in index_column_names:
                    unique_constraint_name = index_column_name.attrib['name']
                    unique_col_list.append('"' + unique_constraint_name + '"')
                unique_dict[(table_name.text, index_name.text)] = sorted(unique_col_list)

        unique_str = '\n'
        unique_constraints = {key: val for key, val in unique_dict.items() if key[0] == table_name.text}
        if unique_constraints:
            for key, value in unique_constraints.items():
                if schema:
                    table = '"' + schema + '"."' + table_name.text + '"'
                else:
                    table = '"' + table_name.text + '"'

                unique_str = unique_str + 'ALTER TABLE ' + table + ' ADD CONSTRAINT "' + key[1] + '" UNIQUE (' + ', '.join(value) + ');'

            constraints.append(unique_str)

    return constraints


def add_constraints(func, table_defs, schema, empty_tables, constraints_file):
    constraints = func(table_defs, schema, empty_tables)
    if constraints:
        with open(constraints_file, "a") as file:
            file.write("\n".join(constraints))


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
            s = file.read()
            include_tables = [line.strip() for line in s.splitlines()]

    tree = ET.parse(metadata_file)
    table_defs = tree.findall("table-def")
    schemas = set()
    for table_def in table_defs:
        table_schema = table_def.find('table-schema')
        schema = table_schema.text
        schemas.add(schema)

    msg = ''
    for schema in schemas:
        if not schema:
            file_name = 'constraints.sql'
        else:
            file_name = schema + '_constraints.sql'

        constraints_file = str(Path(dir_path, file_name))
        empty_tables = pw_ddl.get_empty_tables(table_defs, schema, include_tables)

        with open(constraints_file, "w") as file:
            if schema:
                file.write("-- Constraints for schema '" + schema + "': \n")

        add_constraints(pw_ddl.add_primary_keys, table_defs, schema, empty_tables, constraints_file)
        add_constraints(add_unique, table_defs, schema, empty_tables, constraints_file)
        add_constraints(pw_ddl.add_foreign_keys, table_defs, schema, empty_tables, constraints_file)

        msg = msg + "\nConstraints written to '" + constraints_file + "'"

    return msg[1:]


if __name__ == '__main__':
    print(main(sys.argv))
