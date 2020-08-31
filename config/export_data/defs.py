# Copyright (C) 2020 Morten Eek

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import subprocess
from subprocess import check_output, STDOUT
import jpype as jp
import jpype.imports
from pathlib import Path
import xml.etree.ElementTree as ET
from database.jdbc import Jdbc
from common.file import get_unique_dir
from common.jvm import init_jvm, wb_batch
from common.print import print_and_exit
from common.xml import indent


# TODO: Bytt ut print_and_exit og fjern så den (må sjekke at da avslutter hele med return heller)


def get_db_details(jdbc_url, bin_dir):
    # TODO: Legg inn støtte for flere dbtyper
    if 'jdbc:h2:' in jdbc_url:  # H2 database
        if 'LAZY_QUERY_EXECUTION' not in jdbc_url:
            jdbc_url = jdbc_url + ';LAZY_QUERY_EXECUTION=1;'  # Modify url for less memory use
        driver_jar = bin_dir + '/vendor/jdbc/h2-1.4.199.jar' # WAIT: Juster så ikke hardkodet og sjekk at finnes
        # print(driver_jar)
        driver_class = 'org.h2.Driver'

    return jdbc_url, driver_jar, driver_class


def capture_files(bin_dir, source_path, target_path):
    Path(os.path.dirname(target_path)).mkdir(parents=True, exist_ok=True)
    archive_format = Path(target_path).suffix[1:]

    if archive_format == 'wim':
        cmd = bin_dir + "/vendor/wimlib-imagex capture " + source_path + " " + target_path + " --no-acls --compress=none"
        # subprocess.run(cmd + source_path + " " + target_path + " --no-acls --compress=none", shell=True)
    else:
        cmd = "cd " + str(Path(source_path).parent) + " && tar -cvf " + target_path + " " + os.path.basename(source_path)
        # subprocess.run("cd " + str(Path(source_path).parent) + " && tar -cvf " + target_path + " " + os.path.basename(source_path), shell=True)

    try:
        check_output(cmd, stderr=STDOUT, shell=True).decode()
    except Exception as e:
        return e 

    return 'ok'          


def get_tables(conn, schema):
    results = conn.jconn.getMetaData().getTables(None, schema, "%", None)
    table_reader_cursor = conn.cursor()
    table_reader_cursor._rs = results
    table_reader_cursor._meta = results.getMetaData()
    read_results = table_reader_cursor.fetchall()
    tables = [row[2] for row in read_results if row[3] == 'TABLE']
    return tables


def export_schema(class_path, max_java_heap, subsystem_dir, jdbc, db_tables):
    base_dir = subsystem_dir + '/documentation/'

    if os.path.isfile(base_dir + 'metadata.xml'):
        return

    init_jvm(class_path, max_java_heap)  # Start Java virtual machine
    WbManager = jp.JPackage('workbench').WbManager
    WbManager.prepareForEmbedded()
    batch = jp.JPackage('workbench.sql').BatchRunner()
    batch.setAbortOnError(True)

    batch.setBaseDir(base_dir)
    batch.runScript("WbConnect -url='" + jdbc.url + "' -password=" + jdbc.pwd + ";")
    gen_report_str = "WbSchemaReport -file=metadata.xml -schemas=" + jdbc.db_schema + " -types=SYNONYM,TABLE,VIEW -includeProcedures=true \
                            -includeTriggers=true -writeFullSource=true;"
    batch.runScript(gen_report_str)
    add_row_count_to_schema_file(subsystem_dir, db_tables)

# TODO: Fjern duplisering av kode mellom denn og export_db_schema
def test_db_connect(JDBC_URL, bin_dir, class_path, MAX_JAVA_HEAP, DB_USER, DB_PASSWORD, DB_NAME, DB_SCHEMA, INCL_TABLES, SKIP_TABLES, OVERWRITE_TABLES):
    url, driver_jar, driver_class = get_db_details(JDBC_URL, bin_dir)
    if driver_jar and driver_class:
        # Start Java virtual machine if not started already:
        class_paths = class_path + ':' + driver_jar
        init_jvm(class_paths, MAX_JAVA_HEAP)

        try:
            jdbc = Jdbc(url, DB_USER, DB_PASSWORD, DB_NAME, DB_SCHEMA, driver_jar, driver_class, True, True)
            # TODO: Legg inn forståelig melding hvis db_name eller db_schema er feil/ikke finnes
            if jdbc:
                # Get database metadata:
                db_tables, table_columns = get_db_meta(jdbc)
                export_tables, overwrite_tables = table_check(INCL_TABLES, SKIP_TABLES, OVERWRITE_TABLES, db_tables)
                return 'ok'

            if not export_tables:
                return 'No table data to export. Exiting.'

        except Exception as e:
            return e

    else:
        return 'Not a supported jdbc url. Exiting'


def export_db_schema(JDBC_URL, bin_dir, class_path, MAX_JAVA_HEAP, DB_USER, DB_PASSWORD, DB_NAME, DB_SCHEMA, subsystem_dir, INCL_TABLES, SKIP_TABLES, OVERWRITE_TABLES, DDL_GEN):
    url, driver_jar, driver_class = get_db_details(JDBC_URL, bin_dir)
    if driver_jar and driver_class:
        # Start Java virtual machine if not started already:
        class_paths = class_path + ':' + driver_jar
        init_jvm(class_paths, MAX_JAVA_HEAP)

        try:
            jdbc = Jdbc(url, DB_USER, DB_PASSWORD, DB_NAME, DB_SCHEMA, driver_jar, driver_class, True, True)
            if jdbc:
                # Get database metadata:
                db_tables, table_columns = get_db_meta(jdbc)
                print(table_columns) # TODO: Fiks at ikke henter tabeller og kolonner riktig
                export_schema(class_path, MAX_JAVA_HEAP, subsystem_dir, jdbc, db_tables)
                export_tables, overwrite_tables = table_check(INCL_TABLES, SKIP_TABLES, OVERWRITE_TABLES, db_tables)

            if export_tables:
                print('test')
                # Copy schema data:
                copy_db_schema(subsystem_dir, jdbc, class_path, MAX_JAVA_HEAP, export_tables, bin_dir, table_columns, overwrite_tables, DDL_GEN)
                return 'ok'
            else:
                print('No table data to export. Exiting.')
                return

        except Exception as e:
            print(e)
            return

    else:
        print('Not a supported jdbc url. Exiting')
        return


def get_db_meta(jdbc):
    db_tables = {}
    table_columns = {}
    conn = jdbc.connection
    cursor = conn.cursor()
    tables = get_tables(conn, jdbc.db_schema)

    # Get row count per table:
    for table in tables:
        cursor.execute('SELECT COUNT(*) from "' + table + '";')
        (row_count,) = cursor.fetchone()
        db_tables[table] = row_count

        # Get column names of table:
        cursor.execute('SELECT * from "' + table + '"')
        table_columns[table] = [desc[0] for desc in cursor.description]

    cursor.close()
    conn.close()
    return db_tables, table_columns


def add_row_count_to_schema_file(subsystem_dir, db_tables):
    schema_file = subsystem_dir + '/documentation/metadata.xml'
    tree = ET.parse(schema_file)

    table_defs = tree.findall("table-def")
    for table_def in table_defs:
        table_name = table_def.find("table-name")

        disposed = ET.Element("disposed")
        disposed.text = "false"
        disposal_comment = ET.Element("disposal_comment")
        disposal_comment.text = " "
        rows = ET.Element("rows")

        row_count = db_tables[table_name.text]
        if row_count == 0:
            disposed.text = "true"
            disposal_comment.text = "Empty table"
        rows.text = str(row_count)

        table_def.insert(5, rows)
        table_def.insert(6, disposed)
        table_def.insert(7, disposal_comment)

    root = tree.getroot()
    indent(root)
    tree.write(schema_file)


def table_check(incl_tables, skip_tables, overwrite_tables, db_tables):
    non_empty_tables = {k: v for (k, v) in db_tables.items() if v > 0}
    if incl_tables:
        for tbl in incl_tables:
            if tbl not in non_empty_tables:
                print_and_exit("Table '" + tbl + "' is empty or not in schema. Exiting.")
        for tbl in list(non_empty_tables):
            if tbl not in incl_tables:
                del non_empty_tables[tbl]
    elif skip_tables:
        for tbl in skip_tables:
            if tbl in non_empty_tables:
                del non_empty_tables[tbl]
            else:
                print_and_exit("Table '" + tbl + "' is empty or not in schema. Exiting.")

    if overwrite_tables:
        for tbl in overwrite_tables:
            if tbl not in non_empty_tables:
                print_and_exit("Table '" + tbl + "' is empty or not in source schema. Exiting.")

    return non_empty_tables, overwrite_tables


def get_target_tables(jdbc):
    target_tables = {}
    conn = jdbc.connection
    cursor = conn.cursor()
    tables = get_tables(conn, jdbc.db_schema)

    # Get row count per table:
    for table in tables:
        cursor.execute('SELECT COUNT(*) from "' + table + '";')
        (row_count,) = cursor.fetchone()
        target_tables[table] = row_count

    cursor.close()
    conn.close()
    return target_tables


def get_blob_columns(subsystem_dir, export_tables):
    blob_columns = {}
    schema_file = subsystem_dir + '/documentation/metadata.xml'
    tree = ET.parse(schema_file)

    table_defs = tree.findall("table-def")
    for table_def in table_defs:
        table_name = table_def.find("table-name")
        if table_name.text not in export_tables:
            continue

        columns = []
        column_defs = table_def.findall("column-def")
        for column_def in column_defs:
            column_name = column_def.find('column-name')
            java_sql_type = column_def.find('java-sql-type')
            if int(java_sql_type.text) in (-4, -3, -2, 2004, 2005, 2011):
                columns.append(column_name.text)

        if columns:
            blob_columns[table_name.text] = columns

    return blob_columns


def get_primary_keys(subsystem_dir, export_tables):
    pk_dict = {}
    schema_file = subsystem_dir + '/documentation/metadata.xml'
    tree = ET.parse(schema_file)

    table_defs = tree.findall("table-def")
    for table_def in table_defs:
        table_name = table_def.find("table-name")
        if table_name.text not in export_tables:
            continue

        pk_list = []
        column_defs = table_def.findall("column-def")
        for column_def in column_defs:
            column_name = column_def.find('column-name')
            primary_key = column_def.find('primary-key')

            if primary_key.text == 'true':
                pk_list.append(column_name.text)

        if pk_list:
            pk_dict[table_name.text] = pk_list

    return pk_dict


def get_unique_indexes(subsystem_dir, export_tables):
    unique_dict = {}
    schema_file = subsystem_dir + '/documentation/metadata.xml'
    tree = ET.parse(schema_file)

    table_defs = tree.findall("table-def")
    for table_def in table_defs:
        table_name = table_def.find("table-name")
        if table_name.text not in export_tables:
            continue

        index_defs = table_def.findall("index-def")
        for index_def in index_defs:
            unique = index_def.find('unique')
            primary_key = index_def.find('primary-key')

            unique_col_list = []
            if unique.text == 'true' and primary_key.text == 'false':
                index_column_names = index_def.findall("column-list/column")
                for index_column_name in index_column_names:
                    unique_constraint_name = index_column_name.attrib['name']
                    unique_col_list.append(unique_constraint_name)
                unique_dict[table_name.text] = unique_col_list
                break  # Only need one unique column

    return unique_dict


def run_ddl(jdbc, sql):
    result = 'Success'
    try:
        conn = jdbc.connection
        cursor = conn.cursor()
        cursor.execute(sql)
        cursor.close()
        conn.commit()
        conn.close()
    except Exception as e:
        result = e

    if result != 'Success':
        print_and_exit(result)


def run_select(jdbc, sql):
    conn = jdbc.connection
    cursor = conn.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def gen_sync_table(table, columns, target_url, driver_jar, driver_class, source_query):
    print("Syncing table '" + table + "'...")
    source_query = source_query + ' WHERE ('
    target_query = 'SELECT '

    for col in columns:
        source_query = source_query + '"' + col + '", '
        target_query = target_query + '"' + col + '", '

    source_query = source_query[:-2]
    target_query = target_query[:-2] + ' FROM "' + table + '";'

    t_jdbc = Jdbc(target_url, '', '', '', 'PUBLIC', driver_jar, driver_class, True, True)
    target_values = run_select(t_jdbc, target_query)
    if len(columns) > 1:  # Compound key
        source_query = source_query + ') NOT IN (' + ', '.join(map(str, target_values)) + ')'
    else:
        source_query = source_query + ") NOT IN ('" + "','".join(map(str, ([x[0] for x in target_values]))) + "')"

    return source_query


def create_index(table, pk_dict, unique_dict, ddl):
    if table in pk_dict:
        for col in pk_dict[table]:
            ddl = ddl + '\nCREATE INDEX c_' + col + ' ON "' + table + '" ("' + col + '");'
    if table in unique_dict:
        for col in unique_dict[table]:
            ddl = ddl + '\nCREATE INDEX c_' + col + ' ON "' + table + '" ("' + col + '");'

    return ddl


def copy_db_schema(subsystem_dir, s_jdbc, class_path, max_java_heap, export_tables, bin_dir, table_columns, overwrite_tables, DDL_GEN):
    batch = wb_batch(class_path, max_java_heap)
    target_url = 'jdbc:h2:' + subsystem_dir + '/documentation/' + s_jdbc.db_name + '_' + s_jdbc.db_schema + ';autocommit=off'
    target_url, driver_jar, driver_class = get_db_details(target_url, bin_dir)
    t_jdbc = Jdbc(target_url, '', '', '', 'PUBLIC', driver_jar, driver_class, True, True)
    target_tables = get_target_tables(t_jdbc)
    pk_dict = get_primary_keys(subsystem_dir, export_tables)
    unique_dict = get_unique_indexes(subsystem_dir, export_tables)
    blob_columns = get_blob_columns(subsystem_dir, export_tables)

    if DDL_GEN == 'Native':
        ddl_columns = get_ddl_columns(subsystem_dir)

    mode = '-mode=INSERT'
    std_params = ' -ignoreIdentityColumns=false -removeDefaults=true -commitEvery=1000 '
    previous_export = []
    for table, row_count in export_tables.items():
        insert = True
        params = mode + std_params

        col_query = ''
        if table in blob_columns:
            for column in blob_columns[table]:
                col_query = ',LENGTH("' + column + '") AS ' + column.upper() + '_BLOB_LENGTH_PWCODE'

        source_query = 'SELECT "' + '","'.join(table_columns[table]) + '"' + col_query + ' FROM "' + s_jdbc.db_schema + '"."' + table + '"'

        if table in target_tables and table not in overwrite_tables:
            t_row_count = target_tables[table]
            if t_row_count == row_count:
                previous_export.append(table)
                continue
            elif t_row_count > row_count:
                print_and_exit("Error. More data in target than in source. Table '" + table + "'. Exiting.")
            elif table in pk_dict:
                source_query = gen_sync_table(table, pk_dict[table], target_url, driver_jar, driver_class, source_query)
                insert = False
            elif table in unique_dict:
                source_query = gen_sync_table(table, unique_dict[table], target_url, driver_jar, driver_class, source_query)
                insert = False

        if insert:
            print("Copying table '" + table + "':")
            if DDL_GEN == 'SQL Workbench':
                params = mode + std_params + ' -createTarget=true -dropTarget=true'
            elif DDL_GEN == 'Native':
                t_jdbc = Jdbc(target_url, '', '', '', 'PUBLIC', driver_jar, driver_class, True, True)
                ddl = '\nCREATE TABLE "' + table + '"\n(\n' + ddl_columns[table][:-1] + '\n);'
                ddl = create_index(table, pk_dict, unique_dict, ddl)
                print(ddl)
                sql = 'DROP TABLE IF EXISTS "' + table + '"; ' + ddl
                run_ddl(t_jdbc, sql)

            if table in blob_columns:
                for column in blob_columns[table]:
                    t_jdbc = Jdbc(target_url, '', '', '', 'PUBLIC', driver_jar, driver_class, True, True)
                    sql = 'ALTER TABLE "' + table + '" ADD COLUMN ' + column.upper() + '_BLOB_LENGTH_PWCODE VARCHAR(255);'
                    run_ddl(t_jdbc, sql)

        batch.runScript("WbConnect -url='" + s_jdbc.url + "' -password=" + s_jdbc.pwd + ";")
        target_conn = '"username=,password=,url=' + target_url + '" ' + params
        target_table = '"' + table + '"'
        copy_data_str = "WbCopy -targetConnection=" + target_conn + " -targetSchema=PUBLIC -targetTable=" + target_table + " -sourceQuery=" + source_query + ";"
        result = batch.runScript(copy_data_str)
        batch.runScript("WbDisconnect;")
        jp.java.lang.System.gc()
        if str(result) == 'Error':
            print_and_exit("Error on copying table '" + table + "'\nScroll up for details.")

    if len(previous_export) == len(export_tables.keys()):
        print('All tables already exported.')
    elif not previous_export:
        print('Database export complete.')
    else:
        print('Database export complete. ' + str(len(previous_export)) + ' of ' + str(len(export_tables.keys())) + ' tables were already exported.')


# WAIT: Mangler disse for å ha alle i JDBC 4.0: ROWID=-8 og SQLXML=2009
#                        jdbc-id  iso-name               jdbc-name
jdbc_to_iso_data_type = {
    '-16': 'clob',               # LONGNVARCHAR
    '-15': 'varchar',            # NCHAR
    '-9': 'varchar',            # NVARCHAR
    '-7': 'boolean',            # BIT
    '-6': 'integer',            # TINYINT
    '-5': 'integer',            # BIGINT
    '-4': 'blob',               # LONGVARBINARY
    '-3': 'blob',               # VARBINARY
    '-2': 'blob',               # BINARY
    '-1': 'clob',               # LONGVARCHAR
    '1': 'varchar',            # CHAR
    '2': 'numeric',            # NUMERIC
    '3': 'decimal',            # DECIMAL
    '4': 'integer',            # INTEGER
    '5': 'integer',            # SMALLINT
    '6': 'float',              # FLOAT
    '7': 'real',               # REAL
    '8': 'double precision',   # DOUBLE
    '12': 'varchar',            # VARCHAR
    '16': 'boolean',            # BOOLEAN
    '91': 'date',               # DATE
    '92': 'time',               # TIME
    '93': 'timestamp',          # TIMESTAMP
    '2004': 'blob',               # BLOB
    '2005': 'clob',               # CLOB
    '2011': 'clob',               # NCLOB
}

# WAIT: Sortere long raw sist eller først for å unngå bug i driver?
# -> https://blog.jooq.org/tag/long-raw/


def get_ddl_columns(subsystem_dir):
    ddl_columns = {}
    schema_file = subsystem_dir + '/documentation/metadata.xml'
    tree = ET.parse(schema_file)

    table_defs = tree.findall("table-def")
    for table_def in table_defs:
        table_name = table_def.find("table-name")
        disposed = table_def.find("disposed")

        ddl_columns_list = []
        column_defs = table_def.findall("column-def")
        for column_def in column_defs:
            column_name = column_def.find('column-name')
            java_sql_type = column_def.find('java-sql-type')
            dbms_data_size = column_def.find('dbms-data-size')

            if disposed.text != "true":
                iso_data_type = jdbc_to_iso_data_type[java_sql_type.text]
                if '()' in iso_data_type:
                    iso_data_type = iso_data_type.replace('()', '(' + dbms_data_size.text + ')')

                ddl_columns_list.append('"' + column_name.text + '" ' + iso_data_type + ',')
        ddl_columns[table_name.text] = '\n'.join(ddl_columns_list)

    return ddl_columns
