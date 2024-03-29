import os
import sys
from common.file import get_checksum
from common.process_metadata_pre import normalize_metadata
from common.process_metadata_check import load_data
from common.xml_settings import XMLSettings
import xml.etree.ElementTree as ET
import tarfile
from defs import (  # .defs.py
    normalize_data
)


def main():
    bin_dir = os.environ["pwcode_bin_dir"]  # Get PWCode executable path
    class_path = os.environ['CLASSPATH']  # Get jar path
    config_dir = os.environ["pwcode_config_dir"]  # Get PWCode config path
    tmp_dir = os.path.join(config_dir, 'tmp')
    os.chdir(tmp_dir)  # Avoid littering from subprocesses

    # project_dir = str(Path(__file__).parents[2])
    project_dir = os.environ["pwcode_project_dir"]

    config_path = os.path.join(project_dir, 'pwcode.xml')
    config = XMLSettings(config_path)
    project_name = config.get('name')
    package = config.get('options/create_package')
    convert = config.get('options/convert_files')
    upload = config.get('options/upload')
    multi_schema = config.get('multi_schema')
    memory = '-Xmx' + config.get('options/memory').split(' ')[0] + 'g'
    archive = os.path.join(project_dir, project_name + '.tar')

    if package == 'Yes':
        if not os.path.isfile(archive):
            return "'" + archive + "' does not exist. Exiting."

        checksum = config.get('checksum')
        checksum_verified = config.get('checksum_verified')

        if not checksum:
            return "No checksum in config file. Exiting."

        if not checksum_verified == 'Yes':
            if checksum == get_checksum(archive):
                print("Data verified by checksum.")
                config.put('checksum_verified', 'Yes')
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
                
            
            safe_extract(tar, path=project_dir)

    result = normalize_data(project_dir, bin_dir, class_path, memory, tmp_dir, convert)

    if convert == 'Sample':
        return ''

    if not result:
        return 'Error converting some files. Exiting...'

    # TODO: Legg inn sjekk her på om databaseservicer startet og start hvis ikke

    tree = ET.parse(config_path)
    subsystems = list(tree.find('subsystems'))
    illegal_terms_file = os.path.join(config_dir, 'illegal_terms.txt')

    for subsystem in subsystems:
        subsystem_name = subsystem.tag
        schemas = config.get('subsystems/' + subsystem_name + '/schemas')
        schemas = [x.strip().lower() for x in schemas.split(',')]
        base_path = os.path.join(project_dir, 'content', 'sub_systems', subsystem_name)
        result = normalize_metadata(base_path, illegal_terms_file, schemas, tmp_dir)

    if upload == 'Yes':
        for subsystem in subsystems:
            subsystem_name = subsystem.tag
            if subsystem_name.startswith('doc'):
                # WAIT: Senere ha opplasting til db basert på tsv-filer med fildata
                continue

            schemas = config.get('subsystems/' + subsystem_name + '/schemas')
            schemas = [x.strip().lower() for x in schemas.split(',')]
            for schema in schemas:
                load_data(project_dir, config_dir, schema, multi_schema)

    return 'All data normalized...'

# TODO: Legg inn sjekk på om finnes upakket mappestruktur hvis ikke tar. Ha i config om pakket eller ikke? Ja -> sjekksum henger jo sammen med den


if __name__ == '__main__':
    result = main()
    if result == 'Error':
        print(result, file=sys.stderr)
    else:
        print(result)
