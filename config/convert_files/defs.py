# Copyright(C) 2020 Morten Eek

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

# from PIL import Image
import ocrmypdf
import subprocess
import os
import shutil
import sys
import signal
import zipfile
import re
import cchardet as chardet
import pathlib
# import img2pdf
from pdfy import Pdfy
# from pathlib import Path
from functools import reduce
# import wand
# from wand.image import Image, Color
# from wand.exceptions import BlobError

# Dictionary of converter functions
converters = {}


def add_converter():
    # Decorator for adding functions to converter functions
    def _add_converter(func):
        converters[func.__name__] = func
        return func
    return _add_converter


# def delete_file():
#     # TODO: Fjern garbage files og oppdater i tsv at det er gjort
#     return


def get_file_encoding(path):
    with open(path, "rb") as f:
        text = f.read()
        encoding = chardet.detect(text)['encoding'].lower()  

    return encoding         


@add_converter()
def x2utf8(args):
    # TODO: Sjekk om beholder extension alltid (ikke endre csv, xml mm)
    ok = False
    encoding = get_file_encoding(args['source_file_path'])   

    if encoding != 'utf-8':
        command = ['iconv', '-f', encoding]
        command.extend(['-t', 'UTF8', args['source_file_path'], '-o', args['tmp_file_path']])
        run_shell_command(command)
    else:
        file_copy(args)
        ok = True


    if os.path.exists(args['tmp_file_path']):
        repls = (
            ('‘', 'æ'),
            ('›', 'ø'),
            ('†', 'å'),
        )

        # WAIT: Legg inn validering av utf8 -> https://pypi.org/project/validate-utf8/
        file = open(args['norm_file_path'], "w")
        with open(args['tmp_file_path'], 'r') as file_r:
            for line in file_r:
                file.write(reduce(lambda a, kv: a.replace(*kv), repls, line))

        if os.path.exists(args['norm_file_path']):
            ok = True

    return ok


def extract_nested_zip(zippedFile, toFolder):
    """ Extract a zip file including any nested zip files
        Delete the zip file(s) after extraction
    """
    # pathlib.Path(toFolder).mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zippedFile, 'r') as zfile:
        zfile.extractall(path=toFolder)
    os.remove(zippedFile)
    for root, dirs, files in os.walk(toFolder):
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


@add_converter()
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

@add_converter()
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


@add_converter()
def docbuilder2x(args):
    ok = False
    docbuilder_file = args['tmp_dir'] + "/x2x.docbuilder"
    docbuilder = None

    if args['mime_type'] in (
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ):
        docbuilder = [
            'builder.OpenFile("' + args['source_file_path'] + '", "")',
            'var ws;',
            'var sheets = Api.GetSheets();',
            'var arrayLength = sheets.length;',
            'for (var i = 0; i < arrayLength; i++) {ws = sheets[i];ws.SetPageOrientation("xlLandscape");}',
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


def file_convert(source_file_path, mime_type, version, function, target_dir, keep_original, tmp_dir, norm_ext, count_str, ocr):
    source_file_name = os.path.basename(source_file_path)
    base_file_name = os.path.splitext(source_file_name)[0] + '.'
    tmp_file_path = tmp_dir + '/' + base_file_name + 'tmp'
    norm_file_path = target_dir + '/' + base_file_name
    if norm_ext:
        norm_file_path = norm_file_path + norm_ext

    # TODO: Endre så returneres file paths som starter med prosjektmappe? Alltid, eller bare når genereres arkivpakke?
    normalized = {'result': None, 'norm_file_path': norm_file_path, 'error': None, 'original_file_copy': None}

    if not os.path.isfile(norm_file_path):
        if os.path.islink(source_file_path):
            normalized['result'] = 5  # Not a file
            normalized['norm_file_path'] = None  # TODO: Fikk verdi fra linje over i tsv heller enn tom -> hvorfor?
            # TODO: Fikk også 'Conversion not supported' heller enn "not a file" -> hvorfor?
        elif function in converters:
            pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)

            # print(count_str + source_file_path + ' (' + mime_type + ')')

            function_args = {'source_file_path': source_file_path,
                             'tmp_file_path': tmp_file_path,
                             'norm_file_path': norm_file_path,
                             'keep_original': keep_original,
                             'tmp_dir': tmp_dir,
                             'mime_type': mime_type,
                             'version': version,
                             'ocr': ocr,
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
            #     os.remove(source_file_path) # WAIT: Bare når kjørt som generell behandling av arkivpakke
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
