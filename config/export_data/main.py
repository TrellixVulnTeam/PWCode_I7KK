import shutil
import os
import sys
from pathlib import Path
from common.xml_settings import XMLSettings
# from common.config import add_config_section
import xml.etree.ElementTree as ET
from common.file import md5sum

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from defs import ( # .defs.py
    export_db_schema,
    capture_files,
    test_db_connect
)


def main():
    bin_dir = os.environ["pwcode_bin_dir"]  # Get PWCode executable path
    class_path = os.environ['CLASSPATH']  # Get Java jar path
    config_dir = os.environ['pwcode_config_dir']  # Get PWCode config path
    tmp_dir = os.path.join(config_dir, 'tmp')
    os.chdir(tmp_dir)  # Avoid littering from subprocesses
    data_dir = os.environ['pwcode_data_dir']
    tmp_config_path = os.path.join(config_dir, 'tmp', 'pwcode.xml')
    tmp_config = XMLSettings(tmp_config_path)

    if not os.path.isfile(tmp_config_path):
        return 'No config file found. Exiting.'

    project_name = tmp_config.get('system/name')
    project_dir = os.path.join(data_dir, project_name)

    if not os.path.isdir(project_dir):
        return 'No project folder found. Exiting.'

    archive = os.path.join(project_dir, project_name + '.tar')
    if os.path.isfile(archive):
        return "'" + archive + "' already exists. Exiting."

    config_path = os.path.join(project_dir, '/pwcode.xml')
    if not os.path.isfile(config_path):
        shutil.copyfile(tmp_config_path, config_path)

    config = XMLSettings(config_path)
    memory = '-Xmx' + config.get('options/memory').split(' ')[0] + 'g'
    ddl = config.get('options/ddl')
    package = config.get('options/create_package')

    tree = ET.parse(config_path)
    subsystems = list(tree.find('subsystems'))

    archive_format = 'wim'
    if os.name == "posix":
        archive_format = 'tar'


     # TODO: Splitte ut som egen def for å fjerne duplisering av kode -> Skrive alle variabler til dict heller? Egen config-klasse?
    all_exported = True
    for subsystem in subsystems:
        subsystem_name = subsystem.tag
        db_status = config.get('subsystems/' + subsystem_name + '/db/status')
        db_name = config.get('subsystems/' + subsystem_name + '/db/name')
        schema_name = config.get('subsystems/' + subsystem_name + '/schema_name')
        jdbc_url = config.get('subsystems/' + subsystem_name + '/jdbc_url')
        db_user = config.get('subsystems/' + subsystem_name + '/db/user')
        db_password = config.get('subsystems/' + subsystem_name + '/db/password')
        exclude_tables = config.get('subsystems/' + subsystem_name + '/db/exclude_tables')
        include_tables = config.get('subsystems/' + subsystem_name + '/db/include_tables')
        overwrite_tables = config.get('subsystems/' + subsystem_name + '/db/overwrite_tables')

        if db_status != 'exported':
            all_exported = False

        if not jdbc_url or db_status == 'exported':
            continue

        print('test main1')
        db_check = test_db_connect(jdbc_url, bin_dir, class_path, memory, db_user, db_password, db_name, schema_name, include_tables, exclude_tables, overwrite_tables)
        print('test main2')
        if not db_check == 'ok':
            return db_check

    for subsystem in subsystems:
        folders_tag = subsystem.find('folders')
        if folders_tag:
            folders = list(folders_tag)
            for folder in folders:
                status = config.get('subsystems/' + subsystem_name + '/folders/' + folder.tag + '/status')
                if status != 'exported':
                    all_exported = False

                source_path = config.get('subsystems/' + subsystem_name + '/folders/' + folder.tag + '/path')
                if not os.path.isdir(source_path):
                    return "'" + source_path + "' is not a valid path. Exiting."

    if all_exported is True:
        return "System already exported."

    dirs = [
        os.path.join(project_dir, 'administrative_metadata'),
        os.path.join(project_dir, 'descriptive_metadata'),
        os.path.join(project_dir, 'content/documentation')
    ]

    for dir in dirs:
        Path(dir).mkdir(parents=True, exist_ok=True)

    for subsystem in subsystems:
        subsystem_name = subsystem.tag
        subsystem_dir = os.path.join(project_dir, 'content', 'sub_systems', subsystem_name)
        db_user = config.get('subsystems/' + subsystem_name + '/db/user')

        dirs = [
            os.path.join(subsystem_dir, 'header'),
            os.path.join(subsystem_dir, 'documentation', 'dip')
        ]

        for dir in dirs:
            Path(dir).mkdir(parents=True, exist_ok=True)

        folders_tag = subsystem.find('folders')
        if folders_tag:
            folders = list(folders_tag)
            for folder in folders:
                status = config.get('subsystems/' + subsystem_name + '/folders/' + folder.tag + '/status')
                if status == 'exported':
                    print("'" + folder.tag + "." + archive_format + "' already exported.")
                    continue

                source_path = config.get('subsystems/' + subsystem_name + '/folders/' + folder.tag + '/path')
                target_path = subsystem_dir + '/content/documents/' + folder.tag + "." + archive_format
                Path(subsystem_dir + '/content/documents/').mkdir(parents=True, exist_ok=True)
                file_result = capture_files(bin_dir, source_path, target_path)
                if file_result != 'ok':
                    config.put('subsystems/' + subsystem_name + '/folders/' + folder.tag + '/status', 'failed')
                    config.save()
                    return file_result

                config.put('subsystems/' + subsystem_name + '/folders/' + folder.tag + '/status', 'exported')
                config.save()

        jdbc_url = config.get('subsystems/' + subsystem_name + '/db/jdbc_url')
        db_user = config.get('subsystems/' + subsystem_name + '/db/user')
        db_password = config.get('subsystems/' + subsystem_name + '/db/password')
        db_name = config.get('subsystems/' + subsystem_name + '/db/name')
        schema_name = config.get('subsystems/' + subsystem_name + '/db/schema_name')
        jdbc_url = config.get('subsystems/' + subsystem_name + '/db/jdbc_url')
        exclude_tables = config.get('subsystems/' + subsystem_name + '/db/exclude_tables')
        include_tables = config.get('subsystems/' + subsystem_name + '/db/include_tables')
        overwrite_tables = config.get('subsystems/' + subsystem_name + '/db/overwrite_tables')
        db_status = config.get('subsystems/' + subsystem_name + '/db/status')

        if not db_status:
            continue

        if db_status == 'exported':
            print("Database in subsystem '" + subsystem_name + "' already exported.")
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
            config.put('subsystems/' + subsystem_name + '/db/status', 'failed')
            config.save()
            return db_result

        config.put('subsystems/' + subsystem_name + '/db/status', 'exported')
        config.save()

    if package == 'No':
        return "System exported successfully."

    exclude = [
        os.path.join(project_dir, 'pwcode.xml'),
        os.path.join(project_dir, '.pwcode')
    ]

    if package:
        capture_files(bin_dir, project_dir, archive, exclude)
        for sub_dir_path in [f.path for f in os.scandir(project_dir) if f.is_dir()]:
            if sub_dir_path != os.path.join(project_dir, '.pwcode'):
                shutil.rmtree(sub_dir_path, ignore_errors=True)

        checksum = md5sum(archive)
    else:
        checksum = 'n/a'

    config.put('system/md5sum', checksum)
    config.put('system/md5sum_verified', 'No')
    config.save()

    return 'All data copied and system data package created.'


if __name__ == '__main__':
    msg = main()
    print(msg)
    print('\n')  # WAIT: For flushing last print in def. Better fix later

