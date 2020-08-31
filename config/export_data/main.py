import shutil
import os
from pathlib import Path
from configparser import ConfigParser
from common.xml_settings import XMLSettings
from common.config import add_config_section
import xml.etree.ElementTree as ET
from common.file import md5sum
from defs import (
    export_db_schema,
    capture_files,
    test_db_connect
)


def main():
    bin_dir = os.environ["pwcode_bin_dir"]  # Get PWCode executable path
    class_path = os.environ['CLASSPATH']  # Get Java jar path
    config_dir = os.environ['pwcode_config_dir']
    tmp_dir = config_dir + 'tmp'
    os.chdir(tmp_dir)  # Avoid littering from subprocesses
    data_dir = os.environ['pwcode_data_dir']
    tmp_config_path = config_dir + '/tmp/pwcode.xml'
    tmp_config = XMLSettings(tmp_config_path)

    if not os.path.isfile(tmp_config_path):
        print('No config file found. Exiting.')
        return

    project_name = tmp_config.get('name')
    project_dir = data_dir + project_name + '_'

    if not os.path.isdir(project_dir):
        print('No project folder found. Exiting.')
        return

    archive = project_dir[:-1] + '/' + project_name + '.tar' # TODO: Endre kode så 'tar' og ikke 'wim' ytterst
    if os.path.isfile(archive):
        return "'" + archive + "' already exists. Exiting."         

    config_path = project_dir + '/pwcode.xml'
    if not os.path.isfile(config_path):
        shutil.copyfile(tmp_config_path, config_path)

    config = XMLSettings(config_path)
    memory = '-Xmx' + config.get('options/memory').split(' ')[0] + 'g'
    ddl = config.get('options/ddl')

    tree = ET.parse(config_path)
    subsystems = list(tree.find('subsystems'))  

    archive_format = 'wim'
    if os.name == "posix":
        archive_format = 'tar'

    # TODO: Skrive til xml når ferdig eksportert de forskjellige delene?        
     # TODO: Splitte ut som egen def for å fjerne duplisering av kode -> Skrive alle variabler til dict heller? Egen config-klasse?
    for subsystem in subsystems: 
        subsystem_name = subsystem.tag
        db_name = config.get('subsystems/' + subsystem_name + '/db_name')
        schema_name = config.get('subsystems/' + subsystem_name + '/schema_name')
        jdbc_url = config.get('subsystems/' + subsystem_name + '/jdbc_url')
        db_user = config.get('subsystems/' + subsystem_name + '/db_user')
        db_password = config.get('subsystems/' + subsystem_name + '/db_password')
        exclude_tables = config.get('subsystems/' + subsystem_name + '/exclude_tables')
        include_tables = config.get('subsystems/' + subsystem_name + '/include_tables')
        overwrite_tables = config.get('subsystems/' + subsystem_name + '/overwrite_tables')

        if not jdbc_url:
            continue
        
        # TODO: Sjekk her om skjema og db finnes. Ikke bare at kan koble til databasemotor. Evt. bare gi tilbakemelding hvis ingen tabeller hentes?
        db_check = test_db_connect(jdbc_url, bin_dir, class_path, memory, db_user, db_password, db_name, schema_name, include_tables, exclude_tables, overwrite_tables)

        if not db_check == 'ok':
            print(db_check)
            return

    for subsystem in subsystems:
        folders_tag = subsystem.find('folders')
        if folders_tag:
            folders = list(folders_tag)
            for folder in folders:
                if not os.path.isdir(folder.text):
                    print("'" + folder.text + "' is not a valid path. Exiting.")
                    return   

    dirs = [
        project_dir  + '/administrative_metadata/',
        project_dir  + '/descriptive_metadata/',
        project_dir  + '/content/documentation/'
    ]

    for dir in dirs:
        Path(dir).mkdir(parents=True, exist_ok=True)

    for subsystem in subsystems:
        subsystem_name = subsystem.tag
        subsystem_dir = project_dir + '/content/sub_systems/' + subsystem_name
        db_user = config.get('subsystems/' + subsystem_name + '/db_user')

        dirs = [
            subsystem_dir + '/header',
            subsystem_dir + '/content/documents/',
            subsystem_dir + '/documentation/dip/'
        ]

        for dir in dirs:
            Path(dir).mkdir(parents=True, exist_ok=True)

        folders_tag = subsystem.find('folders')
        if folders_tag:
            file_status = config.get('subsystems/' + subsystem_name + '/status/file')
            if file_status =='exported':
                print("Files in subsystem '" + subsystem_name + "' already exported.")
            else:                
                folders = list(folders_tag)
                for folder in folders:
                    target_path = subsystem_dir + '/content/documents/' + folder.tag + "." + archive_format
                    if os.path.isfile(target_path):
                        continue

                    file_result = capture_files(bin_dir, folder.text, target_path) 
                    if file_result != 'ok':
                        print(file_result)
                        config.put('subsystems/' + subsystem_name + '/status/files', 'failed') 
                        config.save() 
                        return

                config.put('subsystems/' + subsystem_name + '/status/files', 'exported')
                config.save()

        jdbc_url = config.get('subsystems/' + subsystem_name + '/jdbc_url')
        db_user = config.get('subsystems/' + subsystem_name + '/db_user')
        db_password = config.get('subsystems/' + subsystem_name + '/db_password')
        db_name = config.get('subsystems/' + subsystem_name + '/db_name')
        schema_name = config.get('subsystems/' + subsystem_name + '/schema_name')
        jdbc_url = config.get('subsystems/' + subsystem_name + '/jdbc_url')
        exclude_tables = config.get('subsystems/' + subsystem_name + '/exclude_tables')
        include_tables = config.get('subsystems/' + subsystem_name + '/include_tables')
        overwrite_tables = config.get('subsystems/' + subsystem_name + '/overwrite_tables')
        db_status = config.get('subsystems/' + subsystem_name + '/status/db')

        if db_status == 'exported':
            print("Database in subsystem '" + subsystem_name + "' already exported.")
            continue

        if not jdbc_url:
            continue
        
        db_result = export_db_schema(
            jdbc_url,
            bin_dir,
            class_path,
            memory,
            db_user,
            db_password,
            db_name,
            schema_name,
            subsystem_dir,
            include_tables,
            exclude_tables,
            overwrite_tables,
            ddl
            )    

        if db_result != 'ok':
            print(db_result)
            config.put('subsystems/' + subsystem_name + '/status/db', 'failed')
            config.save()   
            return                               

        config.put('subsystems/' + subsystem_name + '/status/db', 'exported')           
        config.save()


if __name__ == '__main__':
    msg = main()
    print(msg)
    print('\n')  # WAIT: For flushing last print in def. Better fix later        


# if __name__ == '__main__':

#     data_dir = os.environ["pwcode_data_dir"]
#     # from toml_config.core import Config
#     # config_file = data_dir + 'config.toml'
#     # my_config = Config(config_file)
#     # my_config.add_section('app').set(key='value', other_key=[1, 2, 3])
#     # http://spika.net/py/xmlsettings/
#     config = XMLSettings(data_dir + "/config.xml")
#     config.put('userdata/level', 100)
#     config.save()

#     msg = main()
#     # print(msg)
