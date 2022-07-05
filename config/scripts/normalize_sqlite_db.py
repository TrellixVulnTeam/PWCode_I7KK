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

from loguru import logger
import sys
from argparse import ArgumentParser, SUPPRESS
from pathlib import Path
from sqlite_utils import Database
from importlib.metadata import version
from platform import python_version
import xml.etree.ElementTree as ET
from specific_import import import_file
pw_log = import_file(str(Path(Path(__file__).resolve().parents[2], 'bin', 'common', 'log.py')))
pw_file = import_file(str(Path(Path(__file__).resolve().parents[2], 'bin', 'common', 'file.py')))


def xstr(s):
    if s is None:
        return ''
    else:
        return str(s)


def index_sqlite_foreign_keys(db):
    logger.info('Adding indexes to any foreign keys without...')
    db.index_foreign_keys()


def show_versions(db):
    sqlite_version = '.'.join(map(str, db.sqlite_version))
    print('\n'.join((('sqlite version: ' + sqlite_version,
                      'sqlite_utils version: ' + version('sqlite_utils'),
                      'python version: ' + python_version(),
                      ''))))


def fix_date_columns(db, date_columns):
    print('Gjør ferdig')


def get_date_columns(table_defs, schema):
    date_columns = {}

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

            java_sql_type = column_def.find('java-sql-type')
            if java_sql_type.text in ['91', '92', '93']:
                ddl_columns_list.append(column_name.text)

        if ddl_columns_list:
            date_columns[table_name.text] = ddl_columns_list

    return date_columns


# def get_date_columns(db, table_columns, table_names):
#     print('get_date_columns not implemented')
#     # TODO: MÅ først legge inn lesing av metadata.xml fil
#     # for table_name in table_names:
#     #     for column in table_columns[table_name]:
#     #         print(column.name)


def drop_check(db, table_names, columns, foreign_keys):
    # If problem with any column, none of them can be dropped
    drop = True
    for column in columns:
        for key in foreign_keys:
            if column.name == key.column:
                if key.other_table not in table_names:
                    drop = False

    return drop


def get_empty_columns(table, columns, count):
    empty_columns = []
    for column in columns:
        empty_count = table.count_where("ifnull(" + column.name + ", '')=''")
        if count == empty_count:
            empty_columns.append(column.name)

    return empty_columns


def drop_foreign_keys_on_table(table, foreign_keys):
    for key in foreign_keys:
        table.transform(drop_foreign_keys=(key.other_table))


def get_sqlite_tables_remove_empty(db, include_tables):
    table_names = db.table_names()
    if 'sqlite_sequence' in table_names:
        table_names.remove('sqlite_sequence')

    table_columns = {}
    keep_table = True
    for table_name in table_names:

        if include_tables:
            if table_name not in include_tables:
                continue

        logger.info('Checking table ' + table_name + '...')
        table = db[table_name]
        foreign_keys = table.foreign_keys

        count = table.count
        columns = table.columns  # list of named tuples (name, type, notnull, default_value, is_pk)
        if count == 0:
            can_drop = drop_check(db, table_names, columns, foreign_keys)
            if can_drop:
                logger.info('Removing empty table ' + table_name + ' and any foreign keys referencing it')
                drop_foreign_keys_on_table(table, foreign_keys)
                table.drop(ignore=True)
                keep_table = False
            else:
                logger.info('Empty table ' + table_name + ' references missing table(s) and could not be dropped')

        else:
            empty_columns = get_empty_columns(table, columns, count)
            if empty_columns:
                can_drop = drop_check(db, table_names, columns, foreign_keys)
                if can_drop:
                    logger.warning('Removing empty columns in ' + table_name + ' and any foreign keys referencing it')
                    drop_foreign_keys_on_table(table, foreign_keys)
                    table.transform(drop={','.join(empty_columns)})
                else:
                    logger.warning('Empty columns in table ' + table_name + ' references missing table(s) and could not be dropped')
            else:
                logger.info('No empty columns. Nothing done')

        if keep_table:
            table_columns[table_name] = columns

    logger.info('All empty tables removed')
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

    required.add_argument('-d', dest='db_path', type=str, help='Path of sqlite database file', required=True)
    required.add_argument('-x', dest='xml_path', type=str, help='Path of metadata.xml file', required=True)
    required.add_argument('-s', dest='schema', type=str, help='Name of schema in metadata.xml file', required=True)
    optional.add_argument('-l', dest='table_list', type=str, help='Path of file with list of tables to include.')

    return parser.parse_args()


def main(argv):
    # WAIT: Sjekk konflikter på base hvis data kopiert inn først med PRAGMA foreign_keys=OFF
    # -> sats på det heller enn å legge til fk i etterkant da det er mindre sjanse for korrupt database
    # TODO: legg inn arg for om ta backup av sqlite fil før kjører script
    log_file = pw_file.uniquify(Path(Path(__file__).resolve().parents[1], 'tmp', Path(__file__).stem + '.log'))
    pw_log.configure_logging(log_file)

    msg = ''
    args = parse_arguments(argv)
    print('')
    for a in args.__dict__:
        print(str(a) + ": " + str(args.__dict__[a]))

    metadata_file = args.xml_path
    db_file = args.db_path
    table_list = args.table_list

    files = [metadata_file, db_file]
    if table_list:
        files.append(table_list)

    for file_path in files:
        if not Path(file_path).is_file():
            return "File '" + str(Path(file_path).name) + "' does not exist. Exiting..."

    include_tables = []
    if table_list:
        with open(table_list) as file:
            s = file.read()
            include_tables = [line.strip() for line in s.splitlines()]

    tree = ET.parse(metadata_file)
    table_defs = tree.findall("table-def")

    schemas = set()
    for table_def in table_defs:
        table_schema = table_def.find('table-schema')
        schema = table_schema.text
        schemas.add(xstr(schema))

    if args.schema not in schemas:
        return "Schema '" + args.schema + "' does not exist in metadata file. Exiting..."

    db = Database(db_file)
    table_columns = get_sqlite_tables_remove_empty(db, include_tables)
    show_versions(db)

    date_columns = get_date_columns(table_defs, schema)
    for table, columns in date_columns.items():
        print(table, ':', columns)

    fix_date_columns(db, date_columns)

    # for x in date_columns:
    #     print(x)

    # logger.info('Optimizing db file...')
    # db.vacuum()
    index_sqlite_foreign_keys(db)  # TODO: Bør gjøres etter at keys, kolonner og tabeller fjernet
    # get_date_columns(db, table_columns, sqlite_tables)

    logger.success('Done')

    # https://sqlite-utils.datasette.io/en/latest/index.html

    # TODO: test for foreign keys:
    # https: // github.com/simonw/sqlite-utils/issues/2
    # db["books"].add_foreign_key("author_id", "authors", "id", ignore=True) # Ignore if already exists
    # Adding multiple foreign keys at once
    # db.add_foreign_keys([
    # ("dogs", "breed_id", "breeds", "id"),
    # ("dogs", "home_town_id", "towns", "id")
    # ])
    # https: // github.com/simonw/sqlite-utils/issues/335

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

    return msg


if __name__ == '__main__':
    print(main(sys.argv))
