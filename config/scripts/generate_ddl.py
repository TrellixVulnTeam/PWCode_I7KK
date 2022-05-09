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
from pathlib import Path
import xml.etree.ElementTree as ET
from argparse import ArgumentParser, SUPPRESS
from distutils.util import strtobool
from common.ddl import get_primary_keys, get_foreign_keys, get_fk_str, get_empty_tables


# TODO: Splitte ut kode som er delt mellom scriptene i en defs.py ?


# WAIT: Mangler denne for å ha alle i JDBC 4.0: SQLXML=2009
# -> må ha reelle data å teste det på først. Takler sqlwb det eller må det egen kode til?
# jdbc-id  iso-name               jdbc-name
jdbc_to_iso_data_type = {
    '-8': 'varchar',           # ROWID
    '-16': 'clob',             # LONGNVARCHAR
    '-15': 'varchar',          # NCHAR
    '-9': 'varchar',           # NVARCHAR
    '-7': 'boolean',           # BIT
    '-6': 'integer',           # TINYINT
    '-5': 'bigint',            # BIGINT
    '-4': 'blob',              # LONGVARBINARY
    '-3': 'blob',              # VARBINARY
    '-2': 'blob',              # BINARY
    '-1': 'clob',              # LONGVARCHAR
    '1': 'varchar',            # CHAR
    '2': 'numeric',            # NUMERIC
    '3': 'decimal',            # DECIMAL
    '4': 'integer',            # INTEGER
    '5': 'integer',            # SMALLINT
    '6': 'float',              # FLOAT
    '7': 'real',               # REAL
    '8': 'double precision',   # DOUBLE
    '12': 'varchar',           # VARCHAR
    '16': 'boolean',           # BOOLEAN
    '91': 'date',              # DATE
    '92': 'time',              # TIME
    '93': 'timestamp',         # TIMESTAMP
    '2004': 'blob',            # BLOB
    '2005': 'clob',            # CLOB
    '2011': 'clob',            # NCLOB
}


def get_ddl_columns(table_defs, schema, pk_dict, unique_dict):
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
        pk_list = []
        if table_name.text in pk_dict:
            pk_list = pk_dict[table_name.text]

        unique_list = []
        if table_name.text in unique_dict:
            unique_list = unique_dict[table_name.text]

        ddl_columns_list = []
        column_defs = table_def.findall("column-def")
        column_defs[:] = sorted(column_defs, key=lambda elem: int(elem.findtext('dbms-position')))
        for column_def in column_defs:
            column_name = column_def.find('column-name')

            java_sql_type = column_def.find('java-sql-type')
            dbms_data_size = column_def.find('dbms-data-size')

            iso_data_type = jdbc_to_iso_data_type[java_sql_type.text]
            if '()' in iso_data_type:
                iso_data_type = iso_data_type.replace('()', '(' + dbms_data_size.text + ')')

            column_text = '"' + column_name.text + '" ' + iso_data_type
            if column_name.text in pk_list or column_name.text in unique_list:
                column_text = column_text + ' NOT NULL'

            ddl_columns_list.append(column_text + ',')
        ddl_columns[table_name.text] = '\n'.join(ddl_columns_list)

    return ddl_columns


def get_unique_indexes(table_defs, schema, empty_tables):
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

    return unique_dict


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
        help='Show this help message and exit'
    )

    required.add_argument('-p', dest='path', type=str, help='Path of metadata.xml file', required=True)
    optional.add_argument('-c', dest='constraints', type=lambda x: bool(strtobool(x)), help='Include constraints (true/false)', default='False')
    optional.add_argument('-d', dest='drop', type=lambda x: bool(strtobool(x)), help='Drop existing table (true/false)', default='False')

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
            file_name = 'ddl.sql'
        else:
            file_name = schema + '_ddl.sql'

        ddl_file = os.path.join(dir_path, file_name)

        empty_tables = get_empty_tables(table_defs, schema)

        with open(ddl_file, "w") as file:
            if schema:
                file.write("-- DDL for schema '" + schema + "': \n")

        pk_dict, pk_tables = get_primary_keys(table_defs, schema, empty_tables)
        unique_dict = get_unique_indexes(table_defs, schema, empty_tables)
        ddl_columns = get_ddl_columns(table_defs, schema, pk_dict, unique_dict)

        if args.constraints:
            constraint_dict, fk_columns_dict, fk_ref_dict = get_foreign_keys(table_defs, schema, empty_tables)

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
            ddl = '\nCREATE TABLE "' + table_name.text + '"(\n' + ddl_columns[table_name.text][:-1]
            if args.constraints:
                pk_str = unique_str = fk_str = ''
                if table_name.text in pk_dict:
                    pk_str = ',\nPRIMARY KEY (' + ', '.join(pk_dict[table_name.text]) + ')'

                unique_constraints = {key: val for key, val in unique_dict.items() if key[0] == table_name.text}
                if unique_constraints:
                    for key, value in unique_constraints.items():
                        unique_str = unique_str + ',\nCONSTRAINT ' + key[1] + ' UNIQUE (' + ', '.join(value) + ')'

                fk_str = get_fk_str(constraint_dict, fk_columns_dict, fk_ref_dict, table_name.text, schema)
                ddl = ddl + pk_str + unique_str + fk_str

            if args.drop:
                ddl = '\nDROP TABLE IF EXISTS "' + table_name.text + '"; ' + ddl

            with open(ddl_file, "a") as file:
                file.write(ddl + ');\n')

        msg = msg + "\nDDL written to '" + ddl_file + "'"

    return msg[1:]


if __name__ == '__main__':
    print(main(sys.argv))
