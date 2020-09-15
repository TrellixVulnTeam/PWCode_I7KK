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
from common.jvm import init_jvm, wb_batch


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


def get_tables(driver_class,jdbc_url,driver_jar):
    conn = jaydebeapi.connect(driver_class,jdbc_url,['', ''], driver_jar)
    try:
        curs = conn.cursor()
        curs.execute("SHOW TABLES;")
        data = curs.fetchall()
        tables = [x[0] for x in data]

    except Exception as e:
        print(e)
        return 'error'

    finally:
        if curs is not None:
            curs.close()
        if conn is not None:
            conn.close()

    return tables            


# def export_db_schema(subsystem_dir, s_jdbc, class_path, max_java_heap, export_tables, bin_dir, table_columns, overwrite_tables, DDL_GEN):
def export_db_schema(data_dir, sub_system, class_path, bin_dir, memory):
    jdbc_url = 'jdbc:h2:' + data_dir + sub_system + ';LAZY_QUERY_EXECUTION=1'
    driver_class = 'org.h2.Driver'    
    driver_jar = bin_dir + '/vendor/jdbc/h2-1.4.200.jar' # WAIT: Fjern hardkoding av denne
    batch = wb_batch(class_path, memory)
    # batch.runScript("WbConnect -url='" + jdbc_url + "';")

    tables = get_tables(driver_class,jdbc_url,driver_jar)
    if tables == 'error':
        return 'not workee'

    for table in tables:
        batch.runScript("WbConnect -url='" + jdbc_url + "';")
        copy_data_str = "WbCopy -targetConnection=" + target_conn + " -targetSchema=PUBLIC -targetTable=" + target_table + " -sourceQuery=" + source_query + ";"
        result = batch.runScript(copy_data_str)
        # target_table = '"' + table + '"'
        result = batch.runScript(copy_data_str)
        batch.runScript("WbDisconnect;")
        jp.java.lang.System.gc()
        if str(result) == 'Error':
            print_and_exit("Error on copying table '" + table + "'\nScroll up for details.")




    return 



    jdbc = Jdbc(url, DB_USER, DB_PASSWORD, DB_NAME, DB_SCHEMA, driver_jar, driver_class, True, True)








    return 'så langt'




    target_url = 'jdbc:h2:' + subsystem_dir + '/content/data/' + s_jdbc.db_name + '_' + s_jdbc.db_schema + ';autocommit=off'
    target_url, driver_jar, driver_class = get_db_details(target_url, bin_dir)
    t_jdbc = Jdbc(target_url, '', '', '', 'PUBLIC', driver_jar, driver_class, True, True)
    target_tables = get_target_tables(t_jdbc)
    # pk_dict = get_primary_keys(subsystem_dir, export_tables)
    # unique_dict = get_unique_indexes(subsystem_dir, export_tables)
    blob_columns = get_blob_columns(subsystem_dir, export_tables)


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


def process(project_dir, bin_dir, class_path, memory):
    sub_systems_dir = project_dir + '/content/sub_systems/' 


    for sub_system in os.listdir(sub_systems_dir): 
        #process db's:
        data_dir = sub_systems_dir + sub_system + "/content/data/"
        h2_file = data_dir + sub_system + ".mv.db" 
        if os.path.isfile(h2_file):
            data_docs_dir = sub_systems_dir + sub_system + "/content/data_documents/"
            Path(data_docs_dir).mkdir(parents=True, exist_ok=True) 
            export_db_schema(data_dir, sub_system, class_path, bin_dir, memory)       
        


        #process files:
        docs_dir = sub_systems_dir + sub_system + "/content/documents" 
        files = get_files(('*.wim', '*.tar'), docs_dir)
        for file in files: 
            export_dir = os.path.splitext(file)[0]
            Path(export_dir).mkdir(parents=True, exist_ok=True)

            if len(os.listdir(export_dir)) != 0:
                continue

            if Path(file).suffix == '.wim':
                subprocess.run("wimapply " + file + " " + export_dir, shell=True)
            else:
                with tarfile.open(file) as tar:
                    tar.extractall(path=export_dir)

            os.remove(file)   

    return 'endre denne'    




    # sub_systems_dir = project_dir + '/content/sub_systems'
    # extracted = False
    # if os.path.isdir(sub_systems_dir):
    #     if len(os.listdir(sub_systems_dir)) != 0:
    #         extracted = True

    # if not extracted:            
    #     with tarfile.open(archive) as tar:
    #         tar.extractall(path=project_dir)   


    # for dir in os.listdir(sub_systems_dir):
    #     # system_name = os.path.basename(SYSTEM_DIR)
    #     # documentation_dir = sub_systems_dir + "/" + dir + "/documentation/"
    #     data_docs_dir = sub_systems_dir + "/" + dir + "/content/data_documents"
    #     docs_dir = sub_systems_dir + "/" + dir + "/content/documents"
    #     data_dir = sub_systems_dir + "/" + dir + "/content/data"
    #     h2_file = data_dir + dir + ".mv.db" 
    #     # schema_file = sub_systems_dir + "/" + dir + "/documentation/metadata_mod.xml"
    #     # header_schema_file = sub_systems_dir + "/" + dir + "/header/metadata.xml"

    #     # TODO: Sjekk først i xml-fil om db og eller filuttrekk slik at ikke lager tommme mapper
    #     for dir in [data_docs_dir, data_dir, docs_dir]:
    #         Path(dir).mkdir(parents=True, exist_ok=True)

    #     files = get_files(('*.wim', '*.tar'), docs_dir)
    #     for file in files:
    #         export_dir = os.path.splitext(file)[0]
    #         Path(export_dir).mkdir(parents=True, exist_ok=True)

    #         if len(os.listdir(export_dir)) != 0:
    #             continue

    #         if Path(file).suffix == '.wim':
    #             subprocess.run("wimapply " + file + " " + export_dir, shell=True)
    #         else:
    #             with tarfile.open(file) as tar:
    #                 tar.extractall(path=export_dir)

    #         os.remove(file)

        # h2_export(h2_file)   # TODO: Test om denne koden ferdig -> nei

    # subdir_and_files = [
    #     tarinfo for tarinfo in tar.getmembers()
    #     if tarinfo.name.startswith("subfolder/")
    # ]
    # tar.extractall(members=subdir_and_files)







    # mount_wim(archive, project_extracted_dir)  # TODO: Legg inn støtte for tar også
    # sql_file = tmp_dir + "/file_process.sql"
    # in_dir = os.path.dirname(filepath) + "/"
    # sys_name = os.path.splitext(os.path.basename(filepath))[0]
    # project_extracted_dir = data_dir + "/" + sys_name + "_mount"
    # av_done_file = in_dir + sys_name + "_av_done"

    # open(tmp_dir + "/PWB.log", 'w').close()  # Clear log file
    # open(sql_file, 'w').close()  # Blank out between runs







def h2_export(h2_file):
    print(h2_file)
    return

    h2_done_file = documentation_dir + "done"  # TODO: bruk config
    if (os.path.isfile(h2_file + ".mv.db")
            and not os.path.isfile(h2_done_file)):
        conn = jaydebeapi.connect(  # WAIT: Endre til egen def
            "org.h2.Driver",
            "jdbc:h2:" + h2_file,
            ["", ""],
            bin_dir +
            "/h2-1.4.196.jar",  # WAIT: Fjern harkodet filnavn
        )

        try:
            curs = conn.cursor()
            curs.execute("SHOW TABLES;")
            data = curs.fetchall()
            tables_in_h2 = [x[0] for x in data]

        except Exception as e:
            print(e)

        finally:
            if curs is not None:
                curs.close()
            if conn is not None:
                conn.close()

        tree = ET.parse(header_xml_file)
        table_defs = tree.findall("table-def")
        for table_def in table_defs:
            table_name = table_def.find("table-name")
            disposed = ET.Element("disposed")
            disposed.text = "false"
            if table_name.text not in tables_in_h2:
                disposed.text = "true"

            table_def.insert(5, disposed)

        root = tree.getroot()
        indent(root)
        tree.write(mod_xml_file)

        xsl = [
            "\n",
            "WbXslt -inputfile=" + mod_xml_file,
            "-stylesheet=" + h2_to_tsv_script,
            '-xsltParameters="url=jdbc:h2:' + h2_file + '"',
            '-xsltParameters="outputdir=' + data_folder + '"',
            "-xsltOutput=" + wbexport_script + ';',
        ]
        with open(tmp_dir + '/h2_to_tsv.sql', "w") as file:
            file.write("\n".join(xsl))

        # TODO: Lag subprocess def som kalles to ganger her med forskjellige parametre
        cmd = 'java -jar sqlworkbench.jar -script=' + tmp_dir + '/h2_to_tsv.sql'
        returncode, stdout, stderr = run_shell_command(cmd, bin_dir)
        print(stdout)

        cmd = 'java -jar sqlworkbench.jar -script=' + tmp_dir + '/wbexport.sql'
        returncode, stdout, stderr = run_shell_command(cmd, bin_dir)
        print(stdout)

        open(h2_done_file, 'a').close()
