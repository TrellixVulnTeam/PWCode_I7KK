# Copyright(C) 2021 Morten Eek

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pathlib import Path
from os.path import relpath
import base64
import petl as etl
import pathlib
import re
import zipfile
import signal
import shutil
from specific_import import import_file
import subprocess
import os
import cchardet as chardet
pw_file = import_file('file.py')
pw_metadata = import_file('metadata.py')

if os.name == "posix":
    import ocrmypdf
    from pdfy import Pdfy

# mime_type: (keep_original, function name, new file extension)
mime_to_norm = {
    'application/msword': (False, 'docbuilder2x', 'pdf'),
    'application/pdf': (False, 'pdf2pdfa', 'pdf'),
    # 'application/rtf': (False, 'abi2x', 'pdf'),
    'application/rtf': (True, 'docbuilder2x', 'pdf'),  # TODO: Finn beste test på om har blitt konvertert til pdf
    'application/vnd.ms-excel': (True, 'docbuilder2x', 'pdf'),
    # 'application/vnd.ms-project': ('pdf'), # TODO: Har ikke ferdig kode for denne ennå
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': (True, 'docbuilder2x', 'pdf'),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': (True, 'docbuilder2x', 'pdf'),
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': (True, 'docbuilder2x', 'pdf'),
    'application/vnd.wordperfect': (False, 'docbuilder2x', 'pdf'),  # TODO: Mulig denne må endres til libreoffice
    # 'application/xhtml+xml; charset=UTF-8': (False, 'wkhtmltopdf', 'pdf'),
    'application/xhtml+xml': (False, 'wkhtmltopdf', 'pdf'),
    # 'application/xml': (False, 'file_copy', 'xml'),
    'application/xml': (False, 'x2utf8', 'xml'),
    'application/x-elf': (False, None, None),  # executable on lin
    'application/x-msdownload': (False, None, None),  # executable on win
    'application/x-ms-installer': (False, None, None),  # Installer on win
    'application/x-tika-msoffice': (False, None, None),
    'n/a': (False, None, None),
    'application/zip': (False, 'zip_to_norm', 'zip'),
    'image/gif': (False, 'image2norm', 'pdf'),
    # 'image/jpeg': (False, 'image2norm', 'pdf'),
    'image/jpeg': (False, 'file_copy', 'jpg'),
    'image/png': (False, 'file_copy', 'png'),
    'image/tiff': (False, 'image2norm', 'pdf'),
    'text/html': (False, 'html2pdf', 'pdf'),  # TODO: Legg til undervarianter her (var opprinnelig 'startswith)
    'text/plain': (False, 'x2utf8', 'txt'),
    'multipart/related': (True, 'mhtml2pdf', 'pdf'),
    'message/rfc822': (True, 'eml2pdf', 'pdf'),
}


# Dictionary of converter functions
converters = {}


def add_converter():
    # Decorator for adding functions to converter functions
    def _add_converter(func):
        converters[func.__name__] = func
        return func
    return _add_converter


@add_converter()
def eml2pdf(args):
    ok = False
    args['tmp_file_path'] = args['tmp_file_path'] + '.pdf'
    command = ['eml_to_pdf', args['source_file_path'], args['tmp_file_path']]
    run_shell_command(command)

    if os.path.exists(args['tmp_file_path']):
        ok = pdf2pdfa(args)

        if os.path.isfile(args['tmp_file_path']):
            os.remove(args['tmp_file_path'])

    return ok


@add_converter()
def mhtml2pdf(args):
    ok = False
    args['tmp_file_path'] = args['tmp_file_path'] + '.pdf'
    java_path = os.environ['pwcode_java_path']  # Get Java home path
    converter_jar = os.path.expanduser("~") + '/bin/emailconverter/emailconverter.jar'

    command = [java_path, '-jar', converter_jar, '-e', args['source_file_path'], '-o', args['tmp_file_path']]
    result = run_shell_command(command)
    # print(result)

    if os.path.exists(args['tmp_file_path']):
        ok = pdf2pdfa(args)

        if os.path.isfile(args['tmp_file_path']):
            os.remove(args['tmp_file_path'])

    return ok


@add_converter()
def x2utf8(args):
    # TODO: Sjekk om beholder extension alltid (ikke endre csv, xml mm)
    # TODO: Test å bruke denne heller enn/i tillegg til replace under: https://ftfy.readthedocs.io/en/latest/

    repls = (
        ('‘', 'æ'),
        ('›', 'ø'),
        ('†', 'å'),
        ('&#248;', 'ø'),
        ('&#229;', 'å'),
        ('&#230;', 'æ'),
        ('&#197;', 'Å'),
        ('&#216;', 'Ø'),
        ('&#198;', 'Æ'),
        ('=C2=A0', ' '),
        ('=C3=A6', 'æ'),
        ('=C3=B8', 'ø'),
        ('=C3=A5', 'å'),
    )

    with open(args['norm_file_path'], "wb") as file:
        with open(args['source_file_path'], 'rb') as file_r:
            content = file_r.read()
            if content is None:
                return False

            char_enc = chardet.detect(content)['encoding']

            try:
                data = content.decode(char_enc)
            except Exception:
                return False

            for k, v in repls:
                data = re.sub(k, v, data, flags=re.MULTILINE)
        file.write(data.encode('utf8'))

        if os.path.exists(args['norm_file_path']):
            return True

    return False


@add_converter()
def zip_to_norm(args):
    # TODO: Blir sjekk på om normalisert fil finnes nå riktig for konvertering av zip-fil når ext kan variere?
    # --> Blir skrevet til tsv som 'converted successfully' -> sjekk hvordan det kan stemme når extension på normalsert varierer

    def copy(norm_dir_path, norm_base_path):
        files = os.listdir(norm_dir_path)
        file = files[0]
        ext = Path(file).suffix
        src = os.path.join(norm_dir_path, file)
        dest = os.path.join(Path(norm_base_path).parent, os.path.basename(norm_base_path) + '.zip' + ext)
        if os.path.isfile(src):
            shutil.copy(src, dest)

    def zip_dir(norm_dir_path, norm_base_path):
        shutil.make_archive(norm_base_path, 'zip', norm_dir_path)

    def rm_tmp(paths):
        for path in paths:
            pw_file.delete_file_or_dir(path)

    norm_base_path = os.path.splitext(args['norm_file_path'])[0]
    norm_zip_path = norm_base_path + '_zip'
    norm_dir_path = norm_zip_path + '_norm'
    paths = [norm_dir_path + '.tsv', norm_dir_path, norm_zip_path]

    extract_nested_zip(args['source_file_path'], norm_zip_path)

    msg, file_count, errors, originals = convert_folder(norm_zip_path, norm_dir_path, args['tmp_dir'], zip=True, keep_file_name=False)

    if 'succcessfully' in msg:
        func = copy

        if file_count > 1:
            func = zip_dir

        try:
            func(norm_dir_path, norm_base_path)
        except Exception as e:
            print(e)
            return False

        rm_tmp(paths)
        if originals:
            return 'originals'
        else:
            return True

    rm_tmp(paths)
    return False


def extract_nested_zip(zipped_file, to_folder):
    with zipfile.ZipFile(zipped_file, 'r') as zfile:
        zfile.extractall(path=to_folder)

    for root, dirs, files in os.walk(to_folder):
        for filename in files:
            if re.search(r'\.zip$', filename):
                fileSpec = os.path.join(root, filename)
                extract_nested_zip(fileSpec, root)


def kill(proc_id):
    os.kill(proc_id, signal.SIGINT)


def run_shell_command(command, cwd=None, timeout=30):
    # ok = False
    os.environ['PYTHONUNBUFFERED'] = "1"
    # cmd = [' '.join(command)]
    stdout = []
    stderr = []
    mix = []  # TODO: Fjern denne mm

    # print(''.join(cmd))
    # sys.stdout.flush()

    proc = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill(proc.pid)

    # while proc.poll() is None:
    #     line = proc.stdout.readline()
    #     if line != "":
    #         stdout.append(line)
    #         mix.append(line)
    #         print(line, end='')

    #     line = proc.stderr.readline()
    #     if line != "":
    #         stderr.append(line)
    #         mix.append(line)
    #         print(line, end='')

    for line in proc.stdout:
        stdout.append(line.rstrip())

    for line in proc.stderr:
        stderr.append(line.rstrip())

    # print(stderr)
    return proc.returncode, stdout, stderr, mix


@ add_converter()
def file_copy(args):
    ok = False
    try:
        shutil.copyfile(args['source_file_path'], args['norm_file_path'])
        ok = True
    except Exception as e:
        print(e)
        ok = False
    return ok


# TODO: Hvordan kalle denne med python: tesseract my-image.png nytt filnavn pdf -> må bruke subprocess

@ add_converter()
def image2norm(args):
    ok = False
    args['tmp_file_path'] = args['tmp_file_path'] + '.pdf'
    command = ['convert', args['source_file_path'], args['tmp_file_path']]
    run_shell_command(command)

    if os.path.exists(args['tmp_file_path']):
        ok = pdf2pdfa(args)

        # WAIT: Egen funksjon for sletting av tmp-filer som kalles fra alle def? Er nå under her for å håndtere endret tmp navn + i overordnet convert funkson
        if os.path.isfile(args['tmp_file_path']):
            os.remove(args['tmp_file_path'])

    return ok


@ add_converter()
def docbuilder2x(args):
    ok = False
    docbuilder_file = os.path.join(args['tmp_dir'], 'x2x.docbuilder')

    docbuilder = None
    # WAIT: Tremger ikke if/else under hvis ikke skal ha spesifikk kode pr format
    if args['mime_type'] in (
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ):
        docbuilder = [
            'builder.OpenFile("' + args['source_file_path'] + '", "")',
            'builder.SaveFile("pdf", "' + args['tmp_file_path'] + '")',
            'builder.CloseFile();',
        ]
    else:
        docbuilder = [
            'builder.OpenFile("' + args['source_file_path'] + '", "")',
            'builder.SaveFile("pdf", "' + args['tmp_file_path'] + '")',
            'builder.CloseFile();',
        ]

    with open(docbuilder_file, "w+") as file:
        file.write("\n".join(docbuilder))

    command = ['documentbuilder', docbuilder_file]
    run_shell_command(command)

    if os.path.exists(args['tmp_file_path']):
        ok = pdf2pdfa(args)

    return ok


@add_converter()
def wkhtmltopdf(args):
    # WAIT: Trengs sjekk om utf-8 og evt. konvertering først her?
    ok = False
    command = ['wkhtmltopdf', '-O', 'Landscape', args['source_file_path'], args['tmp_file_path']]
    run_shell_command(command)

    if os.path.exists(args['tmp_file_path']):
        ok = pdf2pdfa(args)

    return ok


@add_converter()
def abi2x(args):
    ok = False
    command = ['abiword', '--to=pdf', '--import-extension=rtf', '-o', args['tmp_file_path'], args['source_file_path']]
    run_shell_command(command)

    # TODO: Må ha bedre sjekk av generert pdf. Har laget tomme pdf-filer noen ganger
    if os.path.exists(args['tmp_file_path']):
        ok = pdf2pdfa(args)

    return ok


# def libre2x(source_file_path, tmp_file_path, norm_file_path, keep_original, tmp_dir, mime_type):
    # TODO: Endre så bruker collabora online (er installert på laptop). Se notater om curl kommando i joplin
    # command = ["libreoffice", "--convert-to", "pdf", "--outdir", str(filein.parent), str(filein)]
    # run_shell_command(command)


def unoconv2x(file_path, norm_path, format, file_type):
    ok = False
    command = ['unoconv', '-f', format]

    if file_type in (
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ):
        if format == 'pdf':
            command.extend([
                '-d', 'spreadsheet', '-P', 'PaperOrientation=landscape',
                '-eSelectPdfVersion=1'
            ])
        elif format == 'html':
            command.extend(
                ['-d', 'spreadsheet', '-P', 'PaperOrientation=landscape'])
    elif file_type in ('application/msword', 'application/rtf'):
        command.extend(['-d', 'document', '-eSelectPdfVersion=1'])

    command.extend(['-o', '"' + norm_path + '"', '"' + file_path + '"'])
    run_shell_command(command)

    if os.path.exists(norm_path):
        ok = True

    return ok


@ add_converter()
def pdf2pdfa(args):
    ok = False

    if args['mime_type'] == 'application/pdf':
        args['tmp_file_path'] = args['source_file_path']

        # WAIT: Legg inn ekstra sjekk her om hva som skal gjøres hvis ocr = True
        if args['version'] in ('1a', '1b', '2a', '2b'):
            file_copy(args)
            if os.path.exists(args['norm_file_path']):
                ok = True

            return ok

    ocrmypdf.configure_logging(-1)
    result = ocrmypdf.ocr(args['tmp_file_path'], args['norm_file_path'], tesseract_timeout=0, progress_bar=False, skip_text=True)
    if str(result) == 'ExitCode.ok':
        ok = True

    return ok


@ add_converter()
def html2pdf(args):
    ok = False
    try:
        p = Pdfy()
        p.html_to_pdf(args['source_file_path'], args['tmp_file_path'])
    except Exception as e:
        print(e)

    if os.path.exists(args['tmp_file_path']):
        ok = pdf2pdfa(args)

    return ok


def file_convert(source_file_path, mime_type, function, target_dir, tmp_dir, norm_file_path=None, norm_ext=None, version=None, ocr=False, keep_original=False, zip=False):
    source_file_name = os.path.basename(source_file_path)
    base_file_name = os.path.splitext(source_file_name)[0] + '.'
    tmp_file_path = tmp_dir + '/' + base_file_name + 'tmp'
    if norm_file_path is None:
        norm_file_path = target_dir + '/' + base_file_name
        if norm_ext:
            norm_file_path = norm_file_path + norm_ext

    # TODO: Endre så returneres file paths som starter med prosjektmappe? Alltid, eller bare når genereres arkivpakke?
    normalized = {'result': None, 'norm_file_path': norm_file_path, 'error': None, 'original_file_copy': None}

    if not pw_file.check_for_files(norm_file_path + '*'):
        if mime_type == 'n/a':
            normalized['result'] = 5  # Not a file
            normalized['norm_file_path'] = None
        elif function in converters:
            pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)

            function_args = {'source_file_path': source_file_path,
                             'tmp_file_path': tmp_file_path,
                             'norm_file_path': norm_file_path,
                             'keep_original': keep_original,
                             'tmp_dir': tmp_dir,
                             'mime_type': mime_type,
                             'version': version,
                             'zip': zip,
                             #  'ocr': ocr,
                             }

            ok = converters[function](function_args)

            if not ok:
                error_files = target_dir + '/error_documents/'
                pathlib.Path(error_files).mkdir(parents=True, exist_ok=True)
                file_copy_args = {'source_file_path': source_file_path,
                                  'norm_file_path': error_files + os.path.basename(source_file_path)
                                  }
                file_copy(file_copy_args)
                normalized['original_file_copy'] = file_copy_args['norm_file_path']  # TODO: Fjern fil hvis konvertering lykkes når kjørt på nytt
                normalized['result'] = 0  # Conversion failed
                normalized['norm_file_path'] = None
            elif ok == 'originals':
                original_files = target_dir + '/original_documents/'
                pathlib.Path(original_files).mkdir(parents=True, exist_ok=True)
                file_copy_args = {'source_file_path': source_file_path,
                                  'norm_file_path': original_files + os.path.basename(source_file_path)
                                  }
                file_copy(file_copy_args)
                normalized['original_file_copy'] = file_copy_args['norm_file_path']
                normalized['result'] = 1  # Converted successfully
            elif keep_original:
                original_files = target_dir + '/original_documents/'
                pathlib.Path(original_files).mkdir(parents=True, exist_ok=True)
                file_copy_args = {'source_file_path': source_file_path,
                                  'norm_file_path': original_files + os.path.basename(source_file_path)
                                  }
                file_copy(file_copy_args)
                normalized['original_file_copy'] = file_copy_args['norm_file_path']
                normalized['result'] = 1  # Converted successfully
            else:
                normalized['result'] = 1  # Converted successfully
        else:
            if function:
                normalized['result'] = 4
                normalized['error'] = "Missing converter function '" + function + "'"
                normalized['norm_file_path'] = None
            else:
                normalized['result'] = 2  # Conversion not supported
                normalized['norm_file_path'] = None
    else:
        normalized['result'] = 3  # Converted earlier, or manually

    if os.path.isfile(tmp_file_path):
        os.remove(tmp_file_path)

    return normalized


def remove_fields(fields, table):
    for field in fields:
        if field in etl.fieldnames(table):
            table = etl.cutout(table, field)
    return table


def add_fields(fields, table):
    for field in fields:
        if field not in etl.fieldnames(table):
            table = etl.addfield(table, field, None)
    return table


def convert_folder(base_source_dir, base_target_dir, tmp_dir, tika=False, ocr=False, merge=False, tsv_source_path=None, tsv_target_path=None, make_unique=True, sample=False, zip=False, keep_file_name=False):
    # WAIT: Legg inn i gui at kan velge om skal ocr-behandles
    txt_target_path = base_target_dir + '_result.txt'
    json_tmp_dir = base_target_dir + '_tmp'
    converted_now = False
    errors = False
    originals = False

    if merge is False:  # TODO: Trengs begge argumentene?
        make_unique = False

    if tsv_source_path is None:
        tsv_source_path = base_target_dir + '.tsv'
    else:
        txt_target_path = os.path.splitext(tsv_source_path)[1][1:] + '_result.txt'

    if tsv_target_path is None:
        tsv_target_path = base_target_dir + '_processed.tsv'

    if os.path.exists(tsv_target_path):
        os.remove(tsv_target_path)

    Path(base_target_dir).mkdir(parents=True, exist_ok=True)

    # TODO: Viser mime direkte om er pdf/a eller må en sjekke mot ekstra felt i de to under? Forsjekk om Tika og siegfried?

    # TODO: Trengs denne sjekk om tsv her. Gjøres sjekk før kaller denne funskjonen og slik at unødvendig?
    # print(tsv_source_path)
    if not os.path.isfile(tsv_source_path):
        if tika:
            pw_metadata.run_tika(tsv_source_path, base_source_dir, json_tmp_dir, zip)
        else:
            pw_metadata.run_siegfried(base_source_dir, tmp_dir, tsv_source_path, zip)

    # TODO: Legg inn test på at tsv-fil ikke er tom
    pw_file.replace_text_in_file(tsv_source_path, '\0', '')

    table = etl.fromtsv(tsv_source_path)
    table = etl.rename(table,
                       {
                           'filename': 'source_file_path',
                           'tika_batch_fs_relative_path': 'source_file_path',
                           'filesize': 'file_size',
                           'mime': 'mime_type',
                           'Content_Type': 'mime_type',
                           'Version': 'version'
                       },
                       strict=False)

    thumbs_table = etl.select(table, lambda rec: Path(rec.source_file_path).name == 'Thumbs.db')
    if etl.nrows(thumbs_table) > 0:
        thumbs_paths = etl.values(thumbs_table, 'source_file_path')
        for path in thumbs_paths:
            if '/' not in path:
                path = os.path.join(base_source_dir, path)
            if os.path.isfile(path):
                os.remove(path)

        table = etl.select(table, lambda rec: Path(rec.source_file_path).name != 'Thumbs.db')

    table = etl.select(table, lambda rec: rec.source_file_path != '')
    table = etl.select(table, lambda rec: '#' not in rec.source_file_path)
    # WAIT: Ikke fullgod sjekk på embedded dokument i linje over da # faktisk kan forekomme i filnavn
    row_count = etl.nrows(table)

    file_count = sum([len(files) for r, d, files in os.walk(base_source_dir)])

    if row_count == 0:
        print('No files to convert. Exiting.')
        return 'Error', file_count
    elif file_count != row_count:
        print('Row count: ' + str(row_count))
        print('File count: ' + str(file_count))
        print("Files listed in '" + tsv_source_path + "' doesn't match files on disk. Exiting.")
        return 'Error', file_count
    elif not zip:
        print('Converting files..')

    # WAIT: Legg inn sjekk på filstørrelse før og etter konvertering

    append_fields = ('version', 'norm_file_path', 'result', 'original_file_copy', 'id')
    table = add_fields(append_fields, table)

    cut_fields = ('0', '1', 'X_TIKA_EXCEPTION_runtime', 'X_TIKA_EXCEPTION_warn')
    table = remove_fields(cut_fields, table)

    header = etl.header(table)
    pw_file.append_tsv_row(tsv_target_path, header)

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
        if '/' not in source_file_path:
            source_file_path = os.path.join(base_source_dir, source_file_path)

        mime_type = row['mime_type']
        # TODO: Virker ikke når Tika brukt -> finn hvorfor
        if ';' in mime_type:
            mime_type = mime_type.split(';')[0]

        version = row['version']
        result = None
        old_result = row['result']

        if not mime_type:
            if os.path.islink(source_file_path):
                mime_type = 'n/a'

            # kind = filetype.guess(source_file_path)
            extension = os.path.splitext(source_file_path)[1][1:].lower()
            if extension == 'xml':
                mime_type = 'application/xml'

        if not zip:
            print_path = os.path.relpath(source_file_path, Path(base_source_dir).parents[1])
            print(count_str + '.../' + print_path + ' (' + mime_type + ')')

        if mime_type not in mime_to_norm.keys():
            # print("|" + mime_type + "|")

            errors = True
            converted_now = True
            result = 'Conversion not supported'
            pw_file.append_txt_file(txt_target_path, result + ': ' + source_file_path + ' (' + mime_type + ')')
            row['norm_file_path'] = ''
            row['original_file_copy'] = ''
        else:
            keep_original = mime_to_norm[mime_type][0]

            if keep_original:
                originals = True

            if zip:
                keep_original = False

            function = mime_to_norm[mime_type][1]

            # Ensure unique file names in dir hierarchy:
            norm_ext = mime_to_norm[mime_type][2]
            if not norm_ext:
                norm_ext = 'none'

            if make_unique:
                norm_ext = (base64.b32encode(bytes(str(count), encoding='ascii'))).decode('utf8').replace('=', '').lower() + '.' + norm_ext
            target_dir = os.path.dirname(source_file_path.replace(base_source_dir, base_target_dir))
            normalized = file_convert(source_file_path, mime_type, function, target_dir, tmp_dir, None, norm_ext, version, ocr, keep_original, zip=zip)

            if normalized['result'] == 0:
                errors = True
                result = 'Conversion failed'
                pw_file.append_txt_file(txt_target_path, result + ': ' + source_file_path + ' (' + mime_type + ')')
            elif normalized['result'] == 1:
                result = 'Converted successfully'
                converted_now = True
            elif normalized['result'] == 2:
                errors = True
                result = 'Conversion not supported'
                pw_file.append_txt_file(txt_target_path, result + ': ' + source_file_path + ' (' + mime_type + ')')
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
                pw_file.append_txt_file(txt_target_path, result + ': ' + source_file_path + ' (' + mime_type + ')')
            elif normalized['result'] == 5:
                result = 'Not a document'

            if normalized['norm_file_path']:
                row['norm_file_path'] = relpath(normalized['norm_file_path'], base_target_dir)

            file_copy_path = normalized['original_file_copy']
            if file_copy_path:
                file_copy_path = relpath(file_copy_path, base_target_dir)
            row['original_file_copy'] = file_copy_path

        row['result'] = result
        row_values = list(row.values())

        # TODO: Fikset med å legge inn escapechar='\\' i append_tsv_row -> vil det skal problemer senere?
        # row_values = [r.replace('\n', ' ') for r in row_values if r is not None]
        pw_file.append_tsv_row(tsv_target_path, row_values)

        if sample and count > 9:
            break

    if not sample:
        shutil.move(tsv_target_path, tsv_source_path)
    # TODO: Legg inn valg om at hvis merge = true kopieres alle filer til mappe på øverste nivå og så slettes tomme undermapper

    msg = None
    if sample:
        msg = 'Sample files converted.'
        if errors:
            msg = "Not all sample files were converted. See '" + txt_target_path + "' for details."
    else:
        if converted_now:
            msg = 'All files converted succcessfully.'
            if errors:
                msg = "Not all files were converted. See '" + txt_target_path + "' for details."
        else:
            msg = 'All files converted previously.'

    return msg, file_count, errors, originals  # TODO: Fiks så bruker denne heller for oppsummering til slutt når flere mapper konvertert
