
from defs import file_convert  # .defs.py
import sys
import shutil
import os
import xml.etree.ElementTree as ET
from pathlib import Path
import subprocess
import csv
import petl as etl
import base64
from common.xml_settings import XMLSettings
from common.metadata import run_tika
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


def append_tsv_row(file_path, row):
    with open(file_path, 'a') as tsv_file:
        writer = csv.writer(
            tsv_file,
            delimiter='\t',
            quoting=csv.QUOTE_NONE,
            quotechar='',
            lineterminator='\n',
            escapechar='')
        writer.writerow(row)


def append_txt_file(file_path, msg):
    with open(file_path, 'a') as txt_file:
        txt_file.write(msg + '\n')


def convert_folder(project_dir, folder, merge, tmp_dir, tika=False, ocr=False):
    # TODO: Legg inn i gui at kan velge om skal ocr-behandles
    base_source_dir = folder.text
    base_target_dir = os.path.join(project_dir, folder.tag)
    tsv_source_path = base_target_dir + '.tsv'
    txt_target_path = base_target_dir + '_result.txt'
    tsv_target_path = base_target_dir + '_processed.tsv'
    json_tmp_dir = base_target_dir + '_tmp'
    converted_now = False
    errors = False

    Path(base_target_dir).mkdir(parents=True, exist_ok=True)

    # TODO: Viser mime direkte om er pdf/a eller må en sjekke mot ekstra felt i de to under?

    if not os.path.isfile(tsv_source_path):
        if tika:
            # TODO: Må tilpasse tsv under for tilfelle tika. Bare testet med siegried så langt
            run_tika(tsv_source_path, base_source_dir, json_tmp_dir)
        else:
            run_siegfried(base_source_dir, project_dir, tsv_source_path)

    table = etl.fromtsv(tsv_source_path)
    row_count = etl.nrows(table)

    # error_documents
    # original_documents
    # TODO: Legg inn at ikke skal telle filer i mapper med de to navnene over
    file_count = sum([len(files) for r, d, files in os.walk(base_source_dir)])

    # WAIT: Sjekk i forkant om garbage files som skal slettes?
    if row_count == 0:
        print('No files to convert. Exiting.')
        return 'error'
    elif file_count != row_count:
        print("Files listed in '" + tsv_source_path + "' doesn't match files on disk. Exiting.")
        return 'error'
    else:
        print('Converting files..')

    # WAIT: Legg inn sjekk på filstørrelse før og etter konvertering

    table = etl.rename(table, {'filename': 'source_file_path', 'filesize': 'file_size', 'mime': 'mime_type'}, strict=False)

    new_fields = ('norm_file_path', 'result', 'original_file_copy')
    for field in new_fields:
        if field not in etl.fieldnames(table):
            table = etl.addfield(table, field, None)

    header = etl.header(table)
    append_tsv_row(tsv_target_path, header)

    # Treat csv (detected from extension only) as plain text:
    table = etl.convert(table, 'mime_type', lambda v, row: 'text/plain' if row.id == 'x-fmt/18' else v, pass_row=True)

    # Update for missing mime types where id is known:
    table = etl.convert(table, 'mime_type', lambda v, row: 'application/xml' if row.id == 'fmt/979' else v, pass_row=True)

    if os.path.isfile(txt_target_path):
        os.remove(txt_target_path)

    data = etl.dicts(table)
    count = 0
    for row in data:
        count += 1
        count_str = ('(' + str(count) + '/' + str(file_count) + '): ')
        source_file_path = row['source_file_path']
        mime_type = row['mime_type']
        if ';' in mime_type:
            mime_type = mime_type.split(';')[0]

        version = row['version']
        result = None
        old_result = row['result']

        print(count_str + source_file_path + ' (' + mime_type + ')')

        if mime_type not in mime_to_norm.keys():
            errors = True
            converted_now = True
            result = 'Conversion not supported'
            append_txt_file(txt_target_path, result + ': ' + source_file_path + ' (' + mime_type + ')')
            row['norm_file_path'] = ''
            row['original_file_copy'] = ''
        else:
            keep_original = mime_to_norm[mime_type][0]
            function = mime_to_norm[mime_type][1]

            # Ensure unique file names in dir hierarchy:
            norm_ext = (base64.b32encode(bytes(str(count), encoding='ascii'))).decode('utf8').replace('=', '').lower() + '.' + mime_to_norm[mime_type][2]

            target_dir = os.path.dirname(source_file_path.replace(base_source_dir, base_target_dir))
            normalized = file_convert(source_file_path, mime_type, version, function, target_dir, keep_original, tmp_dir, norm_ext, count_str, ocr)

            if normalized['result'] == 0:
                errors = True
                result = 'Conversion failed'
                append_txt_file(txt_target_path, result + ': ' + source_file_path + ' (' + mime_type + ')')
            elif normalized['result'] == 1:
                result = 'Converted successfully'
                converted_now = True
            elif normalized['result'] == 2:
                errors = True
                result = 'Conversion not supported'
                append_txt_file(txt_target_path, result + ': ' + source_file_path + ' (' + mime_type + ')')
            elif normalized['result'] == 3:
                if old_result not in ('Converted successfully', 'Manually converted'):
                    result = 'Manually converted'
                    converted_now = True
                else:
                    result = old_result
            elif normalized['result'] == 4:
                converted_now = True
                errors = True
                result = normalized['error']
                append_txt_file(txt_target_path, result + ': ' + source_file_path + ' (' + mime_type + ')')
            elif normalized['result'] == 5:
                result = 'Not a file'

            row['norm_file_path'] = normalized['norm_file_path']
            row['original_file_copy'] = normalized['original_file_copy']

        row['result'] = result
        append_tsv_row(tsv_target_path, list(row.values()))

    shutil.move(tsv_target_path, tsv_source_path)

    # TODO: Legg inn valg om at hvis merge = true kopieres alle filer til mappe på øverste nivå og så slettes tomme undermapper

    msg = None
    if converted_now:
        if errors:
            msg = "Not all files were converted. See '" + txt_target_path + "' for details."
        else:
            msg = 'All files converted succcessfully.'
    else:
        msg = 'All files converted previously.'

    print(msg)
    # return msg # TODO: Fiks så bruker denne heller for oppsummering til slutt når flere mapper konvertert


def run_siegfried(base_source_dir, project_dir, tsv_path):
    print('\nIdentifying file types...')

    csv_path = os.path.join(project_dir, 'tmp.csv')
    subprocess.run(
        'sf -z -csv "' + base_source_dir + '" > ' + csv_path,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        shell=True,
    )

    with open(csv_path, 'r') as csvin, open(tsv_path, 'w') as tsvout:
        csvin = csv.reader(csvin)
        tsvout = csv.writer(tsvout, delimiter='\t')
        for row in csvin:
            tsvout.writerow(row)

    if os.path.exists(csv_path):
        os.remove(csv_path)


def main():
    config_dir = os.environ['pwcode_config_dir']
    tmp_dir = config_dir + 'tmp'
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
        result = convert_folder(project_dir, folder, merge, tmp_dir)
        results[folder.text] = result

    # print('\n')
    # for k, v in results.items():
    #     print(k + ': ', v)

    # return results


if __name__ == '__main__':
    main()
    print('\n')  # WAIT: For flushing last print in def. Better fix later
