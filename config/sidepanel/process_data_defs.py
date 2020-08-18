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


def mount_wim(filepath, mount_dir):
    Path(mount_dir).mkdir(parents=True, exist_ok=True)
    if len(os.listdir(mount_dir)) == 0:
        subprocess.run(
            "GVFS_DISABLE_FUSE=1; export GVFS_DISABLE_FUSE; wimmountrw --allow-other "
            + filepath + " " + mount_dir,
            shell=True)


def process(mount_dir, archive_format, archive_path):
    mount_wim(archive_path, mount_dir)  # TODO: Legg inn støtte for tar også
    # sql_file = tmp_dir + "/file_process.sql"
    # in_dir = os.path.dirname(filepath) + "/"
    # sys_name = os.path.splitext(os.path.basename(filepath))[0]
    # mount_dir = data_dir + "/" + sys_name + "_mount"
    # av_done_file = in_dir + sys_name + "_av_done"

    # open(tmp_dir + "/PWB.log", 'w').close()  # Clear log file
    # open(sql_file, 'w').close()  # Blank out between runs

    sub_systems_path = mount_dir + "/content/sub_systems"
    for dir in os.listdir(sub_systems_path):
        # system_name = os.path.basename(SYSTEM_DIR)
        documentation_dir = sub_systems_path + "/" + dir + "/documentation/"
        h2_file = documentation_dir + dir + ".mv.db"
        data_docs_dir = sub_systems_path + "/" + dir + "/content/data_documents"
        docs_dir = sub_systems_path + "/" + dir + "/content/documents"
        data_dir = sub_systems_path + "/" + dir + "/content/data"
        schema_file = sub_systems_path + "/" + dir + "/documentation/metadata_mod.xml"
        header_schema_file = sub_systems_path + "/" + dir + "/header/metadata.xml"

        for dir in [data_docs_dir, data_dir, docs_dir]:
            Path(dir).mkdir(parents=True, exist_ok=True)

        for file in glob.glob(docs_dir + "/*." + archive_format):
            export_dir = os.path.splitext(file)[0]
            Path(export_dir).mkdir(parents=True, exist_ok=True)
            if len(os.listdir(export_dir)) == 0:
                subprocess.run("wimapply " + file + " " + export_dir, shell=True)  # TODO: Legg inn støtte for tar også
                os.remove(file)

        h2_export(h2_file)


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
