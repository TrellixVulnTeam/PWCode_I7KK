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
# import glob
import tarfile
import jaydebeapi
import shutil
from common.jvm import init_jvm, wb_batch
from common.print import print_and_exit
import jpype as jp
import jpype.imports
import xml.etree.ElementTree as ET


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


def get_tables(driver_class, jdbc_url, driver_jar):
    conn = jaydebeapi.connect(driver_class, jdbc_url, ['', ''], driver_jar)
    try:
        curs = conn.cursor()
        curs.execute("SHOW TABLES;")
        data = curs.fetchall()
        tables = [str(x[0]) for x in data]
        table_columns = {}

        for table in tables:
            # Get column names of table:
            # TODO: Finnes db-uavhengig måte å begrense til kun en linje hentet ut?
            get_columns = 'SELECT * from "' + table + '";'
            print(get_columns)
            curs.execute(get_columns)
            table_columns[table] = [str(desc[0]) for desc in curs.description]

    except Exception as e:
        print(e)
        return 'error'

    finally:
        if curs is not None:
            curs.close()
        if conn is not None:
            conn.close()

    return tables, table_columns


def get_java_path_sep():
    path_sep = ';'
    if os.name == "posix":
        path_sep = ':'

    return path_sep


# def export_db_schema(subsystem_dir, s_jdbc, class_path, max_java_heap, export_tables, bin_dir, table_columns, overwrite_tables, DDL_GEN):
def export_db_schema(data_dir, sub_system, class_path, java_path, bin_dir, memory):
    jdbc_url = 'jdbc:h2:' + data_dir + os.path.sep + sub_system + ';LAZY_QUERY_EXECUTION=1'
    driver_class = 'org.h2.Driver'
    driver_jar = os.path.join(bin_dir, 'vendor', 'jars', 'h2.jar')
    class_paths = class_path + get_java_path_sep() + driver_jar
    batch = wb_batch(class_paths, memory, java_path)  # TODO: Heller init_jvm direkte bare her?

    tables, table_columns = get_tables(driver_class, jdbc_url, driver_jar)
    if tables == 'error':
        print_and_exit('Error. No tables in source')

    for table in tables:
        batch.runScript("WbConnect -url='" + jdbc_url + "';")
        tsv_file = os.path.join(data_dir, table + '.tsv')
        # TODO: Hvorfor ha med navn på kolonner i select under? Beholde det? -> ja -> sikrer at får eksportert kolonner med ellers ulovlige navn pga quotes
        # --> TODO: har det som trengs for å hente kolonnenavn mm i koden under -> blir forenklet versjon av det

        source_query = 'SELECT "' + '","'.join(table_columns[table]) + '"  FROM PUBLIC."' + table + '"'

        export_data_list = ["WbExport ",
                            "-type=text ",
                            "-file = " + tsv_file + " ",
                            "-continueOnError = false ",
                            "-encoding=UTF8 ",
                            "-header=true ",
                            "-decimal='.' ",
                            "-maxDigits=0 ",
                            "-lineEnding=lf ",
                            "-clobAsFile=false ",
                            "-blobType=file ",
                            "-delimiter=\t ",
                            "-replaceExpression='(\n|\r\n|\r|\t|^$)' -replaceWith=' ' ",
                            "-nullString=' ' ",
                            "-showProgress=10000 ",
                            ";" + source_query + ";"
                            ]

        export_data_str = ''.join(export_data_list)
        result = batch.runScript(export_data_str)
        batch.runScript("WbDisconnect;")
        jp.java.lang.System.gc()
        if str(result) == 'Error':
            print_and_exit("Error on exporting table '" + table + "'\nScroll up for details.")

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


def dispose_tables(sub_systems_dir, sub_system, tables):
    schema_file = os.path.join(sub_systems_dir, sub_system, 'header', 'metadata.xml')
    schema_file_raw = os.path.join(sub_systems_dir, sub_system, 'header', 'metadata_raw.xml')

    shutil.copyfile(schema_file, schema_file_raw)

    tree = ET.parse(schema_file_raw)
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
    tree.write(schema_file)


def process(project_dir, bin_dir, class_path, java_path, memory):
    sub_systems_dir = os.path.join(project_dir, 'content', 'sub_systems')

    for sub_system in os.listdir(sub_systems_dir):
        # process db's:
        data_dir = os.path.join(sub_systems_dir, sub_system, 'content', 'data')
        h2_file = os.path.join(data_dir, sub_system + '.mv.db')
        if os.path.isfile(h2_file):
            data_docs_dir = os.path.join(sub_systems_dir, sub_system, 'content', 'data_documents')
            Path(data_docs_dir).mkdir(parents=True, exist_ok=True)

            tables = export_db_schema(data_dir, sub_system, class_path, java_path, bin_dir, memory)
            if tables:
                dispose_tables(sub_systems_dir, sub_system, tables)
                os.remove(h2_file)
                # TODO: Flytt exporterte blob'er

        # process files:
        docs_dir = os.path.join(sub_systems_dir, sub_system, 'content', 'documents')
        files = get_files(('*.wim', '*.tar'), docs_dir)
        for file in files:
            export_dir = os.path.splitext(file)[0]
            Path(export_dir).mkdir(parents=True, exist_ok=True)

            if len(os.listdir(export_dir)) != 0:
                continue

            # TODO: Skal vel mountes her? Def over og ikke wimapply?
            if Path(file).suffix == '.wim':
                subprocess.run("wimapply " + file + " " + export_dir, shell=True)
            else:
                with tarfile.open(file) as tar:
                    tar.extractall(path=export_dir)

            os.remove(file)

    return 'endre denne'
