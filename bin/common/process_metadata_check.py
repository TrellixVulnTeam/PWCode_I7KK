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

import subprocess
import os
import sys
import shutil
import pathlib
from functools import reduce
# from configparser import SafeConfigParser


def load_data(project_dir, config_dir):
    sub_systems_dir = os.path.join(project_dir, 'content', 'sub_systems')
    # config = SafeConfigParser()
    # tmp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tmp'))
    ora_reset_script = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sql/oracle_reset.sql'))
    tsv2sqlite_script = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tsv2sqlite.py'))
    tsv2mssql_script = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tsv2mssql.py'))
    # conf_file = tmp_dir + "/pwb.ini"
    # config.read(conf_file)
    # data_dir = os.path.abspath(os.path.join(tmp_dir, '../../', '_DATA'))
    # filepath = config.get('ENV', 'wim_path')
    # sys_name = os.path.splitext(os.path.basename(filepath))[0]
    # mount_dir = data_dir + "/" + sys_name + "_mount"
    db_list = ['postgresql', 'oracle', 'mssql', 'sqlite']

    # if not filepath:
    #     exit()

    # WAIT: Lag også powershell eller vbs-versjon for windows
    # WAIT: Endre så henter filplassering auto og resten av paths relativt (som i arkimint)
    def gen_import_file(db):
        ln = [
            '#!/bin/bash \n', '# -- ' + str(db) + ' --',
            '# -- modify variables as needed before running import script -- \n',
            '# -- Variables --', 'user=' + users[db],
            'password=' + passwords[db], 'host=localhost',
            'schema=' + schemas[db], 'db_name=' + db_names[db],
            'sql_bin=' + sql_bin[db], 'import_bin=' + import_bins[db],
            'import_order_file=' + import_order_file, 'data_path=' + data_path,
            'reset_file=' + reset_files[db],
            'ddl_file=' + ddl_files[db] + '\n', '# -- Code --',
            reset_before_statements[db], create_schema_statements[db],
            'while IFS= read -r table', 'do', import_statements[db],
            'done < "$import_order_file"'
        ]

        with open(os.open(import_sql_files[db], os.O_CREAT | os.O_WRONLY, 0o777), 'w') as file:
            file.write("\n".join(ln))

    subfolders = os.listdir(sub_systems_dir)
    for folder in subfolders:
        base_path = os.path.join(sub_systems_dir, folder)
        header_xml_file = os.path.join(base_path, 'header', 'metadata.xml')
        data_path = base_path + "/content/data/"

        if os.path.isfile(header_xml_file) and os.listdir(data_path):
            documentation_folder = os.path.join(base_path, 'documentation')
            import_order_file = os.path.join(documentation_folder, 'import_order.txt')
            sqlite_db = "/tmp/" + folder + ".db"

            order_list = []
            with open(import_order_file) as file:
                for cnt, line in enumerate(file):
                    order_list.append(line.rstrip())

            users = {}
            sql_bin = {}
            import_bins = {}
            passwords = {}
            schemas = {}
            db_names = {}
            done_files = {}  # WAIT: Skriv til config fil heller
            import_sql_files = {}
            reset_before_statements = {}
            reset_after_statements = {}
            create_schema_statements = {}
            ddl_files = {}
            reset_files = {}
            import_statements = {}

            for db in db_list:
                pathlib.Path(os.path.join(documentation_folder, db + '_import')).mkdir(parents=True, exist_ok=True)
                done_files[db] = os.path.join(documentation_folder, db + '_done')
                import_sql_files[db] = os.path.join(documentation_folder, db + '_import', 'import.sh')

                if db in ('postgresql', 'sqlite', 'mssql'):
                    reset_files[db] = ' #Not needed for ' + db
                else:
                    reset_files[db] = os.path.join(documentation_folder, db + '_import, reset_' + db + '.sql')

                if db == 'postgresql':
                    users[db] = 'postgres'
                    passwords[db] = 'P@ssw0rd'
                    schemas[db] = 'pwb #Any existing tables in schema will be deleted by first line in code'
                    db_names[db] = ' #Not needed for postgresql'
                    sql_bin[db] = '/usr/bin/psql'
                    import_bins[db] = '/usr/bin/psql'
                    ddl_files[db] = os.path.join(documentation_folder, 'metadata.sql')
                    reset_before_statements[db] = 'PGOPTIONS="--client-min-messages=warning" $sql_bin "user=$user password=$password host=$host" -q -c "DROP SCHEMA IF EXISTS $schema CASCADE;"'
                    reset_after_statements[db] = sql_bin[db] + ' "user=' + users[db] + ' password=' + passwords[db] + ' host=localhost" -q -c "DROP SCHEMA IF EXISTS pwb CASCADE;"'
                    create_schema_statements[db] = '$sql_bin "user=$user password=$password host=$host" -q -c "CREATE SCHEMA $schema; SET search_path TO $schema;" -f $ddl_file'
                    import_statements[db] = '''$import_bin "user=$user password=$password host=$host" -v "ON_ERROR_STOP=1" -c "\copy \"$schema\".\"$table\" FROM \"$data_path\"\"$table\".tsv delimiter E'\\t' CSV HEADER QUOTE E'\\b' NULL AS ''"'''

                if db == 'oracle':
                    shutil.copyfile(ora_reset_script, os.path.join(documentation_folder, db + '_import', 'reset_oracle.sql'))
                    users[db] = 'oracle'
                    passwords[db] = 'pwb'
                    schemas[db] = 'oracle #Any existing tables in schema will be deleted by first line in code'
                    db_names[db] = ' #Not needed for oracle'
                    sql_bin[db] = '/u01/app/oracle/product/11.2.0/xe/bin/sqlplus'
                    import_bins[db] = '/u01/app/oracle/product/11.2.0/xe/bin/sqlldr'
                    ddl_files[db] = os.path.join(documentation_folder, db + '_import', 'metadata_' + db + '.sql')
                    reset_before_statements[db] = '$sql_bin -S $user/$password@$host < $reset_file'
                    reset_after_statements[db] = sql_bin[db] + ' -S ' + users[db] + '/' + passwords[db] + '@localhost < ' + reset_files[db]
                    create_schema_statements[db] = '$sql_bin -S $user/$password@$host < $ddl_file'
                    import_statements[db] = '$import_bin $user/$password@$host errors=0 skip=1 bindsize=20000000 readsize=20000000 direct=true control="$table".ctl data="$data_path""$table".tsv'
                    repls = (
                        (" text,", " clob,"),
                        (" text)", " clob)"),
                        (" varchar(4000)", " clob"),
                        (" varchar2(4000)", " clob"),
                        # (" boolean", " varchar2(5)"),
                        (" varchar(", " varchar2("),
                    )

                    with open(ddl_files[db], "w") as file:
                        with open(ddl_files['postgresql'], 'r') as file_r:
                            file.write(
                                "ALTER SESSION SET NLS_LENGTH_SEMANTICS=CHAR;\n\n"
                            )
                            for line in file_r:
                                file.write(reduce(lambda a, kv: a.replace(*kv), repls, line))

                if db == 'mssql':  # WAIT: Kjør denne først ved test: sudo systemctl restart mssql-server
                    users[db] = 'sa'
                    passwords[db] = 'P@ssw0rd'
                    schemas[db] = ' #Default schema of user on mssql'
                    db_names[db] = 'pwb #Any existing tables in database will be deleted by first line in code'
                    sql_bin[db] = '/opt/mssql-tools/bin/sqlcmd'
                    # import_bins[db] = '/opt/mssql-tools/bin/bcp'
                    import_bins[db] = 'freebcp'
                    ddl_files[db] = os.path.join(documentation_folder, db + '_import', 'metadata_' + db + '.sql')
                    reset_before_statements[db] = '$sql_bin -b -U $user -P $password -H $host -d master -Q \"DROP DATABASE IF EXISTS $db_name; CREATE DATABASE $db_name\"'
                    reset_after_statements[db] = sql_bin[db] + ' -b -U ' + users[db] + ' -P ' + passwords[db] + ' -H localhost -d master -Q "DROP DATABASE IF EXISTS pwb;"'
                    create_schema_statements[db] = '$sql_bin -b -U $user -P $password -H $host -d $db_name -i $ddl_file'
                    import_statements[db] = 'echo "importing $table...."; $import_bin $table in "$data_path""$table".tsv -U $user -P $password -D $db_name -S $host -F 2 -c'
                    # TODO: Test linjen under på windows (må legge til encodingvalg som ikke støttes på linux da)
                    # db] = 'echo "importing" $table "...."; $import_bin $table in "$data_path""$table".tsv -U $user -P $password -d $db_name -S $host -r 0x0a -F 2 -c'

                    repls = (
                        (" timestamp", " datetime2"),
                        # (" varchar(", " nvarchar("),
                        # (" decimal", " numeric"),
                        # (" text,", " varchar(max),"),
                        # (" text)", " varchar(max))"),
                        #    (" boolean", " varchar(5)"),
                        #  (" bigint", " numeric"), #TODO: Ser ikke ut til at bigint kan ha desimaler i alle dbtyper
                    )

                    with open(ddl_files[db], "w") as file:
                        with open(ddl_files['postgresql'], 'r') as file_r:
                            file.write(
                                # "ALTER DATABASE CURRENT COLLATE Norwegian_100_CS_AS;\n\n"
                                # "ALTER DATABASE CURRENT COLLATE Norwegian_100_CS_AS_WS;\n\n"
                                "ALTER DATABASE CURRENT COLLATE Latin1_General_100_CS_AS_WS_SC_UTF8;\n\n"
                                # "ALTER DATABASE CURRENT COLLATE Norwegian_100_CS_AS_SC;\n\n"
                                # "ALTER DATABASE CURRENT COLLATE Norwegian_100_CS_AS_WS_SC_UTF8;\n\n"
                            )
                            for line in file_r:
                                file.write(
                                    reduce(lambda a, kv: a.replace(*kv), repls,
                                           line))

                if db == 'sqlite':
                    shutil.copyfile(tsv2sqlite_script, os.path.join(documentation_folder, db + '_import', 'tsv2sqlite.py'))
                    users[db] = ' #Not needed for sqlite'
                    passwords[db] = ' #Not needed for sqlite'
                    schemas[db] = ' #Not needed for sqlite'
                    db_names[db] = '/tmp/pwb.db #Name and path of created db-file. Deleted first on rerun'
                    sql_bin[db] = '/usr/bin/sqlite3'
                    import_bins[db] = '"python3 tsv2sqlite.py"'
                    ddl_files[db] = os.path.join(documentation_folder, 'metadata.sql')
                    reset_before_statements[db] = 'rm "$db_name" 2> /dev/null'
                    reset_after_statements[db] = 'echo "*********************************** \n All databases imported successfully"'
                    create_schema_statements[db] = '$sql_bin "$db_name" < $ddl_file'
                    import_statements[db] = '$import_bin $table $data_path$table.tsv $db_name'

                gen_import_file(db)

            # TODO: Lag egen def for suprocess heller. Bedre sjekker før 'done', og 'done' til config-fil heller enn separate filer
            for db in db_list:
                if not os.path.isfile(done_files[db]):
                    try:
                        subprocess.check_call(
                            import_sql_files[db],
                            shell=True,
                            cwd=os.path.join(documentation_folder, db + '_import'))
                    except subprocess.CalledProcessError:
                        # pass # handle errors in the called executable
                        break
                    except OSError:
                        pass
                    else:
                        subprocess.call(
                            'touch ' + done_files[db],
                            shell=True,
                            cwd=os.path.join(documentation_folder, db + '_import'))
                        subprocess.call(
                            reset_after_statements[db],
                            shell=True,
                            cwd=os.path.join(documentation_folder, db + '_import'))

                    sys.stdout.flush()
