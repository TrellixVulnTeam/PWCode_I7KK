
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


# mime_type: (keep_original, function name, new file extension)
mime_to_norm = {
    'application/msword': (False, 'docbuilder2x', 'pdf'),
    'application/pdf': (False, 'pdf2pdfa', 'pdf'),
    'application/rtf': (False, 'abi2x', 'pdf'),
    'application/vnd.ms-excel': (True, 'docbuilder2x', 'pdf'),
    # 'application/vnd.ms-project': ('pdf'), # TODO: Har ikke ferdig kode for denne ennå
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': (True, 'docbuilder2x', 'pdf'),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': (True, 'docbuilder2x', 'pdf'),
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': (True, 'docbuilder2x', 'pdf'),
    'application/vnd.wordperfect': (False, 'docbuilder2x', 'pdf'),  # TODO: Mulig denne må endres til libreoffice
    # 'application/xhtml+xml; charset=UTF-8': (False, 'wkhtmltopdf', 'pdf'),
    'application/xhtml+xml': (False, 'wkhtmltopdf', 'pdf'),
    'application/xml': (False, 'file_copy', 'xml'),
    'application/x-elf': (False, 'what?', None),  # executable on lin
    'application/x-msdownload': (False, 'what?', None),  # executable on win
    'application/x-ms-installer': (False, 'what?', None),  # Installer on win
    'application/x-tika-msoffice': (False, 'delete_file', None),  # TODO: Skriv funksjon ferdig
    'application/zip': (False, 'extract_nested_zip', 'zip'),  # TODO: Legg inn for denne
    'image/gif': (False, 'image2norm', 'pdf'),
    'image/jpeg': (False, 'image2norm', 'pdf'),
    'image/png': (False, 'file_copy', 'png'),
    'image/tiff': (False, 'image2norm', 'pdf'),
    'text/html': (False, 'html2pdf', 'pdf'),  # TODO: Legg til undervarianter her (var opprinnelig 'startswith)
    'text/plain': (False, 'x2utf8', 'txt'),
    'message/rfc822': (False, 'eml2pdf', 'pdf'),
}


def main():
    config_dir = os.environ['pwcode_config_dir']
    tmp_dir = os.path.join(config_dir, 'tmp')
    data_dir = os.environ['pwcode_data_dir']
    java_path = os.environ['pwcode_java_path']
    bin_dir = os.environ["pwcode_bin_dir"]  # Get PWCode executable path
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
        result = convert_folder(project_dir, folder, merge, tmp_dir, mime_to_norm, java_path, bin_dir)
        results[folder.text] = result

    # print('\n')
    for k, v in results.items():
        print(k + ': ', v)

    # return results


if __name__ == '__main__':
    main()
    print('\n')  # WAIT: For flushing last print in def. Better fix later
