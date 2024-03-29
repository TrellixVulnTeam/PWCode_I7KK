# Copyright (C) 2021 Morten Eek

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
import fnmatch
import tarfile
import shutil
from common.jvm import wb_batch
import jpype as jp
import xml.etree.ElementTree as ET
from common.metadata import run_tika
from common.database import run_select
from database.jdbc import Jdbc
from common.convert import convert_folder, file_convert
from common.xml import merge_xml_element


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


def export_lob_columns(data_dir, batch, jdbc_url, table, table_columns, schema):
    txt_file = os.path.join(data_dir, table + '_lobs.txt')
    for column in table_columns[table + '_lobs']:
        file_name = "'" + table.lower() + "_" + column.lower() + "_" + "'" + " || rownum() || '.data'"
        # condition = f'''WHERE NULLIF("{column}", '') IS NOT NULL'''
        source_query = 'SELECT "' + column + '",' + file_name + ' as fname FROM "' + schema + '"."' + table + '"'  # + condition
        # TODO: Må legge inn oppdatering av felt i tsv-fil slik at referanse til filnavn ikke finnes for de feltene som ikke har fil på disk
        # --> gjøre det ifm oppdatering av felt etter normalisering av filer?

        export_data_list = ["WbExport ",
                            "-type=text ",
                            "-file = " + txt_file + " ",
                            "-continueOnError=false ",
                            "-encoding=UTF8 ",
                            "-clobAsFile=true ",
                            "-blobtype=file ",
                            "-showProgress=10000 ",
                            "-filenameColumn=fname ",
                            ";" + source_query + ";"
                            ]

        batch.runScript("WbConnect -url='" + jdbc_url + "';")
        result = batch.runScript(''.join(export_data_list))
        batch.runScript("WbDisconnect;")
        jp.java.lang.System.gc()

    return str(result)


def export_text_columns(data_dir, batch, jdbc_url, table, table_columns, schema):
    batch.runScript("WbConnect -url='" + jdbc_url + "';")
    txt_file = os.path.join(data_dir, table + '.txt')
    columns = table_columns[table]

    for index, column in enumerate(columns):
        if '|| ROWNUM() AS' not in column:
            columns[index] = '"' + column + '"'

    source_query = 'SELECT ' + ','.join(columns) + ' FROM "' + schema + '"."' + table + '"'
    export_data_list = ["WbExport ",
                        "-type=text ",
                        "-file=" + txt_file + " ",
                        "-continueOnError=false ",
                        "-encoding=UTF8 ",
                        "-header=true ",
                        "-decimal='.' ",
                        "-maxDigits=0 ",
                        "-lineEnding=lf ",
                        "-clobAsFile=false ",
                        "-blobtype=base64 ",
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


def get_tables(sub_systems_dir, sub_system, jdbc_url, driver_jar, schema):
    tables = []
    table_columns = {}
    schema_file = os.path.join(sub_systems_dir, sub_system, 'header', 'metadata.xml')
    tree = ET.parse(schema_file)

    jdbc = Jdbc(jdbc_url, '', '', '', schema, driver_jar, 'org.h2.Driver', True, True)
    table_query = f"""SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{schema}'"""
    tables_h2 = run_select(jdbc, table_query)
    tables_h2 = [x[0] for x in tables_h2]

    table_defs = tree.findall('table-def')
    for table_def in table_defs:
        table_schema = table_def.find('table-schema')
        if table_schema.text != schema:
            continue

        disposed = table_def.find('disposed')
        if disposed is not None:
            if disposed.text == 'true':
                continue

        table_name = table_def.find('table-name')
        if table_name.text not in tables_h2:
            continue

        tables.append(table_name.text)

        text_columns = []
        file_columns = []
        column_defs = table_def.findall('column-def')
        column_defs[:] = sorted(column_defs, key=lambda elem: int(elem.findtext('dbms-position')))

        for column_def in column_defs:
            column_name = column_def.find('column-name')
            java_sql_type = int(column_def.find('java-sql-type').text)
            dbms_data_size = int(column_def.find('dbms-data-size').text)
            column_name_fixed = column_name.text.upper()

            # -> Disse regnes som blob: 2004, -4, -3, -2
            # Clob'er: -16, -1, 2005, 2011

            if java_sql_type in (-4, -3, -2, 2004, 2005, 2011, -16, -1):
                if (dbms_data_size > 4000 or java_sql_type in (2004, -4, -3, -2)):
                    length_query = f'''SELECT MAX(LENGTH("{column_name_fixed}")) FROM "{schema}"."{table_name.text}"'''
                    jdbc = Jdbc(jdbc_url, '', '', '', schema, driver_jar, 'org.h2.Driver', True, True)
                    result = run_select(jdbc, length_query)
                    max_length = [x[0] for x in result][0]

                    # TODO: Endre senere her slik at tomme felt ikke skrives til text_columns så fjernes i tsv
                    # -> Må legge inn 'disposed' på kolonne da og ha sjekk mot det i annen kode så det blir riktg ved opplasting
                    if max_length is not None:
                        if max_length > 4000:
                            file_columns.append(column_name_fixed)
                            # TODO: Mulig å endre til normalisert filnavn direkte her?
                            file_name_stem = "'" + str(table_name.text).lower() + "_" + str(column_name_fixed).lower() + "_" + "'"
                            column_name_fixed = file_name_stem + ' || ROWNUM() AS "' + column_name_fixed + '"'

            text_columns.append(column_name_fixed)

        if text_columns:
            table_columns[table_name.text] = text_columns

        if file_columns:
            table_columns[table_name.text + '_lobs'] = file_columns

    return tables, table_columns


def get_schemas(sub_systems_dir, sub_system):
    schemas = []
    schema_file = os.path.join(sub_systems_dir, sub_system, 'header', 'metadata.xml')
    tree = ET.parse(schema_file)

    table_defs = tree.findall('table-def')
    for table_def in table_defs:
        table_schema = table_def.find('table-schema')
        if table_schema.text is not None and table_schema.text not in schemas:
            schemas.append(table_schema.text)

    if not schemas:
        schemas.append('PUBLIC')

    return schemas


def export_db_schema(data_dir, sub_system, class_path, bin_dir, memory, sub_systems_dir, schema, db_file):
    jdbc_url = 'jdbc:h2:' + db_file[:-6] + ';LAZY_QUERY_EXECUTION=1;TRACE_LEVEL_FILE=0'
    driver_jar = os.path.join(bin_dir, 'vendor', 'jars', 'h2.jar')
    class_paths = class_path + get_java_path_sep() + driver_jar
    batch = wb_batch(class_paths, memory)
    tables, table_columns = get_tables(sub_systems_dir, sub_system, jdbc_url, driver_jar, schema)

    Path(data_dir).mkdir(parents=True, exist_ok=True)

    for table in tables:
        if table in table_columns:
            result = export_text_columns(data_dir, batch, jdbc_url, table, table_columns, schema)
            if result == 'Error':
                return result

        if table + '_lobs' in table_columns:
            result = export_lob_columns(data_dir, batch, jdbc_url, table, table_columns, schema)
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
    # TODO: Denne kalles ikke lenger. Kan den fjernes?
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

        value = 'false'
        if table_name.text not in tables:
            value = 'true'

        merge_xml_element(table_def, 'disposed', value, 5)

    root = tree.getroot()
    indent(root)
    tree.write(schema_file, encoding='utf-8')


def get_db_file(database_dir, db_path):
    if os.path.isdir(database_dir):
        for file_name in os.listdir(database_dir):
            file_path = os.path.join(database_dir, file_name)
            if fnmatch.fnmatch(file_path, db_path):
                return file_path


def normalize_data(project_dir, bin_dir, class_path, memory, tmp_dir, convert):
    sub_systems_dir = os.path.join(project_dir, 'content', 'sub_systems')
    tika_tmp_dir = os.path.join(tmp_dir, 'tika')
    all_done = True

    print('Normalizing data...')

    for sub_system in os.listdir(sub_systems_dir):

        # process db's:
        database_dir = os.path.join(sub_systems_dir, sub_system, 'content', 'database')
        db_path = os.path.join(database_dir, '*.mv.db')
        db_file = get_db_file(database_dir, db_path)

        if db_file:
            schemas = get_schemas(sub_systems_dir, sub_system)

            for schema in schemas:
                print("Processing schema '" + schema + "'...")
                data_dir = os.path.join(sub_systems_dir, sub_system, 'content', schema.lower(), 'data')
                Path(data_dir).mkdir(parents=True, exist_ok=True)
                if len(os.listdir(data_dir)) > 0:
                    continue

                data_docs_dir = os.path.join(sub_systems_dir, sub_system, 'content', schema.lower(), 'data_documents_tmp')
                Path(data_docs_dir).mkdir(parents=True, exist_ok=True)
                print("Exporting schema: '" + schema + "' to disk...")

                tables = export_db_schema(data_dir, sub_system, class_path, bin_dir, memory, sub_systems_dir, schema, db_file)
                if tables == 'Error':
                    print(tables)
                    return False

                for data_file in glob.iglob(data_dir + os.path.sep + '*.data'):
                    if os.path.getsize(data_file) == 0:
                        os.remove(data_file)
                    else:
                        shutil.move(data_file, data_docs_dir)

                for text_file in glob.iglob(data_dir + os.path.sep + '*_lobs.txt'):
                    os.remove(text_file)

                if os.path.isdir(data_docs_dir):
                    if len(os.listdir(data_docs_dir)) == 0:
                        os.rmdir(data_docs_dir)
                    else:
                        tsv_file = os.path.join(sub_systems_dir, sub_system, 'header', 'data_documents.tsv')
                        if not os.path.isfile(tsv_file):
                            run_tika(tsv_file, data_docs_dir, tika_tmp_dir)

            # shutil.rmtree(database_dir)

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
                    # WAIT: Egne funksjoner for virussjekk og win-kommandoer med return verdi som sjekkes
                    subprocess.run('clamdscan -m -v ' + export_dir, shell=True)
                    subprocess.run('wimmount ' + str(file) + ' ' + mount_dir, shell=True)
                else:
                    with tarfile.open(file) as tar:
                        def is_within_directory(directory, target):
                            
                            abs_directory = os.path.abspath(directory)
                            abs_target = os.path.abspath(target)
                        
                            prefix = os.path.commonprefix([abs_directory, abs_target])
                            
                            return prefix == abs_directory
                        
                        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                        
                            for member in tar.getmembers():
                                member_path = os.path.join(path, member.name)
                                if not is_within_directory(path, member_path):
                                    raise Exception("Attempted Path Traversal in Tar File")
                        
                            tar.extractall(path, members, numeric_owner=numeric_owner) 
                            
                        
                        safe_extract(tar, path=export_dir)

                run_tika(tsv_file, mount_dir, tika_tmp_dir)

            if os.path.exists(mount_dir):
                subprocess.run('wimunmount --force ' + mount_dir + ' 2>/dev/null', shell=True)

            sample = False
            if convert in ('Yes', 'Sample'):
                if convert == 'Sample':
                    sample = True

                base_target_dir = export_dir + '_normalized'
                tsv_target_path = os.path.splitext(tsv_file)[0] + '_processed.tsv'
                msg, file_count, errors, originals = convert_folder(export_dir, base_target_dir, tmp_dir, tsv_source_path=tsv_file, tsv_target_path=tsv_target_path, sample=sample, merge=True)
                print(msg)

                # TODO: Må hente ut denne og kobinere med resultat av konvertering av eksporterte lob'er under slik at vises samlet til slutt

                if not sample:
                    if 'All files converted' in msg:
                        if os.path.isfile(file):
                            os.remove(file)

                        shutil.rmtree(export_dir)
                        shutil.move(base_target_dir, export_dir)
                    else:
                        all_done = False

        if os.path.exists(docs_dir):
            if len(os.listdir(docs_dir)) == 0:
                os.rmdir(docs_dir)

        if db_file:
            schemas = get_schemas(sub_systems_dir, sub_system)
            for schema in schemas:
                # TODO: Trenger navnestandard for tsv-fil som er skjema-avhengig? -> vil ikke virke hvis flere skjema har blob'er ellers
                data_docs_dir = os.path.join(sub_systems_dir, sub_system, 'content', schema.lower(), 'data_documents_tmp')
                if os.path.exists(data_docs_dir):
                    if len(os.listdir(data_docs_dir)) == 0:
                        os.rmdir(data_docs_dir)
                    else:
                        sample = False
                        if convert in ('Yes', 'Sample'):
                            if convert == 'Sample':
                                sample = True

                            export_dir = data_docs_dir
                            base_target_dir = data_docs_dir[:-4]
                            tsv_file = os.path.join(sub_systems_dir, sub_system, 'header', 'data_documents.tsv')
                            tsv_target_path = os.path.splitext(tsv_file)[0] + '_processed.tsv'
                            msg, file_count, errors, originals = convert_folder(export_dir, base_target_dir, tmp_dir, tsv_source_path=tsv_file,
                                                                                tsv_target_path=tsv_target_path, make_unique=False, sample=sample)
                            print(msg)

                            if not sample:
                                if 'All files converted' in msg:
                                    shutil.rmtree(export_dir)
                                else:
                                    all_done = False

        for file in files:
            mount_dir = os.path.splitext(file)[0] + '_mount'
            subprocess.run('rm -rdf ' + mount_dir, shell=True)

    return all_done
