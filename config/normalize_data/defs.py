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
from pathlib import Path
import glob
import tarfile
import jaydebeapi
import shutil
from common.jvm import wb_batch
from common.print import print_and_exit
import jpype as jp
import jpype.imports
import xml.etree.ElementTree as ET
from common.metadata import run_tika
from common.convert import convert_folder, file_convert


def mount_wim(filepath, mount_dir):
    Path(mount_dir).mkdir(parents=True, exist_ok=True)
    if len(os.listdir(mount_dir)) == 0:
        subprocess.run(
            "GVFS_DISABLE_FUSE=1; export GVFS_DISABLE_FUSE; wimmountrw --allow-other "
            + filepath + " " + mount_dir,
            shell=True)


def get_files(extensions, path):
    all_files = []
    for ext in extensions:
        all_files.extend(Path(path).glob(ext))
    return all_files


def get_java_path_sep():
    if os.name == "posix":
        return ':'
    return ';'


def export_lob_columns(data_dir, batch, jdbc_url, table, table_columns):
    txt_file = os.path.join(data_dir, table + '_lobs.txt')
    clob = 'true'
    blob = 'file'
    for column in table_columns[table + '_lobs']:
        file_name = "'" + table + "_" + column + "_" + "'" + " || rownum() || '.data'"
        condition = f'''WHERE NULLIF("{column}", '') IS NOT NULL'''
        source_query = 'SELECT "' + column + '",' + file_name + ' as fname FROM PUBLIC."' + table + '"' + condition

        export_data_list = ["WbExport ",
                            "-type=text ",
                            "-file = " + txt_file + " ",
                            "-continueOnError = false ",
                            "-clobAsFile = " + clob + " ",
                            "-blobtype = " + blob + " ",
                            "-showProgress=10000 ",
                            "-filenameColumn=fname ",
                            ";" + source_query + ";"
                            ]

        batch.runScript("WbConnect -url='" + jdbc_url + "';")
        result = batch.runScript(''.join(export_data_list))
        batch.runScript("WbDisconnect;")
        jp.java.lang.System.gc()

    return str(result)


def export_text_columns(data_dir, batch, jdbc_url, table, table_columns):
    batch.runScript("WbConnect -url='" + jdbc_url + "';")
    txt_file = os.path.join(data_dir, table + '.txt')
    columns = table_columns[table]
    clob = 'false'
    blob = 'base64'

    for index, column in enumerate(columns):
        if '|| ROWNUM() AS' not in column:
            columns[index] = '"' + column + '"'

    source_query = 'SELECT ' + ','.join(columns) + '  FROM PUBLIC."' + table + '"'
    export_data_list = ["WbExport ",
                        "-type=text ",
                        "-file = " + txt_file + " ",
                        "-continueOnError = false ",
                        "-encoding=UTF8 ",
                        "-header=true ",
                        "-decimal='.' ",
                        "-maxDigits=0 ",
                        "-lineEnding=lf ",
                        "-clobAsFile = " + clob + " ",
                        "-blobtype = " + blob + " ",
                        "-delimiter=\t ",
                        "-replaceExpression='(\n|\r\n|\r|\t|^$)' -replaceWith=' ' ",
                        "-nullString=' ' ",
                        "-showProgress=10000 ",
                        ";" + source_query + ";"
                        ]

    result = batch.runScript(''.join(export_data_list))
    batch.runScript("WbDisconnect;")
    jp.java.lang.System.gc()

    return str(result)


def get_tables(sub_systems_dir, sub_system):
    tables = []
    table_columns = {}
    schema_file = os.path.join(sub_systems_dir, sub_system, 'header', 'metadata.xml')
    tree = ET.parse(schema_file)
    db_type = tree.find('database-product-name')

    table_defs = tree.findall('table-def')
    for table_def in table_defs:
        # TODO: Sjekk om disposed lagt til mm i metadata.xml før denne kjører
        disposed = table_def.find('disposed')

        if disposed.text == 'true':
            continue

        table_name = table_def.find('table-name')
        tables.append(table_name.text)

        text_columns = []
        file_columns = []
        column_defs = table_def.findall('column-def')

        for column_def in column_defs:
            column_name = column_def.find('column-name')
            java_sql_type = column_def.find('java-sql-type')
            # TODO: Sjekk på lengde på denne om den skal eskporteres eller ikke?
            # -> hva er originalt navn på felttypen. Kan en bruke det direkte heller?
            # TODO: -> ingen av de sjekkene er god nok-> en må finne maks reell lengde pr kolonne
            column_name_fixed = column_name.text
            if int(java_sql_type.text) == -16 and db_type.text == 'Microsoft SQL Server':
                file_columns.append(column_name_fixed)
                file_name_stem = "'" + table_name.text + "_" + column_name_fixed + "_" + "'"
                column_name_fixed = file_name_stem + ' || ROWNUM() AS "' + column_name_fixed + '"'

            text_columns.append(column_name_fixed)

        if text_columns:
            table_columns[table_name.text] = text_columns

        if file_columns:
            table_columns[table_name.text + '_lobs'] = file_columns

    return tables, table_columns


def export_db_schema(data_dir, sub_system, class_path, bin_dir, memory, sub_systems_dir):
    database_dir = os.path.join(data_dir, 'database')
    jdbc_url = 'jdbc:h2:' + database_dir + os.path.sep + sub_system + ';LAZY_QUERY_EXECUTION=1;TRACE_LEVEL_FILE=0'
    driver_jar = os.path.join(bin_dir, 'vendor', 'jars', 'h2.jar')
    class_paths = class_path + get_java_path_sep() + driver_jar
    batch = wb_batch(class_paths, memory)

    # tables, table_columns = get_tables(driver_class, jdbc_url, driver_jar)
    tables, table_columns = get_tables(sub_systems_dir, sub_system)

    for table in tables:
        if table in table_columns:
            result = export_text_columns(data_dir, batch, jdbc_url, table, table_columns)
            if result == 'Error':
                return result

        if table + '_lobs' in table_columns:
            result = export_lob_columns(data_dir, batch, jdbc_url, table, table_columns)
            if result == 'Error':
                return result

    return tables


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


def dispose_tables(sub_systems_dir, sub_system, tables, tmp_dir):
    schema_file = os.path.join(sub_systems_dir, sub_system, 'header', 'metadata.xml')
    schema_file_raw = os.path.join(sub_systems_dir, sub_system, 'header', 'metadata_raw.xml')

    # Fix any encoding issues:
    # WAIT: Mulig trengtes bare pga av tidligere 'tree.write' uten å spesifisere utf8
    file_convert(schema_file, 'application/xml', 'x2utf8', tmp_dir, tmp_dir, schema_file_raw)
    # os.remove(schema_file)  # WAIT: Linje under skulle overskrevet hvis fil finnes men gjør ikke det
    shutil.move(schema_file_raw, schema_file)

    tree = ET.parse(schema_file)
    table_defs = tree.findall("table-def")
    for table_def in table_defs:
        table_name = table_def.find("table-name")
        disposed = ET.Element("disposed")
        disposed.text = "false"
        if table_name.text not in tables:
            disposed.text = "true"

        table_def.insert(5, disposed)

    root = tree.getroot()
    indent(root)
    tree.write(schema_file, encoding='utf-8')


def normalize_data(project_dir, bin_dir, class_path, java_path, memory, tmp_dir):
    sub_systems_dir = os.path.join(project_dir, 'content', 'sub_systems')
    tika_tmp_dir = os.path.join(tmp_dir, 'tika')

    for sub_system in os.listdir(sub_systems_dir):

        # process db's:
        data_dir = os.path.join(sub_systems_dir, sub_system, 'content', 'data')
        database_dir = os.path.join(data_dir, 'database')
        db_file = os.path.join(database_dir, sub_system + '.mv.db')
        data_docs_dir = os.path.join(sub_systems_dir, sub_system, 'content', 'data_documents_tmp')
        if os.path.isfile(db_file):
            Path(data_docs_dir).mkdir(parents=True, exist_ok=True)

            tables = export_db_schema(data_dir, sub_system, class_path, bin_dir, memory, sub_systems_dir)
            if tables == 'Error':
                return tables

            if tables:
                dispose_tables(sub_systems_dir, sub_system, tables, tmp_dir)
                shutil.rmtree(database_dir)

                for data_file in glob.iglob(data_dir + os.path.sep + '*.data'):
                    shutil.move(data_file, data_docs_dir)

                for text_file in glob.iglob(data_dir + os.path.sep + '*_lobs.txt'):
                    os.remove(text_file)

        return  # TODO: For test. Fjern etterpå

        if len(os.listdir(data_docs_dir)) == 0:
            os.rmdir(data_docs_dir)
        else:
            tsv_file = os.path.join(sub_systems_dir, sub_system, 'header', 'data_documents.tsv')
            if not os.path.isfile(tsv_file):
                run_tika(tsv_file, data_docs_dir, tika_tmp_dir, java_path)

        # process files:
        docs_dir = os.path.join(sub_systems_dir, sub_system, 'content', 'documents')
        files = get_files(('*.wim', '*.tar'), docs_dir)
        for file in files:
            export_dir = os.path.splitext(file)[0]
            Path(export_dir).mkdir(parents=True, exist_ok=True)

            mount_dir = export_dir + '_mount'
            tsv_file = os.path.join(sub_systems_dir, sub_system, 'header', os.path.basename(export_dir) + '_documents.tsv')
            if not os.path.isfile(tsv_file):
                if Path(file).suffix == '.wim':
                    Path(mount_dir).mkdir(parents=True, exist_ok=True)
                    subprocess.run('wimapply ' + str(file) + ' ' + export_dir + ' 2>/dev/null', shell=True)
                    print('Scanning files for viruses...')
                    # WAIT: Egen funksjon for virus sjekk med return verdi
                    subprocess.run('clamdscan -m -v ' + export_dir, shell=True)
                    subprocess.run('wimmount ' + str(file) + ' ' + mount_dir, shell=True)
                else:
                    with tarfile.open(file) as tar:
                        tar.extractall(path=export_dir)

                run_tika(tsv_file, mount_dir, tika_tmp_dir, java_path)

            if os.path.exists(mount_dir):
                subprocess.run('wimunmount --force ' + mount_dir + ' 2>/dev/null', shell=True)

            # TODO: Hva er riktig mappe å konvertere til? Sjekk PWB-kode
            base_target_dir = export_dir + '_normalized'
            tsv_target_path = os.path.splitext(tsv_file)[0] + '_processed.tsv'
            result = convert_folder(project_dir, export_dir, base_target_dir, tmp_dir, java_path, tsv_source_path=tsv_file, tsv_target_path=tsv_target_path)
            print(result)
            # TODO: Må hente ut denne og kobinere med resultat av konvertering av eksporterte lob'er under slik at vises samlet til slutt

            if 'All files converted' in result:
                if os.path.isfile(file):
                    os.remove(file)

                shutil.rmtree(export_dir)
                shutil.move(base_target_dir, export_dir)

        if os.path.exists(docs_dir):
            if len(os.listdir(docs_dir)) == 0:
                os.rmdir(docs_dir)

        if os.path.exists(data_docs_dir):
            if len(os.listdir(data_docs_dir)) == 0:
                os.rmdir(data_docs_dir)
            else:
                export_dir = data_docs_dir
                base_target_dir = data_docs_dir[:-4]
                tsv_file = os.path.join(sub_systems_dir, sub_system, 'header', 'data_documents.tsv')
                tsv_target_path = os.path.splitext(tsv_file)[0] + '_processed.tsv'
                result = convert_folder(project_dir, export_dir, base_target_dir, tmp_dir, java_path, tsv_source_path=tsv_file, tsv_target_path=tsv_target_path)
                print(result)

                if 'All files converted' in result:
                    shutil.rmtree(export_dir)

        for file in files:
            mount_dir = os.path.splitext(file)[0] + '_mount'
            subprocess.run('rm -rdf ' + mount_dir, shell=True)
