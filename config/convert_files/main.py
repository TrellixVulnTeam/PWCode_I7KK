import shutil
import os
import xml.etree.ElementTree as ET
from pathlib import Path
import glob
import json
import subprocess
import csv
import petl as etl
from common.xml_settings import XMLSettings
# from petl import extendheader, rename, appendtsv
from defs import file_convert # .defs.py
import base64

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
    'application/xhtml+xml; charset=UTF-8': (False, 'wkhtmltopdf', 'pdf'),
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
    'text/plain; charset=ISO-8859-1': (False, 'x2utf8', 'txt'),
    'text/plain; charset=UTF-8': (False, 'x2utf8', 'txt'),
    'text/plain; charset=windows-1252': (False, 'x2utf8', 'txt'),
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
    base_target_dir = project_dir + '/' + folder.tag
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

    if os.path.isfile(txt_target_path):
        os.remove(txt_target_path)

    data = etl.dicts(table)
    count = 0
    for row in data:
        count += 1
        count_str = ('(' + str(count) + '/' + str(file_count) + '): ')
        source_file_path = row['source_file_path']
        mime_type = row['mime_type']
        id = row['id']

        if not mime_type:
            if id == 'fmt/979':
                mime_type = 'application/xml'
            else:
                mime_type = 'unknown mime type'                

        version = row['version']
        result = None
        old_result = row['result']

        if mime_type not in mime_to_norm.keys():
            errors = True
            result = 'Conversion not supported'
            append_txt_file(txt_target_path, result + ': ' + source_file_path + ' (' + mime_type + ')')
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
        row['result'] = result
        row['original_file_copy'] = normalized['original_file_copy']
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

    return msg


def flatten_dir(destination, tsv_log=None):
    all_files = []
    first_loop_pass = True

    for root, _dirs, files in os.walk(destination):
        if first_loop_pass:
            first_loop_pass = False
            continue
        for filepath in files:
            all_files.append(os.path.join(root, filepath))

    for filepath in all_files:
        filename = os.path.basename(filepath)
        file_ext = Path(filename).suffix
        file_base = os.path.splitext(filename)[0]
        uniq = 1
        new_path = destination + "/%s%d%s" % (file_base, uniq, file_ext)

        while os.path.exists(new_path):
            new_path = destination + "/%s%d%s" % (file_base, uniq, file_ext)
            uniq += 1
        shutil.move(filepath, new_path)


def reduce_item(key, value):
    # Reduction Condition 1
    if type(value) is list:
        i = 0
        for sub_item in value:
            reduce_item(str(i), sub_item)
            i = i + 1
    # Reduction Condition 2
    elif type(value) is dict:
        sub_keys = value.keys()
        for sub_key in sub_keys:
            reduce_item(str(sub_key).replace(":", "_").replace("-", "_"), value[sub_key])
    # Base Condition
    else:
        reduced_item[str(key)] = str(value)


def json_to_tsv(json_path, tsv_path):
    node = ''
    fp = open(json_path, 'r')
    json_value = fp.read()
    raw_data = json.loads(json_value)
    fp.close()

    try:
        data_to_be_processed = raw_data[node]
    except Exception:
        data_to_be_processed = raw_data

    processed_data = []
    header = []
    for item in data_to_be_processed:
        global reduced_item
        reduced_item = {}
        reduce_item(node, item)
        header += reduced_item.keys()
        processed_data.append(reduced_item)

    header = list(set(header))
    header.sort()

    with open(tsv_path, 'w+') as f:
        writer = csv.DictWriter(f, header, delimiter='\t')
        writer.writeheader()
        for row in processed_data:
            writer.writerow(row)


def flattenjson(b, prefix='', delim='/', val=None):
    if val is None:
        val = {}

    if isinstance(b, dict):
        for j in b.keys():
            flattenjson(b[j], prefix + delim + j, delim, val)
    elif isinstance(b, list):
        get = b
        for j in range(len(get)):
            key = str(j)

            # If the nested data contains its own key, use that as the header instead.
            if isinstance(get[j], dict):
                if 'key' in get[j]:
                    key = get[j]['key']

            flattenjson(get[j], prefix + delim + key, delim, val)
    else:
        val[prefix] = b

    return val


def merge_json_files(tmp_dir, json_path):
    glob_data = []
    for file in glob.glob(tmp_dir + '/*.json'):
        with open(file) as json_file:
            data = json.load(json_file)
            i = 0
            while i < len(data):
                glob_data.append(data[i])
                i += 1

    with open(json_path, 'w') as f:
        json.dump(glob_data, f, indent=4)


def run_tika(tsv_path, base_source_dir, tmp_dir):
    Path(tmp_dir).mkdir(parents=True, exist_ok=True)

    json_path = tmp_dir + '/merged.json'
    tika_path = '~/bin/tika/tika-app.jar'  # WAIT: Som configvalg hvor heller?
    # if not os.path.isfile(tsv_path):
    # TODO: Endre så bruker bundlet java
    # TODO: Legg inn switch for om hente ut metadata også (bruke tika da). Bruke hva ellers?
    print('\nIdentifying file types and extracting metadata...')
    subprocess.run(  # TODO: Denne blir ikke avsluttet ved ctrl-k -> fix (kill prosess gruppe?)
        'java -jar ' + tika_path + ' -J -m -i ' + base_source_dir + ' -o ' + tmp_dir,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        shell=True,
    )

    # Flatten dir hierarchy:
    flatten_dir(tmp_dir)

    # Merge Tika-generated files:
    if not os.path.isfile(json_path):
        merge_json_files(tmp_dir, json_path)

    if not os.path.isfile(tsv_path):
        json_to_tsv(json_path, tsv_path)

    if os.path.isfile(tsv_path):
        shutil.rmtree(tmp_dir)


def run_siegfried(base_source_dir, project_dir, tsv_path):
    print('\nIdentifying file types...')

    csv_path = project_dir + '/tmp.csv'
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
    tmp_config_path = config_dir + '/tmp/convert_files.xml'
    tmp_config = XMLSettings(tmp_config_path)

    if not os.path.isfile(tmp_config_path):
        print('No config file found. Exiting.')
        return

    project_name = tmp_config.get('name')
    project_dir = data_dir + project_name

    if not os.path.isdir(project_dir):
        print('No project folder found. Exiting.')
        return

    config_path = project_dir + '/convert_files.xml'
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

    print('\n')
    for k, v in results.items():
        print(k + ': ', v)

    # return results


if __name__ == '__main__':
    main()
    print('\n')  # WAIT: For flushing last print in def. Better fix later
