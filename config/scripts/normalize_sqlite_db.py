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

from genericpath import exists
import os
import sys
from argparse import ArgumentParser, SUPPRESS
from pathlib import Path
from sqlite_utils import Database
import xml.etree.ElementTree as ET
# from common.ddl import get_empty_tables
# from distutils.util import strtobool


def index_sqlite_foreign_keys(db):
    print('Adding indexes to any foreign keys without...')
    db.index_foreign_keys()


def show_sqlite_version(db):
    sqlite_version = '.'.join(map(str, db.sqlite_version))
    print('sqlite_version: ' + sqlite_version)


def get_date_columns(db, table_columns, table_names):
    print('get_date_columns not implemented')
    # for table_name in table_names:
    #     for column in table_columns[table_name]:
    #         print(column.name)


def get_sqlite_tables_remove_empty(db):
    table_columns = {}
    table_names = db.table_names()
    table_names.remove('sqlite_sequence')
    for table_name in table_names:
        table = db[table_name]
        foreign_keys = table.foreign_keys

        count = table.count
        if count == 0:
            for key in foreign_keys:
                table.transform(drop_foreign_keys=(key.other_table))

            print('Removing empty table ' + table_name + ' and any foreign keys referencing it')
            table.drop(ignore=True)
        else:
            columns = table.columns  # list of named tuples (name, type, notnull, default_value, is_pk)
            for column in columns:
                empty_count = table.count_where("ifnull(" + column.name + ", '')=''")
                if count == empty_count:
                    print(' '.join(('Removing empty column ', column.name, ' in table ',
                                    table_name, ' and any foreign keys referencing it')))

                    for key in foreign_keys:
                        if column == key.column:
                            if not db[key.other_table].exists():  # Fix for cases where table dropped but fk remains -> TODO: Virker ikke alltid
                                print('Table: ' + key.other_table)
                                print('Column: ' + key.other_column)
                                with db.conn:
                                    db[key.other_table].create({key.other_column: column.type})
                                with db.conn:
                                    table.transform(drop_foreign_keys=(key.other_table))
                                    # db[key.other_table].drop(ignore=True)

                            table.transform(drop_foreign_keys=(key.other_table))
                            db[key.other_table].transform(drop={key.other_column})

                    columns.remove(column)  # TODO: Virker ikke hvis koblet til kolonne i tabell som ikke finnes lenger. Løse hvordan?
                    table.transform(drop={column.name})

            table_columns[table_name] = columns

    print('All empty tables removed')
    return table_columns


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

    required.add_argument('-x', dest='xml_path', type=str, help='Path of metadata.xml file', required=True)
    required.add_argument('-d', dest='db_path', type=str, help='Path of sqlite database file', required=True)
    optional.add_argument('-l', dest='table_list', type=str, help='Path of file with list of tables to include.')

    return parser.parse_args()


def main(argv):
    # WAIT: Sjekk konflikter på base hvis data kopiert inn først med PRAGMA foreign_keys=OFF
    # -> sats på det heller enn å legge til fk i etterkant da det er mindre sjanse for korrupt database
    # TODO: legg inn arg for om ta backup av sqlite fil før kjører script
    msg = ''
    args = parse_arguments(argv)
    for a in args.__dict__:
        print(str(a) + ": " + str(args.__dict__[a]))

    metadata_file = args.xml_path
    db_file = args.db_path

    for file_path in [metadata_file, db_file]:
        if not os.path.isfile(file_path):
            print(file_path)
            return "File '" + str(Path(file_path).name) + "' does not exist. Exiting..."

    # dir_path = Path(metadata_file).resolve().parents[0]
    db = Database(db_file)
    show_sqlite_version(db)

    table_columns = get_sqlite_tables_remove_empty(db)
    # table_columns = get_sqlite_columns_remove_empty(db, sqlite_tables)
    return 'test_kk'
    index_sqlite_foreign_keys(db)  # TODO: Bør gjøres etter at keys, kolonner og tabeller fjernet
    # get_date_columns(db, table_columns, sqlite_tables)

    # Endte kolonne name til upper i tabell dogs
    # db["dogs"].convert("name", lambda value: value.upper())
    # Samme for kun noen rader
    # db["dogs"].convert("name", lambda v: v.upper(), where="id > :id", where_args={"id": 20})
    # Samme men skriv til ny kolonne
    # db["dogs"].convert("name", lambda value: value.upper(), output="name_upper", output_type=TEXT)
    # For flere kolonner
    # db["dogs"].convert(["name", "twitter"], lambda value: value.upper())
    # Add column
    # db["dogs"].add_column("instagram", TEXT)

    # Mapping python til sql:
    # float: "FLOAT"
    # int: "INTEGER"
    # bool: "INTEGER"
    # str: "TEXT"
    # bytes: "BLOB"
    # datetime.datetime: "TEXT"
    # datetime.date: "TEXT"
    # datetime.time: "TEXT"

    # Legg til colonne som er foreign key
    # db["dogs"].add_column("species_id", fk="species", fk_col="ref")
    # print(db.schema)
    # Convert the 'age' column to an integer, and 'weight' to a float
    # table.transform(types={"age": int, "weight": float})
    # Rename column 'age' to 'initial_age':
    # table.transform(rename={"age": "initial_age"})
    # Make the 'age' and 'weight' columns NOT NULL
    # table.transform(not_null={"age", "weight"})
    # 'age' is NOT NULL but we want to allow NULL:
    # table.transform(not_null={"age": False})
    # Check if table exists
    # db["PlantType"].exists()
    # Registrer UDF og replace atuo slik at rvt oppdatert funksjonskode brukes
    # @db.register_function(deterministic=True, replace=True)
    # def reverse_string(s):
    #     return s[::-1]

    include_tables = []
    if args.table_list:
        with open(args.table_list) as file:
            include_tables = file.read().splitlines()

    # tree = ET.parse(metadata_file)
    # table_defs = tree.findall("table-def")
    # schemas = set()
    # for table_def in table_defs:
    #     table_schema = table_def.find('table-schema')
    #     schema = table_schema.text
    #     schemas.add(schema)

    return msg[1:]


if __name__ == '__main__':
    print(main(sys.argv))
