import os
from pathlib import Path
from configparser import ConfigParser
from common.config import add_config_section
from common.file import md5sum, copy_file_progress
from process_data_defs import (
    mount_wim,
    process,
)

""" SYSTEM """
SYSTEM_DIR = '/home/bba/bin/PWCode/projects/test'  # Dir with wim- or tar archive and pwcode.ini


def main():
    config_dir = os.environ["pwcode_config_dir"]  # Get PWCode config path
    tmp_dir = config_dir + '/tmp'
    os.chdir(tmp_dir)  # Avoid littering from subprocesses
    config = ConfigParser()
    config_file = SYSTEM_DIR + "/pwcode.ini"

    if os.path.isdir(SYSTEM_DIR) and os.path.isfile(config_file):
        config.read(config_file)
        checksum = config.get('SYSTEM', 'checksum')
        checksum_verified = config.get('SYSTEM', 'checksum_verified')
        archive_format = config.get('SYSTEM', 'archive_format')

        system_name = os.path.basename(SYSTEM_DIR)
        archive_path = SYSTEM_DIR + '/' + system_name + '.' + archive_format
        archive_bak_path = SYSTEM_DIR + '/bak/' + system_name + '.' + archive_format
        mount_dir = SYSTEM_DIR + '/mount'
        bak_dir = SYSTEM_DIR + '/bak'

        for dir in [mount_dir, bak_dir]:
            Path(dir).mkdir(parents=True, exist_ok=True)

        if not checksum:
            return "No checksum in 'pwcode.ini'. Exiting."

        if not os.path.isfile(archive_path):
            return "'" + archive_path + "' is not a valid archive path. Exiting."

        if not eval(checksum_verified):
            if checksum == md5sum(archive_path):
                print("Data verified by checksum.")
                config.set('SYSTEM', 'checksum_verified', "True")

                with open(config_file, "w+") as f:
                    config.write(f, space_around_delimiters=False)
            else:
                return "Checksum Mismatch. Check data integrity. Exiting."

        if not os.path.isfile(archive_bak_path):
            print("\nBackup archive before processing...")
            copy_file_progress(archive_path, archive_bak_path, prefix='Backup archive:', suffix='done', decimals=0, length=50)
            print("\nBackup complete.")

        process(mount_dir, archive_format, archive_path)

    else:
        return "'" + SYSTEM_DIR + "' is not a valid path. Exiting."

    # return 'All data processed.'  # WAIT: Printes ikke alltid -> hvorfor?


if __name__ == '__main__':
    msg = main()
    print(msg)

