import os
from pathlib import Path
# from common.config import add_config_section
from common.file import md5sum, copy_file_progress
from common.xml_settings import XMLSettings
import tarfile
# import xml.etree.ElementTree as ET
from defs import (  # .defs.py
    process
)


def main():
    bin_dir = os.environ["pwcode_bin_dir"]  # Get PWCode executable path
    java_path = os.environ['pwcode_java_path']  # Get Java home path
    class_path = os.environ['CLASSPATH']  # Get jar path
    config_dir = os.environ["pwcode_config_dir"]  # Get PWCode config path
    tmp_dir = os.path.join(config_dir, 'tmp')
    os.chdir(tmp_dir)  # Avoid littering from subprocesses
    project_dir = str(Path(__file__).parents[2])
    config_path = os.path.join(project_dir, 'pwcode.xml')
    config = XMLSettings(config_path)
    project_name = config.get('name')
    package = config.get('options/create_package')
    memory = '-Xmx' + config.get('options/memory').split(' ')[0] + 'g'
    archive = os.path.join(project_dir, project_name + '.tar')

    if package == 'Yes':
        if not os.path.isfile(archive):
            return "'" + archive + "' does not exist. Exiting."

        checksum = config.get('md5sum')
        checksum_verified = config.get('md5sum_verified')

        if not checksum:
            return "No checksum in config file. Exiting."

        if not checksum_verified == 'Yes':
            if checksum == md5sum(archive):
                print("Data verified by checksum.")
                config.put('md5sum_verified', 'Yes')
                config.save()
            else:
                return "Checksum mismatch. Check data integrity. Exiting."

    sub_systems_dir = os.path.join(project_dir, 'content', 'sub_systems')
    extracted = False
    if os.path.isdir(sub_systems_dir):
        if len(os.listdir(sub_systems_dir)) != 0:
            extracted = True

    if not extracted:
        with tarfile.open(archive) as tar:
            tar.extractall(path=project_dir)

    # TODO: Hent java path
    process(project_dir, bin_dir, class_path, java_path, memory)
    # process_files(project_dir)

    return 'hva her?'


# TODO: Rekkefølge:
# -- Fix directories and extract from H2 if exists
# WbVarDef -file=tmp/pwb.ini; WbSysExec -program='python3' -argument='"$[pwb_path]/process_files_pre.py"' -env="PATH=$[py_path]";
# -- Virus check and metadata extract
# WbVarDef -file=tmp/pwb.ini; WbSysExec -ifNotEmpty=wim_path -program='python3' -argument='"$[pwb_path]/process_files_check.py"' -env="PATH=$[py_path]";
# -- Convert files
# WbVarDef -file=tmp/pwb.ini; WbSysExec -ifNotEmpty=wim_path -program='python3' -argument='"$[pwb_path]/process_files_convert.py"' -env="PATH=$[py_path]";
# -- Save log/unmount wim image
# WbVarDef -file=tmp/pwb.ini; WbSysExec -ifNotEmpty=wim_path -program='python3' -argument='"$[pwb_path]/wim_umount.py"' -env="PATH=$[py_path]";
# -- Clean up
# WbVarDef -file=tmp/pwb.ini; WbSysExec -ifNotEmpty=wim_path -program='python3' -argument='"$[pwb_path]/cleanup.py"' -env="PATH=$[py_path]";
# WbSysExec -ifEmpty=wim_path -program='echo "*** Some files not converted. Scroll up to see the list. ***"'
# -- Read env variables from config-file
# WbVarDef -file=tmp/pwb.ini;
# -- Normalize metadata and generate sql
# WbSysExec -program='python3' -argument='"$[pwb_path]/process_metadata_pre.py"' -env="PATH=$[py_path]";
# -- Read env variables from config-file
# WbVarDef -file=tmp/pwb.ini;
# -- Test data import
# WbSysExec -ifNotEmpty=wim_path -program='python3' -argument='"$[pwb_path]/process_metadata_check.py"' -env="PATH=$[py_path]";
# -- Save log/unmount wim image
# WbSysExec -ifNotEmpty=wim_path -program='python3' -argument='"$[pwb_path]/wim_umount.py"' -env="PATH=$[py_path]";
# -- Clean up
# WbSysExec -ifNotEmpty=wim_path -program='python3' -argument='"$[pwb_path]/cleanup.py"' -env="PATH=$[py_path]";

    # for dir in os.listdir(sub_systems_dir):
    #     docs_dir = sub_systems_dir + "/" + dir + "/content/documents"

    # tree = ET.parse(config_path)
    # subsystems = list(tree.find('subsystems'))
    # for subsystem in subsystems:
    #     folders_tag = subsystem.find('folders')
    #     if folders_tag:
    #         docs_dir = sub_systems_dir + subsystem.tag + "/content/documents/"
    #         Path(docs_dir).mkdir(parents=True, exist_ok=True)

    #     data_dir = sub_systems_dir + "/" + subsystem.tag + "/content/data/"
    #     data_docs_dir = sub_systems_dir + "/" + subsystem.tag + "/content/data_documents/"
    #     h2_file = data_dir + subsystem.tag + ".mv.db"
    #     if os.path.isfile(h2_file):
    #         for dir in [data_docs_dir, data_dir]:
    #             Path(dir).mkdir(parents=True, exist_ok=True)

    # TODO: Legg inn sjekk på om finnes upakket mappestruktur hvis ikke tar. Ha i config om pakket eller ikke? Ja -> sjekksum henger jo sammen med den


if __name__ == '__main__':
    msg = main()
    print(msg)
