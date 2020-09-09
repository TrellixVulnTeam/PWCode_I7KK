import os
from pathlib import Path
from common.config import add_config_section
from common.file import md5sum, copy_file_progress
from common.xml_settings import XMLSettings
from defs import (
    mount_wim,
    process,
)


def main():
    config_dir = os.environ["pwcode_config_dir"]  # Get PWCode config path
    tmp_dir = config_dir + 'tmp'
    os.chdir(tmp_dir)  # Avoid littering from subprocesses
    project_dir = str(Path(__file__).parents[2])
    config_path = project_dir + '/pwcode.xml'
    config = XMLSettings(config_path)
    project_name = config.get('system/name')

    project_extracted_dir = project_dir + '/' + project_name
    archive = project_extracted_dir + '.tar' 
    if not os.path.isfile(archive):
        return "'" + archive + "' does not exist. Exiting."         

    checksum = config.get('system/md5sum')
    checksum_verified = config.get('system/md5sum_verified')

    if not checksum:
        return "No checksum in config file. Exiting."

    if not checksum_verified == 'Yes':
        if checksum == md5sum(archive):
            print("Data verified by checksum.")
            config.put('system/md5sum_verified', 'Yes')
            config.save()
        else:
            return "Checksum mismatch. Check data integrity. Exiting."

    return process(project_extracted_dir, archive)


if __name__ == '__main__':
    msg = main()
    print(msg)

