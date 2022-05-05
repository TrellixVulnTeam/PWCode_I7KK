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

# Only tested against H2-databases

import os
import sys
from argparse import ArgumentParser, SUPPRESS
from distutils.util import strtobool
from pathlib import Path
import xml.etree.ElementTree as ET


# TODO: Splitte ut kode som er delt mellom scriptene i en defs.py ?

def get_columns(table_defs, schema, empty_tables, quote):  # TODO: Arg her for om tødler rundt eller ikke
    # TODO: Tilpass denne til det som trengs for wbcopy
    ddl_columns = {}

    for table_def in table_defs:
        table_schema = table_def.find('table-schema')
        if table_schema is not None:
            if table_schema.text is not None and len(schema) > 0:
                if table_schema.text != schema:
                    continue

        disposed = table_def.find("disposed")
        if disposed is not None:
            if disposed.text == "true":
                continue

        table_name = table_def.find("table-name")
        ddl_columns_list = []
        column_defs = table_def.findall("column-def")
        column_defs[:] = sorted(column_defs, key=lambda elem: int(elem.findtext('dbms-position')))
        for column_def in column_defs:
            column_name = column_def.find('column-name')
            if quote:
                ddl_columns_list.append(column_name.text + ',')
            else:
                ddl_columns_list.append(column_name.text + ',')
        ddl_columns[table_name.text] = ''.join(ddl_columns_list)

    return ddl_columns


def get_empty_tables(table_defs, schema):
    empty_tables = []
    for table_def in table_defs:
        if schema:
            table_schema = table_def.find('table-schema')
            if table_schema.text != schema:
                continue

        disposed = table_def.find('disposed')
        if disposed:
            if disposed.text == 'true':
                table_name = table_def.find('table-name')
                empty_tables.append(table_name.text)

    return empty_tables


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
    optional.add_argument('-q', dest='quote', type=lambda x: bool(strtobool(x)), help='Quote fields (true/false)', default='True')

    return parser.parse_args()


def main(argv):
    args = parse_arguments(argv)
    for a in args.__dict__:
        print(str(a) + ": " + str(args.__dict__[a]))

    metadata_file = args.path
    dir_path = Path(metadata_file).resolve().parents[0]

    if not os.path.isfile(metadata_file):
        return "No 'metada.xml' file in script-directory. Exiting..."

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
            file_name = 'wbcopy.sql'
        else:
            file_name = schema + '_wbcopy.sql'

        wbcopy_file = os.path.join(dir_path, file_name)
        empty_tables = get_empty_tables(table_defs, schema)
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

            disposed = table_def.find("disposed")
            if disposed is not None:
                if disposed.text == "true":
                    continue

            table_name = table_def.find("table-name")
            source_query = ' '.join((
                'SELECT',
                columns[table_name.text][:-1],
                'FROM',
                table_name.text,
            ))

            copy_data_str = "WbCopy -targetProfile=" + args.target + " -targetTable=" + table_name.text + " -sourceQuery=" + source_query + ";"

            with open(wbcopy_file, "a") as file:
                file.write("\n\n" + copy_data_str)

        msg = msg + "\nDDL written to '" + wbcopy_file + "'"

    return msg[1:]


if __name__ == '__main__':
    print(main(sys.argv))
