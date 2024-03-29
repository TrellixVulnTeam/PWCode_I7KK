#! python3

# Copyright (C) 2021 Morten Eek

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
import pathlib
import sys
if os.name == "posix":
    import xml.etree.ElementTree as ET
import fileinput
from toposort import toposort_flatten
from tempfile import NamedTemporaryFile
import shutil
import csv
import petl as etl
from petl.util.base import Table
from petl.compat import text_type
from functools import reduce
from common.xml import merge_xml_element

csv.field_size_limit(sys.maxsize)


def normalize_header(table, illegal_v):
    return NormalizedHeaderView(table, illegal_v)


class NormalizedHeaderView(Table):
    def __init__(self, table, illegal_v):
        self.table = table
        self.illegal_v = illegal_v

    def __iter__(self):
        it = iter(self.table)
        hdr = next(it)
        outhdr = tuple((text_type(normalize_name(f, self.illegal_v))) for f in hdr)
        yield outhdr
        for row in it:
            yield row


# http://www.docjar.com/html/api/java/sql/Types.java.html
# TODO: Test for XML:
# The only way to retrieve and update XMLType columns using SQL Workbench/J is to cast the columns to a CLOB
# value e.g. CAST(xml_column AS CLOB) or to_clob(xml_column)
#
# Mangler disse for alle i JDBC 4.0: ROWID=-8 og SQLXML=2009
# jdbc-id  iso-name             jdbc-name
jdbc_to_iso_data_type = {
    '-16': 'text',              # LONGNVARCHAR
    '-15': 'varchar()',         # NCHAR
    '-9': 'varchar()',          # NVARCHAR
    '-7': 'varchar(5)',         # BIT
    '-6': 'integer',            # TINYINT
    '-5': 'bigint',             # BIGINT
    '-4': 'text',               # LONGVARBINARY
    '-3': 'text',               # VARBINARY
    '-2': 'text',               # BINARY
    '-1': 'text',               # LONGVARCHAR
    '1': 'varchar()',           # CHAR
    '2': 'numeric',             # NUMERIC  # WAIT: Se xslt for ekstra nyanser på denne
    '3': 'decimal',             # DECIMAL  # WAIT: Se xslt for ekstra nyanser på denne
    '4': 'integer',             # INTEGER
    '5': 'integer',             # SMALLINT
    '6': 'float',               # FLOAT
    '7': 'real',                # REAL
    '8': 'double precision',    # DOUBLE
    '12': 'varchar()',          # VARCHAR
    '16': 'varchar(5)',         # BOOLEAN
    '91': 'date',               # DATE
    '92': 'time',               # TIME
    '93': 'timestamp',          # TIMESTAMP
    '2004': 'text',             # BLOB
    '2005': 'text',             # CLOB
    '2011': 'text',             # NCLOB
}

# jdbc-id  ora-ctl-name                         jdbc-name
jdbc_to_ora_ctl_data_type = {
    '-16': 'CHAR(1000000)',                     # LONGNVARCHAR # WAIT: Finn absolutte maks som kan brukes
    '-15': 'CHAR()',                            # NCHAR
    '-9': 'CHAR()',                             # NVARCHAR
    '-7': 'CHAR(5)',                            # BIT
    '-6': 'INTEGER EXTERNAL',                   # TINYINT
    '-5': 'INTEGER EXTERNAL',                   # BIGINT
    '-4': 'CHAR(1000000)',                      # LONGVARBINARY
    '-3': 'CHAR(1000000)',                      # VARBINARY
    '-2': 'CHAR(1000000)',                      # BINARY
    '-1': 'CHAR(1000000)',                      # LONGVARCHAR
    '1': 'CHAR()',                              # CHAR
    '2': 'DECIMAL EXTERNAL',                    # NUMERIC  # TODO: Se xslt for ekstra nyanser på denne
    '3': 'DECIMAL EXTERNAL',                    # DECIMAL  # TODO: Se xslt for ekstra nyanser på denne
    '4': 'INTEGER EXTERNAL',                    # INTEGER
    '5': 'INTEGER EXTERNAL',                    # SMALLINT
    '6': 'FLOAT EXTERNAL',                      # FLOAT
    '7': 'DECIMAL EXTERNAL',                    # REAL
    '8': 'DECIMAL EXTERNAL',                    # DOUBLE
    '12': 'CHAR()',                             # VARCHAR
    '16': 'CHAR(5)',                            # BOOLEAN
    '91': 'DATE "YYYY-MM-DD"',                  # DATE
    '92': 'TIMESTAMP',                          # TIME
    '93': 'TIMESTAMP "YYYY-MM-DD HH24:MI:SS"',  # TIMESTAMP
    '2004': 'CHAR(1000000)',                    # BLOB
    '2005': 'CHAR(1000000)',                    # CLOB
    '2011': 'CHAR(1000000)',                    # NCLOB
}


def pwb_replace_in_file(file_path, search_text, new_text):
    with fileinput.input(file_path, inplace=True) as f:
        for line in f:
            new_line = line.replace(search_text, new_text)
            print(new_line, end='')


def pwb_lower_dict(d):
    new_dict = dict((k.lower(), v.lower()) for k, v in d.items())
    return new_dict


def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def get_empty_tables(table_defs, schema):
    empty_tables = []
    for table_def in table_defs:
        table_schema = table_def.find('table-schema')
        if table_schema.text.lower() != schema:
            continue

        table_name = table_def.find("table-name")
        disposed = table_def.find("disposed")
        if disposed.text == "true":
            empty_tables.append(table_name.text.lower())

    return empty_tables


def sort_dependent_tables_old(table_defs, base_path, empty_tables, illegal_tables):
    deps_dict = {}
    for table_def in table_defs:
        table_name = table_def.find("table-name")
        disposed = table_def.find("disposed")
        if disposed.text != "true":
            deps_dict.update({
                table_name.text:
                get_table_deps(table_name, table_def, deps_dict,
                               empty_tables, illegal_tables)
            })
    deps_list = toposort_flatten(deps_dict)

    return deps_list


def sort_dependent_tables(table_defs, base_path, illegal_tables, schema, empty_tables):
    deps_dict = {}
    for table_def in table_defs:
        table_schema = table_def.find('table-schema')
        if table_schema.text.lower() != schema:
            continue

        table_name = table_def.find("table-name")
        # print(table_name.text)

        disposed = table_def.find("disposed")
        if disposed.text != "true":
            deps_dict.update({
                table_name.text.lower():
                get_table_deps(table_name, table_def, deps_dict, empty_tables, illegal_tables, schema)
            })

    deps_list = toposort_flatten(deps_dict)

    # for dep in deps_list:
    #     print(dep)

    return deps_list


def normalize_name(name, illegal_dict, t_count=0):
    repls = (
        ('æ', 'ae'),
        ('ø', 'oe'),
        ('å', 'aa'),
    )

    norm_name = reduce(lambda a, kv: a.replace(*kv), repls, name.lower())
    if norm_name in illegal_dict:
        norm_name = illegal_dict[norm_name]

    if len(norm_name) > 29:
        t_count += 1
        norm_name = norm_name[:26] + "_" + str(t_count) + "_"

    return norm_name


def get_table_deps_old(table_name, table_def, deps_dict, empty_tables, illegal_tables):
    table_deps = set()
    foreign_keys = table_def.findall("foreign-keys/foreign-key")
    for foreign_key in foreign_keys:
        constraint_name = foreign_key.find("constraint-name")
        ref_table = foreign_key.find("references/table-name")
        ref_table_value = ref_table.text.lower()
        if ref_table_value not in table_deps and ref_table_value not in empty_tables:
            if ref_table_value in deps_dict.keys():
                if table_name.text in deps_dict[ref_table_value]:
                    constraint_name.text = "_disabled_" + constraint_name.text
                    continue
            ref_table_value = normalize_name(ref_table.text, illegal_tables).lower()
            table_deps.add(ref_table_value)

    if len(table_deps) == 0:
        table_deps.add(table_name.text)
    return table_deps


def get_table_deps(table_name, table_def, deps_dict, empty_tables, illegal_tables, schema):
    table_deps = set()
    foreign_keys = table_def.findall("foreign-keys/foreign-key")
    for foreign_key in foreign_keys:
        constraint_name = foreign_key.find("constraint-name")

        # WAIT: Legg inn støtte senere for constraints på tvers av skjemaer?
        table_schema = foreign_key.find("references/table-schema")
        if table_schema.text.lower() != schema:
            continue

        print(constraint_name.text)
        ref_table = foreign_key.find("references/table-name")
        # ref_table_value = ref_table.text.lower()
        ref_table_value = normalize_name(ref_table.text, illegal_tables).lower()
        if ref_table_value not in table_deps and ref_table_value not in empty_tables:
            if ref_table_value in deps_dict.keys():
                if table_name.text.lower() in deps_dict[ref_table_value]:
                    if not constraint_name.text.startswith('_disabled_'):
                        constraint_name.text = "_disabled_" + constraint_name.text
                    continue
            # ref_table_value = normalize_name(ref_table.text, illegal_tables).lower()
            table_deps.add(ref_table_value)

    # TODO: Må ha sjekk på skjema for denne og?
    if len(table_deps) == 0:
        table_deps.add(table_name.text.lower())
    # print(table_name.text.lower() + ': ' + str(table_deps))
    return table_deps


def tsv_fix(base_path, new_file_name, pk_list, illegal_columns, tsv_process, tmp_dir):
    if tsv_process:
        pwb_replace_in_file(new_file_name, '\0', '')  # Remove null bytes

    table = etl.fromcsv(
        new_file_name,
        delimiter='\t',
        skipinitialspace=True,
        quoting=csv.QUOTE_NONE,
        quotechar='',
        escapechar='')

    # row_count = etl.nrows(table)

    if tsv_process:
        tempfile = NamedTemporaryFile(mode='w', dir=tmp_dir, delete=False)

        table = normalize_header(table, illegal_columns)

        print(new_file_name)
        # TODO: Kode med pk under håndterte ikke kolonnenavn fra illegal terms
        for pk in pk_list:
            table = etl.convert(table, pk.lower(),
                                lambda a: a if len(str(a)) > 0 else '-')

        writer = csv.writer(
            tempfile,
            delimiter='\t',
            quoting=csv.QUOTE_NONE,
            quotechar='',
            escapechar='',
            lineterminator='\n')
        writer.writerows(table)

        shutil.move(tempfile.name, new_file_name)
    # return row_count


def normalize_metadata(base_path, illegal_terms_file, schemas, tmp_dir):
    illegal_terms_set = set(map(str.strip, open(illegal_terms_file)))
    d = {s: s + '_' for s in illegal_terms_set if s}
    illegal_tables = d.copy()

    illegal_columns = d.copy()
    tsv_done_file = os.path.join(base_path, 'documentation', 'tsv_done')
    header_xml_file = os.path.join(base_path, 'header', 'metadata.xml')

    if os.path.isfile(header_xml_file):
        tree = ET.parse(header_xml_file)
        tree_lookup = ET.parse(header_xml_file)

        t_count = 0
        c_count = 0
        pk_dict = {}
        constraint_dict = {}
        fk_columns_dict = {}
        fk_ref_dict = {}
        unique_dict = {}
        table_defs = tree.findall("table-def")
        for table_def in table_defs:
            table_schema = table_def.find('table-schema')
            if table_schema.text is None:
                table_schema.text = 'PUBLIC'

            schema = table_schema.text.lower()
            table_name = table_def.find("table-name")
            old_table_name = ET.Element("original-table-name")
            old_table_name.text = table_name.text

            # Add tables names too long for oracle to 'illegal_tables'
            # TODO: Bruk normalize funksjon heller her og inkorporer kode under i den heller
            # if len(table_name.text) > 29:
            #     t_count += 1
            #     table_name.text = table_name.text[:26] + "_" + str(t_count) + "_"
            #     illegal_tables[old_table_name.text] = table_name.text

            table_name_norm = normalize_name(table_name.text, illegal_tables, t_count)
            file_name = os.path.join(base_path, 'content', schema, 'data', table_name.text + '.txt')
            new_file_name = os.path.join(base_path, 'content', schema, 'data', table_name_norm.lower() + '.tsv')

            tsv_process = False
            if not os.path.isfile(tsv_done_file):
                tsv_process = True

            if os.path.isfile(file_name):
                os.rename(file_name, new_file_name)

            # if table_name.text in illegal_tables:
            #     table_name.text = illegal_tables[table_name.text]

            #     # TODO: Bare slette fil direkte her heller?
            #     ill_new_file_name = os.path.splitext(file_name)[0] + '_.tsv'
            #     if os.path.isfile(new_file_name):
            #         os.rename(new_file_name, ill_new_file_name)
            #     new_file_name = ill_new_file_name

            # table_name.text = table_name_norm.lower()
            # table_name.text = table_name.text.lower()

            merge_xml_element(table_def, 'original-table-name', old_table_name.text, 3)

            table_def.set('name', table_name_norm)

            # unique_list = []
            index_defs = table_def.findall("index-def")
            for index_def in index_defs:
                unique = index_def.find('unique')
                primary_key = index_def.find('primary-key')
                index_name = index_def.find('name')

                unique_col_list = []
                if unique.text == 'true' and primary_key.text == 'false':
                    index_column_names = index_def.findall("column-list/column")
                    for index_column_name in index_column_names:
                        unique_constraint_name = index_column_name.attrib['name'].lower()
                        unique_col_list.append(unique_constraint_name)
                    unique_dict[(table_name_norm, index_name.text.lower())] = sorted(unique_col_list)

            pk_list = []
            column_defs = table_def.findall("column-def")
            for column_def in column_defs:
                column_name = column_def.find('column-name')
                primary_key = column_def.find('primary-key')
                column_name.text = normalize_name(column_name.text, illegal_columns)
                # column_name_short = None

                if len(column_name.text) > 29:
                    c_count += 1
                    column_name.text = column_name.text[:26] + "_" + str(c_count)
                    # illegal_columns[column_name.text] = column_name_short
                    # column_name.text = column_name_short

                # column_name_norm = normalize_name(column_name.text, illegal_columns)
                if primary_key.text == 'true':
                    pk_list.append(column_name.text)

                    # if column_name.text in illegal_columns:
                    #     column_name.text = column_name.text.lower() + '_'

                    # # tab_constraint_name.text = tab_constraint_name.text + '_'
                    # if column_name_short:
                    #     column_name_norm = column_name_short
                    # else:
                    #     column_name_norm = normalize_name(column_name.text, illegal_columns)

                    # # TODO: Feil at ikke er navn med underscore sist når illegal name her?

            pk_dict[table_name_norm] = ', '.join(sorted(pk_list))

            if os.path.exists(new_file_name):
                tsv_fix(base_path, new_file_name, pk_list, illegal_columns, tsv_process, tmp_dir)

        # Sort tables in dependent order:
        for schema in schemas:
            ddl_file = os.path.join(base_path, 'documentation', schema + '_ddl.sql')

            oracle_dir = os.path.join(base_path, 'documentation', 'oracle_import')
            pathlib.Path(os.path.join(oracle_dir, schema)).mkdir(parents=True, exist_ok=True)

            empty_tables = get_empty_tables(table_defs, schema)

            # for tabl in illegal_tables:
            #     print(tabl)
            # return

            deps_list = sort_dependent_tables(table_defs, base_path, illegal_tables, schema, empty_tables)

            import_order_file = os.path.join(base_path, 'documentation', schema + '_tables.txt')
            with open(import_order_file, 'w') as file:
                for val in deps_list:
                    val = normalize_name(val, illegal_tables)
                    file.write('%s\n' % val)

            ddl_columns = {}
            for table_def in table_defs:
                table_schema = table_def.find('table-schema')
                table_name = table_def.find("table-name")
                disposed = table_def.find("disposed")
                self_dep_set = set()
                index = 0

                table_name_norm = normalize_name(table_name.text, illegal_tables)

                if table_schema.text.lower() != schema:
                    continue

                ora_ctl_file = os.path.join(oracle_dir, schema, table_name_norm + '.ctl')
                ora_ctl_list = []
                if disposed.text == "true":
                    continue

                ora_ctl = [
                    'LOAD DATA', 'CHARACTERSET UTF8 LENGTH SEMANTICS CHAR',
                    'INFILE ' + table_name_norm + '.tsv',
                    'INSERT INTO TABLE ' + str(table_name_norm).upper(),
                    "FIELDS TERMINATED BY '\\t' TRAILING NULLCOLS", '(#'
                ]
                ora_ctl_list.append('\n'.join(ora_ctl))

                if table_name_norm in deps_list:
                    index = int(deps_list.index(table_name_norm))

                merge_xml_element(table_def, 'dep-position', str(index + 1), 6)

                constraint_set = set()
                foreign_keys = table_def.findall("foreign-keys/foreign-key")
                for foreign_key in foreign_keys:
                    tab_constraint_name = foreign_key.find("constraint-name")
                    old_tab_constraint_name_text = tab_constraint_name.text

                    if str(tab_constraint_name.text).startswith('SYS_C'):
                        tab_constraint_name.text = tab_constraint_name.text + '_'

                    tab_constraint_name.text = tab_constraint_name.text.lower()
                    merge_xml_element(foreign_key, 'original-constraint-name', old_tab_constraint_name_text, 1)

                    fk_references = foreign_key.findall('references')
                    for fk_reference in fk_references:
                        tab_ref_table_name = fk_reference.find("table-name")
                        old_tab_ref_table_name = ET.Element("original-table-name")
                        old_tab_ref_table_name.text = tab_ref_table_name.text

                        if tab_ref_table_name.text.lower() in empty_tables:
                            if not tab_constraint_name.text.startswith('_disabled_'):
                                tab_constraint_name.text = "_disabled_" + tab_constraint_name.text

                        tab_ref_table_name.text = normalize_name(tab_ref_table_name.text, illegal_tables).lower()
                        merge_xml_element(fk_reference, 'original-table-name', old_tab_ref_table_name.text, 3)

                        if not tab_constraint_name.text.startswith('_disabled_'):
                            constraint_set.add(tab_constraint_name.text + ':' + tab_ref_table_name.text)

                    # WAIT: Slå sammen de to under til en def

                    source_column_set = set()
                    source_columns = foreign_key.findall('source-columns')
                    for source_column in source_columns:
                        source_column_names = source_column.findall('column')

                        for source_column_name in source_column_names:
                            value = source_column_name.text
                            source_column_name.text = normalize_name(source_column_name.text, illegal_columns).lower()

                            merge_xml_element(source_column, 'original-column', value, 10)
                            source_column_set.add(source_column_name.text)

                    if not len(source_column_set) == 0:
                        fk_columns_dict.update({tab_constraint_name.text: source_column_set})  # TODO: Endre andre til å være på denne formen heller enn split på : mm?

                    referenced_columns = foreign_key.findall('referenced-columns')
                    for referenced_column in referenced_columns:
                        referenced_column_names = referenced_column.findall('column')

                        for referenced_column_name in referenced_column_names:
                            old_referenced_column_name_text = referenced_column_name.text
                            referenced_column_name.text = normalize_name(referenced_column_name.text, illegal_columns).lower()
                            merge_xml_element(referenced_column, 'original-column', old_referenced_column_name_text, 10)

                constraint_dict[table_name_norm] = ','.join(constraint_set).lower()

                column_defs = table_def.findall("column-def")
                column_defs[:] = sorted(column_defs, key=lambda elem: int(elem.findtext('dbms-position')))
                # WAIT: Sortering virker men blir ikke lagret til xml-fil. Fiks senere når lage siard/datapackage-versjoner

                ddl_columns_list = []
                for column_def in column_defs:
                    column_name = column_def.find('column-name')
                    java_sql_type = column_def.find('java-sql-type')
                    dbms_data_size = column_def.find('dbms-data-size')
                    value = column_name.text
                    column_name.text = normalize_name(column_name.text, illegal_columns).lower()
                    merge_xml_element(column_def, 'original-column-name', value, 2)
                    column_def.set('name', column_name.text)

                    col_references = column_def.findall('references')
                    ref_col_ok = False
                    for col_reference in col_references:
                        ref_col_ok = True
                        ref_column_name = col_reference.find('column-name')
                        col_ref_table_name = col_reference.find('table-name')
                        col_constraint_name = col_reference.find('constraint-name')
                        old_col_constraint_name_text = col_constraint_name.text
                        old_ref_column_name_text = ref_column_name.text
                        old_ref_table_name_text = col_ref_table_name.text

                        ref_column_name.text = normalize_name(ref_column_name.text, illegal_columns)
                        merge_xml_element(column_def, 'original-column-name', old_ref_column_name_text, 3)

                        col_ref_table_name.text = normalize_name(col_ref_table_name.text, illegal_tables)
                        merge_xml_element(col_reference, 'original-table-name', old_ref_table_name_text, 3)

                        old_col_constraint_fix = False
                        if str(col_constraint_name.text).startswith('SYS_C'):
                            col_constraint_name.text = col_constraint_name.text + '_'
                            old_col_constraint_fix = True

                        if col_ref_table_name.text.lower() in empty_tables:
                            if not col_constraint_name.text.startswith('_disabled_'):
                                col_constraint_name.text = "_disabled_" + col_constraint_name.text
                            old_col_constraint_fix = True

                        if old_col_constraint_fix:
                            merge_xml_element(col_reference, 'original-constraint-name', old_col_constraint_name_text, 2)

                        if col_ref_table_name.text.lower(
                        ) == table_name.text and col_ref_table_name.text.lower(
                        ) not in empty_tables:
                            self_dep_set.add(ref_column_name.text.lower() + ':' + column_name.text.lower())

                        xpath_str = "table-def[table-name='" + col_ref_table_name.text + "']/column-def[column-name='" + old_ref_column_name_text + "']"
                        ref_column = tree_lookup.find(xpath_str)

                        if ref_column:
                            ref_column_data_size = ref_column.find(
                                'dbms-data-size')
                            if ref_column_data_size.text != dbms_data_size.text:
                                dbms_data_size.text = ref_column_data_size.text

                    if ref_col_ok:
                        fk_ref_dict[table_name_norm + ':' + column_name.text] = ref_column_name.text

                    if disposed.text != "true":
                        ora_ctl_type = jdbc_to_ora_ctl_data_type[java_sql_type.text]
                        if '()' in ora_ctl_type:
                            ora_ctl_type = ora_ctl_type.replace('()', '(' + dbms_data_size.text + ')')

                        ora_ctl_list.append(
                            column_name.text + ' ' + ora_ctl_type)

                        iso_data_type = jdbc_to_iso_data_type[java_sql_type.text]
                        if '()' in iso_data_type:
                            if int(dbms_data_size.text) < 4001:
                                iso_data_type = iso_data_type.replace('()', '(' + dbms_data_size.text + ')')
                            else:
                                iso_data_type = 'text'

                        ddl_columns_list.append(column_name.text + ' ' + iso_data_type + ',')

                # Write Oracle SQL Loader control file:
                if disposed.text != "true":
                    with open(ora_ctl_file, "w") as file:
                        file.write((',\n'.join(ora_ctl_list)).replace(
                            '#,', '') + ' TERMINATED BY WHITESPACE \n)')

                if len(self_dep_set) != 0:
                    order_by_constraint(base_path, table_name.text, table_schema.text, self_dep_set)

                ddl_columns[table_name_norm] = '\n'.join(ddl_columns_list)

            root = tree.getroot()
            indent(root)
            tree.write(header_xml_file, encoding='utf-8')

            ddl = []

            # # TODO Print under kun for test
            # for table in deps_list:
            #     print(table)
            # # TODO: Fjern duplikater her eller finn måte å unngå i utgangspunktet

            for table in deps_list:
                table_norm = normalize_name(table, illegal_tables)
                pk_str = ''
                if pk_dict[table_norm]:
                    pk_str = ',\nPRIMARY KEY (' + pk_dict[table_norm] + ')'

                unique_str = ''
                unique_constraints = {key: val for key, val in unique_dict.items() if key[0] == table}
                if unique_constraints:
                    for key, value in unique_constraints.items():
                        unique_str = unique_str + ',\nCONSTRAINT ' + key[1] + ' UNIQUE (' + ', '.join(value) + ')'

                fk_str = ''
                if constraint_dict[table_norm]:
                    for s in [x for x in constraint_dict[table_norm].split(',')]:
                        constr, ref_table = s.split(':')
                        # TODO: Er ref_table normalisert?

                        ref_column_list = []
                        source_column_list = fk_columns_dict[constr]
                        for col in source_column_list:
                            col = normalize_name(col, illegal_columns)
                            ref_column_list.append(fk_ref_dict[table_norm + ':' + col] + ':' + col)

                        ref_column_list = sorted(ref_column_list)
                        ref_s = ''
                        source_s = ''
                        for s in ref_column_list:
                            ref, source = s.split(':')
                            ref_s = ref_s + ', ' + ref
                            source_s = source_s + ', ' + source
                        ref_s = ref_s[2:]
                        source_s = source_s[2:]

                        fk_str = fk_str + ',\nCONSTRAINT ' + constr + '\nFOREIGN KEY (' + source_s + ')\nREFERENCES ' + ref_table + ' (' + ref_s + ')'

                ddl.append('\nCREATE TABLE ' + table_norm + '(\n' + ddl_columns[table_norm][:-1] + pk_str + unique_str + fk_str + ');')

            with open(ddl_file, "w") as file:
                file.write("\n".join(ddl))

        open(tsv_done_file, 'a').close()

        # TODO: Denne syntaksen er støttet av alle
        # create table newish_table (
        #     id   int not null,
        #     id_A int not null,
        #     id_B int not null,
        #     id_C int null,
        #     id_t int,
        #     constraint pk_newish_table primary key (id),
        #     constraint u_constrainte4 unique (id_t),
        #     constraint u_constrainte5 unique (id_A, id_B, id_C)
        # );


def order_by_constraint(base_path, table, schema, self_dep_set):
    file_name = base_path + "/content/data/" + table + ".tsv"
    tempfile = NamedTemporaryFile(mode='w', dir=base_path + "/content/data/", delete=False)
    table = etl.fromcsv(
        file_name,
        delimiter='\t',
        skipinitialspace=True,
        quoting=csv.QUOTE_NONE,
        quotechar='',
        escapechar='')

    key_dep_dict = {}

    # print(file_name)
    for constraint in self_dep_set:
        child_dep, parent_dep = constraint.split(':')
        data = etl.values(table, child_dep, parent_dep)
        for d in data:
            key_dep_set = {d[1]}
            key_dep_dict.update({d[0]: key_dep_set})

    key_dep_list = toposort_flatten(key_dep_dict)
    table = etl.addfield(
        table, 'pwb_index',
        lambda rec: int(key_dep_list.index(rec[child_dep])))
    table = etl.sort(table, 'pwb_index')
    table = etl.cutout(table, 'pwb_index')

    writer = csv.writer(
        tempfile,
        delimiter='\t',
        quoting=csv.QUOTE_NONE,
        quotechar='',
        lineterminator='\n',
        escapechar='')

    writer.writerows(table)
    shutil.move(tempfile.name, file_name)
