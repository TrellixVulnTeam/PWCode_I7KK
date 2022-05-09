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


def get_primary_keys(table_defs, schema, empty_tables):
    pk_dict = {}
    pk_tables = []

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
            pk_dict[table_name.text] = sorted(pk_list)
            pk_tables.append(table_name.text)

    return pk_dict, pk_tables


def add_primary_keys(table_defs, schema, empty_tables):
    pk_dict, pk_tables = get_primary_keys(table_defs, schema, empty_tables)
    constraints = []

    for table in pk_tables:
        pk_list = sorted(pk_dict[table])
        fix_null_str = ''
        for p in pk_list:
            fix_null_str = fix_null_str + 'ALTER TABLE "' + table + '" ALTER COLUMN ' + p + ' SET NOT NULL; '

        pk_dict[table] = ', '.join(pk_list)
        constraints.append('\n' + fix_null_str + 'ALTER TABLE "' + table + '" ADD PRIMARY KEY(' + pk_dict[table] + ');')

    return constraints


def get_foreign_keys(table_defs, schema, empty_tables):
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

    return constraint_dict, fk_columns_dict, fk_ref_dict


def get_fk_str(constraint_dict, fk_columns_dict, fk_ref_dict, table, schema, alter=False):
    fk_str = ''
    if constraint_dict[table]:
        for s in [x for x in constraint_dict[table].split(',')]:
            constr, ref_table = s.split(':')

            ref_column_list = []
            for col in fk_columns_dict[constr]:
                ref_column_list.append(fk_ref_dict[table + ':' + col] + ':' + col)

            ref_s = source_s = ''
            for s in sorted(ref_column_list):
                ref, source = s.split(':')
                ref_s = ref_s + ', "' + ref + '"'
                source_s = source_s + ', "' + source + '"'

            if alter:
                if schema:
                    tbl = '\nALTER TABLE "' + schema + '"."' + table + '"'
                    ref_tbl = 'REFERENCES "' + schema + '"."' + ref_table + '"'
                else:
                    tbl = '\nALTER TABLE "' + table + '"'
                    ref_tbl = 'REFERENCES "' + ref_table + '"'
                fk_str = fk_str + tbl + ' ADD CONSTRAINT "' + constr + '" FOREIGN KEY (' + source_s[2:] + ') ' + ref_tbl + ' (' + ref_s[2:] + ');'
            else:
                fk_str = fk_str + ',\nCONSTRAINT "' + constr + '"\nFOREIGN KEY (' + source_s[2:] + ')\nREFERENCES "' + ref_table + '" (' + ref_s[2:] + ')'

    return fk_str


def add_foreign_keys(table_defs, schema, empty_tables):
    constraint_dict, fk_columns_dict, fk_ref_dict = get_foreign_keys(table_defs, schema, empty_tables)
    constraints = []

    for table_def in table_defs:
        if schema:
            table_schema = table_def.find('table-schema')
            if table_schema.text != schema:
                continue

        table_name = table_def.find('table-name')
        if table_name.text in empty_tables:
            continue

        fk_str = get_fk_str(constraint_dict, fk_columns_dict, fk_ref_dict, table_name.text, schema, True)
        if len(fk_str) > 0:
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
