import shutil
import os
from configparser import ConfigParser
from common.xml_settings import XMLSettings
from common.config import add_config_section
import xml.etree.ElementTree as ET
from common.file import md5sum
from defs import (
    export_db_schema,
    export_files,
    capture_files,
    test_db_connect
)

# """ SYSTEM """
# project_name = 'test2'  # Will also be the name of the generated data package
# EXPORT_TYPE = 'FILES'  # DATABASE | FILES | BOTH
# PACKAGE = True  # Set to true when all export runs are done to package as a wim or tar file with checksum
# ARCHIVE_FORMAT = 'wim'  # TODO: Implementer tar som alternativ + autodekter hva som er tilgjengelig

# """ FILES """
# # Extract all files from these directories:
# DIR_PATHS = [
#     # 'path/to/extract/on/linux',
#     '/home/bba/Downloads/RationalPlan/',
#     '/home/bba/Downloads/python/',
#     # '/home/bba/Downloads/vscode-icons-master/'
#     # 'c:\path\on\windows'
# ]

# """ DATABASE """
# DB_NAME = 'DOCULIVEHIST_DBO'
# DB_SCHEMA = 'PUBLIC'
# JDBC_URL = 'jdbc:h2:/home/bba/Desktop/DOCULIVEHIST_DBO_PUBLIC'
# DB_USER = ''
# DB_PASSWORD = ''
# MAX_JAVA_HEAP = '-Xmx4g'  # g=GB. Increase available memory as needed
# DDL_GEN = 'PWCode'  # PWCode | SQLWB -> Choose between generators for 'create table'
# # Copy all tables in schema except these:
# SKIP_TABLES = [
#     #    'EDOKFILES',
#     # 'tabnavn',
# ]
# # Copy only these tables (overrides 'SKIP_TABLES') :
# INCL_TABLES = [
#     # 'EDOKFILES',
#     # 'ALL',
# ]
# # Overwrite table rather than sync if exists in target:
# OVERWRITE_TABLES = [
#     # 'EDOKFILES',
#     # 'OA_SAK',
# ]


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

     # TODO: Splitte ut som egen def for å fjerne duplisering av kode
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

        db_check = test_db_connect(jdbc_url, bin_dir, class_path, memory, db_user, db_password, db_name, schema_name, include_tables, exclude_tables, overwrite_tables)
        if not db_check == 'ok':
            print(db_check)
            return


    for subsystem in subsystems:
        subsystem_name = subsystem.tag
        # subsystem_dir = system_dir + '/content/sub_systems/' + name
        db_name = subsystem.find('db_name')
        schema_name = subsystem.find('schema_name')
        folders_tag = subsystem.find('folders')
        if folders_tag:
            folders = list(folders_tag)
            for folder in folders:
                if not os.path.isdir(folder.text):
                    print("'" + folder.text + "' is not a valid path. Exiting.")
                    return   

        # TODO: Sjekk på db kobling her



        # export_files(project_dir, subsystem_dir, EXPORT_TYPE, project_name, DIR_PATHS, bin_dir, ARCHIVE_FORMAT)

#         # Create data package directories and extract any files:

#         # Export database schema:
#         if DB_NAME and DB_SCHEMA and JDBC_URL and EXPORT_TYPE != 'FILES':
#             export_db_schema(
#                 JDBC_URL,
#                 bin_dir,
#                 class_path,
#                 MAX_JAVA_HEAP,
#                 DB_USER,
#                 DB_PASSWORD,
#                 DB_NAME,
#                 DB_SCHEMA,
#                 subsystem_dir,
#                 INCL_TABLES,
#                 SKIP_TABLES,
#                 OVERWRITE_TABLES,
#                 DDL_GEN
#             )

#         if PACKAGE:
#             capture_files(bin_dir, system_dir, archive)
#             checksum = md5sum(archive)

#             config = ConfigParser()
#             config_file = system_dir[:-1] + "/pwcode.ini"

#             config.read(config_file)
#             add_config_section(config, 'SYSTEM')
#             config.set('SYSTEM', 'checksum', checksum)
#             config.set('SYSTEM', 'archive_format', ARCHIVE_FORMAT)
#             config.set('SYSTEM', 'checksum_verified', "False")
#             with open(config_file, "w+") as f:
#                 config.write(f, space_around_delimiters=False)

#             shutil.rmtree(system_dir, ignore_errors=True)
#             return 'All data copied and system data package created.'

#         else:
#             return 'All data copied. Create system data package now if finished extracting system data.'
           



# def main():
#     bin_dir = os.environ["pwcode_bin_dir"]  # Get PWCode executable path
#     class_path = os.environ['CLASSPATH']  # Get Java jar path
#     data_dir = os.environ["pwcode_data_dir"]  # Get PWCode data path (projects)
#     config_dir = os.environ["pwcode_config_dir"]  # Get PWCode config path
#     subsystem_dir = None
#     tmp_dir = config_dir + 'tmp'

#     os.chdir(tmp_dir)  # Avoid littering from subprocesses

#     if project_name:
#         system_dir = data_dir + project_name + '_'  # --> projects/[system_]
#         archive = system_dir[:-1] + '/' + project_name + '.' + ARCHIVE_FORMAT
#         if os.path.isfile(archive):
#             return "'" + archive + "' already exists. Exiting."




#         if EXPORT_TYPE != 'FILES':
#             if not (DB_NAME and DB_SCHEMA):
#                 return 'Missing database- or schema -name. Exiting.'
#             else:
#                 subsystem_dir = system_dir + '/content/sub_systems/' + DB_NAME + '_' + DB_SCHEMA

#         if EXPORT_TYPE != 'DATABASE' and not DIR_PATHS:
#             return 'Missing directory paths. Exiting.'

#         # Create data package directories and extract any files:
#         export_files(system_dir, subsystem_dir, EXPORT_TYPE, project_name, DIR_PATHS, bin_dir, ARCHIVE_FORMAT)

#         # Export database schema:
#         if DB_NAME and DB_SCHEMA and JDBC_URL and EXPORT_TYPE != 'FILES':
#             export_db_schema(
#                 JDBC_URL,
#                 bin_dir,
#                 class_path,
#                 MAX_JAVA_HEAP,
#                 DB_USER,
#                 DB_PASSWORD,
#                 DB_NAME,
#                 DB_SCHEMA,
#                 subsystem_dir,
#                 INCL_TABLES,
#                 SKIP_TABLES,
#                 OVERWRITE_TABLES,
#                 DDL_GEN
#             )

#         if PACKAGE:
#             capture_files(bin_dir, system_dir, archive)
#             checksum = md5sum(archive)

#             config = ConfigParser()
#             config_file = system_dir[:-1] + "/pwcode.ini"

#             config.read(config_file)
#             add_config_section(config, 'SYSTEM')
#             config.set('SYSTEM', 'checksum', checksum)
#             config.set('SYSTEM', 'archive_format', ARCHIVE_FORMAT)
#             config.set('SYSTEM', 'checksum_verified', "False")
#             with open(config_file, "w+") as f:
#                 config.write(f, space_around_delimiters=False)

#             shutil.rmtree(system_dir, ignore_errors=True)
#             return 'All data copied and system data package created.'

#         else:
#             return 'All data copied. Create system data package now if finished extracting system data.'

#     else:
#         return 'Missing system name. Exiting.'


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
