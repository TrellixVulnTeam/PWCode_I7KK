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

import petl as etl


def get_db_type(key_column, value_column, Key_value):  # WAIT: Mangler SQLXML=2009 for å ha alle i JDBC 4.0
    db_types = [['jdbc_no', 'jdbc_name', 'iso', 'sqlite'],
                [-8, 'rowid', 'varchar', 'varchar'],
                [-16, 'longnvarchar', 'clob', 'clob'],
                [-15, 'nchar', 'varchar', 'varchar'],
                [-9, 'nvarchar', 'varchar', 'varchar'],
                [-7, 'bit', 'boolean', 'boolean'],
                [-6, 'tinyint', 'integer', 'integer'],
                [-5, 'bigint', 'bigint', 'bigint'],
                [-4, 'longvarbinary', 'blob', 'blob'],
                [-3, 'varbinary', 'blob', 'blob'],
                [-2, 'binary', 'blob', 'blob'],
                [-1, 'longvarchar', 'clob', 'clob'],
                [1, 'char', 'varchar', 'varchar'],
                [2, 'numeric', 'numeric', 'numeric'],
                [3, 'decimal', 'decimal', 'decimal'],
                [4, 'integer', 'integer', 'integer'],
                [5, 'smallint', 'integer', 'integer'],
                [6, 'float', 'float', 'float'],
                [7, 'real', 'real', 'real'],
                [8, 'double', 'double precision', 'double precision'],
                [12, 'varchar', 'varchar', 'varchar'],
                [16, 'boolean', 'boolean', 'boolean'],
                [91, 'date', 'date', 'date'],
                [92, 'time', 'time', 'text'],
                [93, 'timestamp', 'timestamp', 'text'],
                [2004, 'blob', 'blob', 'blob'],
                [2005, 'clob', 'clob', 'clob'],
                [2011, 'nclob', 'clob', 'clob'],
                ]

    return etl.lookup(db_types, key_column, value_column)[Key_value][0]


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


def get_empty_tables(table_defs, schema, include_tables=[]):
    empty_tables = []
    include_dict = {}

    if include_tables:
        include_dict = dict([s.split(':') for s in include_tables])

    for table_def in table_defs:
        if schema:
            table_schema = table_def.find('table-schema')
            if table_schema.text != schema:
                continue

        disposed = table_def.find('disposed')
        table_name = table_def.find('table-name')
        if disposed:
            if disposed.text == 'true':
                empty_tables.append(table_name.text)
        elif include_tables:
            if table_name.text not in include_dict or include_dict[table_name.text] == '0':
                empty_tables.append(table_name.text)

    return empty_tables
