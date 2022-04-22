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
from pathlib import Path
import xml.etree.ElementTree as ET


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
                # TODO: Var blitt nullable på noen som så skulle blir pk med annet script... Ser ut til å gjelde bare for tomme tabeller
                column_text = column_text + ' NOT NULL'

            ddl_columns_list.append(column_text + ',')
        ddl_columns[table_name.text] = '\n'.join(ddl_columns_list)

    return ddl_columns


def get_primary_keys(table_defs, schema, empty_tables):
    pk_dict = {}

    for table_def in table_defs:
        if schema:
            table_schema = table_def.find('table-schema')
            if table_schema.text != schema:
                continue

        primary_key_name = table_def.find('primary-key-name')
        if not primary_key_name.text:
            continue

        table_name = table_def.find("table-name")
        if table_name.text in empty_tables:
            continue

        pk_list = []
        column_defs = table_def.findall('column-def')
        for column_def in column_defs:
            primary_key = column_def.find('primary-key')

            if primary_key.text == 'true':
                column_name = column_def.find('column-name')
                pk_list.append('"' + column_name.text + '"')

        if pk_list:
            pk_dict[table_name.text] = pk_list

    return pk_dict


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


def main():
    script_dir_path = Path(__file__).resolve().parents[0]
    metadata_file = os.path.join(script_dir_path, 'metadata.xml')

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

        ddl_file = os.path.join(script_dir_path, file_name)

        empty_tables = get_empty_tables(table_defs, schema)

        with open(ddl_file, "w") as file:
            if schema:
                file.write("-- DDL for schema '" + schema + "': \n")

        pk_dict = get_primary_keys(table_defs, schema, empty_tables)
        unique_dict = get_unique_indexes(table_defs, schema, empty_tables)
        ddl_columns = get_ddl_columns(table_defs, schema, pk_dict, unique_dict)

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
            ddl = '\nCREATE TABLE "' + table_name.text + '"\n(\n' + ddl_columns[table_name.text][:-1] + '\n);'
            # ddl = 'DROP TABLE IF EXISTS "' + table_name.text + '"; ' + ddl

            with open(ddl_file, "a") as file:
                file.write("\n\n" + ddl)

        msg = msg + "\nDDL written to '" + ddl_file + "'"

    return msg[1:]


if __name__ == '__main__':
    print(main())
