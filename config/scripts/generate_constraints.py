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


def add_primary_keys(table_defs, schema, empty_tables):
    constraints = []
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

        if schema:
            table = '"' + schema + '"."' + table_name.text + '"'
        else:
            table = '"' + table_name.text + '"'

        pk_list = []
        column_defs = table_def.findall('column-def')
        for column_def in column_defs:
            primary_key = column_def.find('primary-key')

            if primary_key.text == 'true':
                column_name = column_def.find('column-name')
                pk_list.append('"' + column_name.text + '"')

        pk_dict[table_name.text] = ', '.join(sorted(pk_list))
        constraints.append('\nALTER TABLE ' + table + ' ADD PRIMARY KEY(' + pk_dict[table_name.text] + ');')

    return constraints


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
                unique_str = unique_str + '\nALTER TABLE ' + table + ' ADD CONSTRAINT "' + key[1] + '" UNIQUE (' + ', '.join(value) + ');'

            constraints.append(unique_str + '\n')

    return constraints


def add_foreign_keys(table_defs, schema, empty_tables):
    constraints = []
    constraint_dict = {}
    fk_columns_dict = {}
    fk_ref_dict = {}
    for table_def in table_defs:
        if schema:
            table_schema = table_def.find('table-schema')
            if table_schema.text != schema:
                continue

        table_name = table_def.find('table-name')
        if table_name.text in empty_tables:
            continue

        constraint_set = set()
        foreign_keys = table_def.findall('foreign-keys/foreign-key')

        for foreign_key in foreign_keys:
            ref_table_name = foreign_key.find('references/table-name')
            if ref_table_name.text in empty_tables:
                continue

            tab_constraint_name = foreign_key.find('constraint-name')
            constraint_set.add(tab_constraint_name.text + ':' + ref_table_name.text)

            source_column_set = set()
            source_columns = foreign_key.findall('source-columns')

            for source_column in source_columns:
                source_column_names = source_column.findall('column')

                for source_column_name in source_column_names:
                    source_column_set.add(source_column_name.text)

            if not len(source_column_set) == 0:
                fk_columns_dict.update({tab_constraint_name.text: source_column_set})

        constraint_dict[table_name.text] = ','.join(constraint_set)
        column_defs = table_def.findall('column-def')
        column_defs[:] = sorted(column_defs, key=lambda elem: int(elem.findtext('dbms-position')))

        for column_def in column_defs:
            column_name = column_def.find('column-name')
            col_references = column_def.findall('references')

            for col_reference in col_references:
                ref_column_name = col_reference.find('column-name')
                fk_ref_dict[table_name.text + ':' + column_name.text] = ref_column_name.text

    for table_def in table_defs:
        if schema:
            table_schema = table_def.find('table-schema')
            if table_schema.text != schema:
                continue

        table_name = table_def.find('table-name')
        if table_name.text in empty_tables:
            continue

        fk_str = ''
        if constraint_dict[table_name.text]:
            for s in [x for x in constraint_dict[table_name.text].split(',')]:
                constr, ref_table = s.split(':')

                if ref_table in empty_tables:
                    continue

                ref_column_list = []
                source_column_list = fk_columns_dict[constr]

                for col in source_column_list:
                    ref_column_list.append(fk_ref_dict[table_name.text + ':' + col] + ':' + col)

                ref_column_list = sorted(ref_column_list)
                ref_s = ''
                source_s = ''
                for s in ref_column_list:
                    ref, source = s.split(':')
                    ref_s = ref_s + ', "' + ref + '"'
                    source_s = source_s + ', "' + source + '"'
                ref_s = ref_s[2:]
                source_s = source_s[2:]
                if schema:
                    table = '"' + schema + '"."' + table_name.text + '"'
                    ref_table = '"' + schema + '"."' + ref_table + '"'
                else:
                    table = '"' + table_name.text + '"'
                    ref_table = '"' + ref_table + '"'

                # WAIT: Test å legge inn støtte for constraint på tvers av skjemaer

                fk_str = fk_str + '\nALTER TABLE ' + table + ' ADD CONSTRAINT "' + constr + '" FOREIGN KEY (' + source_s + ') REFERENCES ' + ref_table + ' (' + ref_s + ');'

            if fk_str:
                constraints.append(fk_str)

    return constraints


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


def add_constraints(func, table_defs, schema, empty_tables, constraints_file):
    constraints = func(table_defs, schema, empty_tables)
    if constraints:
        with open(constraints_file, "a") as file:
            file.write("\n".join(constraints))


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
            file_name = 'constraints.sql'
        else:
            file_name = schema + '_constraints.sql'

        constraints_file = os.path.join(script_dir_path, file_name)

        empty_tables = get_empty_tables(table_defs, schema)

        with open(constraints_file, "w") as file:
            if schema:
                file.write("-- Constraints for schema '" + schema + "': \n")

        add_constraints(add_primary_keys, table_defs, schema, empty_tables, constraints_file)
        add_constraints(add_unique, table_defs, schema, empty_tables, constraints_file)
        add_constraints(add_foreign_keys, table_defs, schema, empty_tables, constraints_file)

        msg = msg + "\nConstraints written to '" + constraints_file + "'"

    return msg[1:]


if __name__ == '__main__':
    print(main())
