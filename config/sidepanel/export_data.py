import shutil
import os
from configparser import ConfigParser
from common.xml_settings import XMLSettings
from common.config import add_config_section
from common.file import md5sum
from export_data_defs import (
    export_db_schema,
    export_files,
    capture_files,
)

""" SYSTEM """
SYSTEM_NAME = 'test2'  # Will also be the name of the generated data package
EXPORT_TYPE = 'FILES'  # DATABASE | FILES | BOTH
PACKAGE = True  # Set to true when all export runs are done to package as a wim or tar file with checksum
ARCHIVE_FORMAT = 'wim'  # TODO: Implementer tar som alternativ + autodekter hva som er tilgjengelig

""" FILES """
# Extract all files from these directories:
DIR_PATHS = [
    # 'path/to/extract/on/linux',
    '/home/bba/Downloads/RationalPlan/',
    '/home/bba/Downloads/python/',
    # '/home/bba/Downloads/vscode-icons-master/'
    # 'c:\path\on\windows'
]

""" DATABASE """
DB_NAME = 'DOCULIVEHIST_DBO'
DB_SCHEMA = 'PUBLIC'
JDBC_URL = 'jdbc:h2:/home/bba/Desktop/DOCULIVEHIST_DBO_PUBLIC'
DB_USER = ''
DB_PASSWORD = ''
MAX_JAVA_HEAP = '-Xmx4g'  # g=GB. Increase available memory as needed
DDL_GEN = 'PWCode'  # PWCode | SQLWB -> Choose between generators for 'create table'
# Copy all tables in schema except these:
SKIP_TABLES = [
    #    'EDOKFILES',
    # 'tabnavn',
]
# Copy only these tables (overrides 'SKIP_TABLES') :
INCL_TABLES = [
    # 'EDOKFILES',
    # 'ALL',
]
# Overwrite table rather than sync if exists in target:
OVERWRITE_TABLES = [
    # 'EDOKFILES',
    # 'OA_SAK',
]


def main():
    bin_dir = os.environ["pwcode_bin_dir"]  # Get PWCode executable path
    class_path = os.environ['CLASSPATH']  # Get Java jar path
    data_dir = os.environ["pwcode_data_dir"]  # Get PWCode data path (projects)
    config_dir = os.environ["pwcode_config_dir"]  # Get PWCode config path
    subsystem_dir = None
    tmp_dir = config_dir + 'tmp'

    os.chdir(tmp_dir)  # Avoid littering from subprocesses

    if SYSTEM_NAME:
        system_dir = data_dir + SYSTEM_NAME + '_'  # --> projects/[system_]
        archive = system_dir[:-1] + '/' + SYSTEM_NAME + '.' + ARCHIVE_FORMAT
        if os.path.isfile(archive):
            return "'" + archive + "' already exists. Exiting."

        if EXPORT_TYPE != 'FILES':
            if not (DB_NAME and DB_SCHEMA):
                return 'Missing database- or schema -name. Exiting.'
            else:
                subsystem_dir = system_dir + '/content/sub_systems/' + DB_NAME + '_' + DB_SCHEMA

        if EXPORT_TYPE != 'DATABASE' and not DIR_PATHS:
            return 'Missing directory paths. Exiting.'

        # Create data package directories and extract any files:
        export_files(system_dir, subsystem_dir, EXPORT_TYPE, SYSTEM_NAME, DIR_PATHS, bin_dir, ARCHIVE_FORMAT)

        # Export database schema:
        if DB_NAME and DB_SCHEMA and JDBC_URL and EXPORT_TYPE != 'FILES':
            export_db_schema(
                JDBC_URL,
                bin_dir,
                class_path,
                MAX_JAVA_HEAP,
                DB_USER,
                DB_PASSWORD,
                DB_NAME,
                DB_SCHEMA,
                subsystem_dir,
                INCL_TABLES,
                SKIP_TABLES,
                OVERWRITE_TABLES,
                DDL_GEN
            )

        if PACKAGE:
            capture_files(bin_dir, system_dir, archive)
            checksum = md5sum(archive)

            config = ConfigParser()
            config_file = system_dir[:-1] + "/pwcode.ini"

            config.read(config_file)
            add_config_section(config, 'SYSTEM')
            config.set('SYSTEM', 'checksum', checksum)
            config.set('SYSTEM', 'archive_format', ARCHIVE_FORMAT)
            config.set('SYSTEM', 'checksum_verified', "False")
            with open(config_file, "w+") as f:
                config.write(f, space_around_delimiters=False)

            shutil.rmtree(system_dir, ignore_errors=True)
            return 'All data copied and system data package created.'

        else:
            return 'All data copied. Create system data package now if finished extracting system data.'

    else:
        return 'Missing system name. Exiting.'


if __name__ == '__main__':

    data_dir = os.environ["pwcode_data_dir"]
    # from toml_config.core import Config
    # config_file = data_dir + 'config.toml'
    # my_config = Config(config_file)
    # my_config.add_section('app').set(key='value', other_key=[1, 2, 3])
    # http://spika.net/py/xmlsettings/
    config = XMLSettings(data_dir + "/config.xml")
    config.put('userdata/level', 100)
    config.save()

    msg = main()
    # print(msg)
