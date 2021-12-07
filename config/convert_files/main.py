
# from defs import file_convert  # .defs.py
import sys
import shutil
import os
import xml.etree.ElementTree as ET
# import subprocess
# import csv
from common.xml_settings import XMLSettings
from common.convert import convert_folder
# from petl import extendheader, rename, appendtsv

# WAIT: Lage egen plugin.py som setter paths mm så slipper å repetere i plugin kode
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def main():
    config_dir = os.environ['pwcode_config_dir']
    tmp_dir = os.path.join(config_dir, 'tmp')
    data_dir = os.environ['pwcode_data_dir']
    tmp_config_path = os.path.join(config_dir, 'tmp', 'convert_files.xml')
    tmp_config = XMLSettings(tmp_config_path)

    if not os.path.isfile(tmp_config_path):
        print('No config file found. Exiting.')
        return

    project_name = tmp_config.get('name')
    project_dir = os.path.join(data_dir, project_name)

    if not os.path.isdir(project_dir):
        print('No project folder found. Exiting.')
        return

    config_path = os.path.join(project_dir, 'convert_files.xml')
    if not os.path.isfile(config_path):
        shutil.copyfile(tmp_config_path, config_path)

    config = XMLSettings(config_path)
    merge = config.get('options/merge')

    tree = ET.parse(config_path)
    folders = list(tree.find('folders'))

    for folder in folders:
        if not os.path.isdir(folder.text):
            print("'" + folder.text + "' is not a valid path. Exiting.")
            return

    results = {}
    for folder in folders:
        base_target_dir = os.path.join(project_dir, folder.tag)
        msg, file_count, errors, originals = convert_folder(folder.text, base_target_dir, tmp_dir, merge=merge)
        results[folder.text] = msg

    # print('\n')
    for k, v in results.items():
        print(k + ': ', v)

    # return results


if __name__ == '__main__':
    main()
    print('\n')  # WAIT: For flushing last print in def. Better fix later
