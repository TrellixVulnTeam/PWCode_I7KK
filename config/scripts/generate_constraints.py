# Copyright(C) 2021 Morten Eek

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


import os
from pathlib import Path
import xml.etree.ElementTree as ET


def add_primary_keys(table_defs, schema):
    constraints = []
    pk_dict = {}

    for table_def in table_defs:
        table_schema = table_def.find('table-schema')
        if table_schema.text != schema:
            continue

        table_name = table_def.find("table-name")

        pk_list = []
        column_defs = table_def.findall("column-def")
        for column_def in column_defs:
            column_name = column_def.find('column-name')
            primary_key = column_def.find('primary-key')

            if primary_key.text == 'true':
                pk_list.append(column_name.text)

        pk_dict[table_name.text] = ', '.join(sorted(pk_list))

        constraints.append('\nALTER TABLE ' + table_name.text + ' ADD PRIMARY KEY(' + pk_dict[table_name.text] + ');')

    return constraints


def add_unique(table_defs, schema):
    constraints = []
    unique_dict = {}

    for table_def in table_defs:
        table_schema = table_def.find('table-schema')
        if table_schema.text != schema:
            continue

        table_name = table_def.find("table-name")
        index_defs = table_def.findall("index-def")

        for index_def in index_defs:
            unique = index_def.find('unique')
            primary_key = index_def.find('primary-key')
            index_name = index_def.find('name')

            unique_col_list = []
            if unique.text == 'true' and primary_key.text == 'false':
                index_column_names = index_def.findall("column-list/column")
                for index_column_name in index_column_names:
                    unique_constraint_name = index_column_name.attrib['name']
                    unique_col_list.append(unique_constraint_name)
                unique_dict[(table_name.text, index_name.text)] = sorted(unique_col_list)

        unique_str = '\n'
        unique_constraints = {key: val for key, val in unique_dict.items() if key[0] == table_name.text}
        if unique_constraints:
            for key, value in unique_constraints.items():
                unique_str = unique_str + '\nALTER TABLE ' + table_name.text + ' ADD CONSTRAINT ' + key[1] + ' UNIQUE (' + ', '.join(value) + ');'

            constraints.append(unique_str + '\n')

    return constraints


def add_foreign_keys(table_defs, schema):
    constraints = []
    constraint_dict = {}
    fk_columns_dict = {}
    fk_ref_dict = {}
    for table_def in table_defs:
        table_schema = table_def.find('table-schema')
        if table_schema.text != schema:
            continue

        table_name = table_def.find("table-name")
        constraint_set = set()
        foreign_keys = table_def.findall("foreign-keys/foreign-key")

        for foreign_key in foreign_keys:
            tab_constraint_name = foreign_key.find("constraint-name")

            fk_references = foreign_key.findall('references')
            for fk_reference in fk_references:
                tab_ref_table_name = fk_reference.find("table-name")
                constraint_set.add(tab_constraint_name.text + ':' + tab_ref_table_name.text)

            source_column_set = set()
            source_columns = foreign_key.findall('source-columns')

            for source_column in source_columns:
                source_column_names = source_column.findall('column')

                for source_column_name in source_column_names:
                    source_column_set.add(source_column_name.text)

            if not len(source_column_set) == 0:
                fk_columns_dict.update({tab_constraint_name.text: source_column_set})

        constraint_dict[table_name.text] = ','.join(constraint_set)
        column_defs = table_def.findall("column-def")
        column_defs[:] = sorted(column_defs, key=lambda elem: int(elem.findtext('dbms-position')))

        for column_def in column_defs:
            column_name = column_def.find('column-name')
            col_references = column_def.findall('references')

            for col_reference in col_references:
                ref_column_name = col_reference.find('column-name')
                fk_ref_dict[table_name.text + ':' + column_name.text] = ref_column_name.text

    for table_def in table_defs:
        table_schema = table_def.find('table-schema')
        if table_schema.text != schema:
            continue

        table_name = table_def.find("table-name")

        fk_str = ''
        if constraint_dict[table_name.text]:
            for s in [x for x in constraint_dict[table_name.text].split(',')]:
                constr, ref_table = s.split(':')
                ref_column_list = []
                source_column_list = fk_columns_dict[constr]

                for col in source_column_list:
                    ref_column_list.append(fk_ref_dict[table_name.text + ':' + col] + ':' + col)

                ref_column_list = sorted(ref_column_list)
                ref_s = ''
                source_s = ''
                for s in ref_column_list:
                    ref, source = s.split(':')
                    ref_s = ref_s + ', ' + ref
                    source_s = source_s + ', ' + source
                ref_s = ref_s[2:]
                source_s = source_s[2:]
                fk_str = fk_str + '\nALTER TABLE ' + table_name.text + ' ADD CONSTRAINT ' + constr + ' FOREIGN KEY (' + source_s + ') REFERENCES ' + ref_table + ' (' + ref_s + ')'

            constraints.append(fk_str)

    return constraints


def add_constraints(func, table_defs, schema, constraints_file):
    constraints = func(table_defs, schema)
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
        constraints_file = os.path.join(script_dir_path, schema + '_constraints.sql')

        with open(constraints_file, "w") as file:
            file.write("-- Constraints for schema '" + schema + "': \n")

        add_constraints(add_primary_keys, table_defs, schema, constraints_file)
        add_constraints(add_unique, table_defs, schema, constraints_file)
        add_constraints(add_foreign_keys, table_defs, schema, constraints_file)

        msg = msg + "\nConstraints for schema '" + schema + "' written to '" + constraints_file + "'"

    return msg[1:]


if __name__ == '__main__':
    print(main())
