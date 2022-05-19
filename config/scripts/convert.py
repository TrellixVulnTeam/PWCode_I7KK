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

import os
import subprocess
import shutil
import signal
import zipfile
import re
import pathlib
import csv
import glob
from os.path import relpath
from pathlib import Path
import petl as etl
import typer
import cchardet as chardet
if os.name == "posix":
    import ocrmypdf
    from pdfy import Pdfy


class File:
    """Contains methods for converting and adding text to files"""

    def __init__(self, path, mime_type='text/plain', version=None):
        self.path = path
        self.mime_type = mime_type
        self.version = version
        split_ext = os.path.splitext(path)
        # relative path without extension
        self.relative_root = split_ext[0]
        self.ext = split_ext[1]

    def append_tsv_row(self, row):
        """Append row to tsv file"""
        with open(self.path, 'a') as tsv_file:
            writer = csv.writer(
                tsv_file,
                delimiter='\t',
                quoting=csv.QUOTE_NONE,
                quotechar='',
                lineterminator='\n',
                escapechar='')
            writer.writerow(row)

    def append_txt(self, msg):
        """Append text to file"""
        with open(self.path, 'a') as txt_file:
            txt_file.write(msg + '\n')

    def convert(self, target_dir):
        """Convert file to archive format"""
        normalized = {'result': None, 'norm_file_path': None, 'error': None}

        # TODO: Finn ut beste måten å håndtere manuelt konverterte filer
        # if not check_for_files(norm_file_path + '*'):
        if True:
            if self.mime_type == 'n/a':
                normalized['msg'] = 'Not a document'
                normalized['norm_file_path'] = None
            else:

                converter = Converter(target_dir)
                norm_file_path, msg = converter.run(self)

                if not norm_file_path:
                    normalized['msg'] = msg or 'Conversion failed'
                    normalized['norm_file_path'] = None
                else:
                    normalized['msg'] = 'Converted successfully'
                    normalized['norm_file_path'] = norm_file_path
        else:
            normalized['msg'] = 'Manually converted'

        return normalized

class Converter:
    """Contains methods for converting from/to different filetypes"""

    def __init__(self, target_dir):
        self.target_dir = target_dir

    def run(self, src_file: File):
        """Run a file conversion"""
        result = False
        msg = None
        tmp_file_path = self.target_dir + '/' + src_file.relative_root + src_file.ext + '.tmp'
        tmp_file = File(tmp_file_path, 'application/pdf')
        pathlib.Path(os.path.dirname(tmp_file_path)).mkdir(parents=True, exist_ok=True)

        if src_file.mime_type in ('text/plain', 'application/xml'):
            result = self.x2utf8(src_file)
        elif src_file.mime_type == 'message/rfc822':
            result = self.eml2pdf(src_file, tmp_file)
        elif src_file.mime_type == 'multipart/related':
            result = self.mhtml2pdf(src_file, tmp_file)
        elif src_file.mime_type == 'application/zip':
            result = self.zip_to_norm(src_file)
        elif src_file.mime_type in ('image/gif', 'image/tiff'):
            result = self.image2norm(src_file, tmp_file)
        elif src_file.mime_type in (
            'application/msword', 'application/rtf', 'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.wordperfect'
        ):
            result = self.docbuilder2x(src_file, tmp_file)
        elif src_file.mime_type == 'application/xhtml+xml':
            result = self.wkhtml2pdf(src_file, tmp_file)
        elif src_file.mime_type == 'application/pdf':
            result = self.pdf2pdfa(src_file)
        elif src_file.mime_type == 'text/html':
            result = self.html2pdf(src_file, tmp_file)
        else:
            norm_file_path = self.target_dir + '/' + src_file.relative_root + src_file.ext
            shutil.copyfile(src_file.path, norm_file_path)
            msg = "Conversion not supported"

        if os.path.isfile(tmp_file.path):
            os.remove(tmp_file.path)

        return result, msg

    def x2utf8(self, src_file: File):
        """Convert text files to utf8 with Linux file endings"""

        # TODO: Test å bruke denne heller enn/i tillegg til replace under:
        #       https://ftfy.readthedocs.io/en/latest/

        norm_file_path = self.target_dir + '/' + src_file.relative_root + src_file.ext

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

        with open(norm_file_path, "wb") as file:
            with open(src_file.path, 'rb') as file_r:
                content = file_r.read()
                if content is None:
                    return ""

                char_enc = chardet.detect(content)['encoding']

                try:
                    data = content.decode(char_enc)
                except Exception:
                    return ""

                for k, v in repls:
                    data = re.sub(k, v, data, flags=re.MULTILINE)
            file.write(data.encode('utf8'))

            if os.path.exists(norm_file_path):
                return norm_file_path

        return ""


    def eml2pdf(self, src_file: File, tmp_file):
        """Convert email to pdf"""
        norm_file_path = ""
        command = ['eml_to_pdf', src_file.path, tmp_file.path]
        run_shell_command(command)

        if os.path.exists(tmp_file.path):
            norm_file_path = self.pdf2pdfa(tmp_file)

        return norm_file_path


    def mhtml2pdf(self, src_file: File, tmp_file: File):
        """Convert archived web content to pdf"""
        norm_file_path = ""
        java_path = os.environ['pwcode_java_path']  # Get Java home path
        converter_jar = os.path.expanduser("~") + '/bin/emailconverter/emailconverter.jar'

        command = [java_path, '-jar', converter_jar, '-e', src_file.path, '-o', tmp_file.path]
        result = run_shell_command(command)
        # print(result)

        if os.path.exists(tmp_file.path):
            norm_file_path = self.pdf2pdfa(tmp_file)

        return norm_file_path


    def zip_to_norm(self, src_file: File):
        """Exctract all files, convert them, and zip them again"""

        # TODO: Blir sjekk på om normalisert fil finnes nå riktig
        #       for konvertering av zip-fil når ext kan variere?
        # --> Blir skrevet til tsv som 'converted successfully'
        # --> sjekk hvordan det kan stemme når extension på normalsert varierer

        def copy(norm_dir_path, norm_base_path):
            files = os.listdir(norm_dir_path)
            file = files[0]
            ext = Path(file).suffix
            src = os.path.join(norm_dir_path, file)
            dest = os.path.join(
                Path(norm_base_path).parent,
                os.path.basename(norm_base_path) + '.zip' + ext
            )
            if os.path.isfile(src):
                shutil.copy(src, dest)

        def zip_dir(norm_dir_path, norm_base_path):
            shutil.make_archive(norm_base_path, 'zip', norm_dir_path)

        def rm_tmp(paths):
            for path in paths:
                delete_file_or_dir(path)

        norm_zip_path = src_file.relative_root + '_zip'
        norm_dir_path = norm_zip_path + '_norm'
        paths = [norm_dir_path + '.tsv', norm_dir_path, norm_zip_path]

        extract_nested_zip(src_file.path, norm_zip_path)

        msg, file_count, errors = convert_folder(norm_zip_path, norm_dir_path, zipped=True)

        if 'succcessfully' in msg:
            func = copy

            if file_count > 1:
                func = zip_dir

            try:
                func(norm_dir_path, src_file.relative_root)
            except Exception as e:
                print(e)
                return False

            rm_tmp(paths)

            return True

        rm_tmp(paths)
        return False


    def image2norm(self, src_file: File, tmp_file: File):
        """Convert images to pdf"""
        norm_file_path = ""
        command = ['convert', src_file.path, tmp_file.path]
        run_shell_command(command)

        if os.path.exists(tmp_file.path):
            norm_file_path = self.pdf2pdfa(tmp_file)

        return norm_file_path


    def docbuilder2x(self, src_file: File, tmp_file: File):
        """Convert office files to pdf"""
        norm_file_path = ""
        docbuilder_file = os.path.join(self.target_dir, 'x2x.docbuilder')

        docbuilder = None
        # WAIT: Tremger ikke if/else under hvis ikke skal ha spesifikk kode pr format
        if src_file.mime_type in (
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ):
            docbuilder = [
                'builder.OpenFile("' + src_file.path + '", "")',
                'builder.SaveFile("pdf", "' + tmp_file.path + '")',
                'builder.CloseFile();',
            ]
        else:
            docbuilder = [
                'builder.OpenFile("' + src_file.path + '", "")',
                'builder.SaveFile("pdf", "' + tmp_file.path + '")',
                'builder.CloseFile();',
            ]

        with open(docbuilder_file, "w+") as file:
            file.write("\n".join(docbuilder))

        command = ['documentbuilder', docbuilder_file]
        run_shell_command(command)

        if os.path.exists(tmp_file.path):
            norm_file_path = self.pdf2pdfa(tmp_file)

        if os.path.isfile(docbuilder_file):
            os.remove(docbuilder_file)

        return norm_file_path


    def wkhtml2pdf(self, src_file: File, tmp_file: File):
        """Convert html to pdf using QT Webkit rendering engine"""
        # WAIT: Trengs sjekk om utf-8 og evt. konvertering først her?
        norm_file_path = False
        command = ['wkhtmltopdf', '-O', 'Landscape', src_file.path, tmp_file.path]
        run_shell_command(command)

        if os.path.exists(tmp_file.path):
            norm_file_path = self.pdf2pdfa(tmp_file)

        return norm_file_path


    def abi2x(self, src_file: File, tmp_file: File):
        """Convert rtf to pdf using Abiword"""
        norm_file_path = ""
        command = ['abiword', '--to=pdf', '--import-extension=rtf', '-o',
                   tmp_file.path, src_file.path]
        run_shell_command(command)

        # TODO: Må ha bedre sjekk av generert pdf. Har laget tomme pdf-filer noen ganger
        if os.path.exists(tmp_file.path):
            norm_file_path = self.pdf2pdfa(tmp_file)

        return norm_file_path


    def pdf2pdfa(self, src_file: File):
        """Convert pdf to pdf/a"""

        if src_file.path.startswith(self.target_path):
            norm_file_path = src_file.relative_root + '.pdf'
        else:
            norm_file_path = self.target_dir + '/' + src_file.relative_root + src_file.ext

        # WAIT: Legg inn ekstra sjekk her om hva som skal gjøres hvis ocr = True
        if src_file.version in ('1a', '1b', '2a', '2b'):
            shutil.copyfile(src_file.path, norm_file_path)
            if os.path.exists(norm_file_path):
                norm_file_path = ""

            return norm_file_path

        ocrmypdf.configure_logging(-1)
        # Set tesseract_timeout=0 to only do PDF/A-conversion, and not ocr
        result = ocrmypdf.ocr(src_file.path, norm_file_path,
                              tesseract_timeout=0, progress_bar=False, skip_text=True)
        if str(result) != 'ExitCode.ok':
            norm_file_path = ""

        return norm_file_path


    def html2pdf(self, src_file: File, tmp_file: File):
        """Convert html to pdf"""
        norm_file_path = ""
        try:
            p = Pdfy()
            p.html_to_pdf(src_file.path, tmp_file.path)
        except Exception as e:
            print(e)

        if os.path.exists(tmp_file.path):
            norm_file_path = self.pdf2pdfa(tmp_file)

        return norm_file_path


    def unoconv2x(self, file_path, norm_path, format, file_type):
        """Convert office files to pdf"""
        success = False
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
            success = True

        return success


def run_siegfried(source_dir, target_dir, tsv_path, zipped=False):
    """Generate tsv file with info about file types"""
    if not zipped:
        print('\nIdentifying file types...')

    csv_path = os.path.join(target_dir, 'siegfried.csv')
    os.chdir(source_dir)
    subprocess.run(
        'sf -z -csv * > ' + csv_path,
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


def delete_file_or_dir(path):
    """Delete file or directory tree"""
    if os.path.isfile(path):
        os.remove(path)

    if os.path.isdir(path):
        shutil.rmtree(path)


def check_for_files(filepath):
    """Check if files exists"""
    for filepath_object in glob.glob(filepath):
        if os.path.isfile(filepath_object):
            return True

    return False


def extract_nested_zip(zipped_file, to_folder):
    """Extract nested zipped files to specified folder"""
    with zipfile.ZipFile(zipped_file, 'r') as zfile:
        zfile.extractall(path=to_folder)

    for root, dirs, files in os.walk(to_folder):
        for filename in files:
            if re.search(r'\.zip$', filename):
                fileSpec = os.path.join(root, filename)
                extract_nested_zip(fileSpec, root)


def run_shell_command(command, cwd=None, timeout=30):
    """Run shell command"""
    os.environ['PYTHONUNBUFFERED'] = "1"
    stdout = []
    stderr = []
    mix = []  # TODO: Fjern denne mm

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
        os.kill(proc.pid, signal.SIGINT)

    for line in proc.stdout:
        stdout.append(line.rstrip())

    for line in proc.stderr:
        stderr.append(line.rstrip())

    return proc.returncode, stdout, stderr, mix


def remove_fields(table, *args):
    """Remove fields from petl table"""
    for field in args:
        if field in etl.fieldnames(table):
            table = etl.cutout(table, field)
    return table


def add_fields(table, *args):
    """Add fields to petl table"""
    for field in args:
        if field not in etl.fieldnames(table):
            table = etl.addfield(table, field, None)
    return table


def convert_folder(source_dir: str, target_dir: str, zipped: bool=False):
    """Convert all files in folder"""
    tsv_source_path = target_dir + '.tsv'
    converted_now = False
    errors = False

    result_file = File(target_dir + '_result.txt')
    tsv_file = File(target_dir + '_processed.tsv')
    # Empty files
    open(result_file.path, 'w').close()
    open(tsv_file.path, 'w').close()

    Path(target_dir).mkdir(parents=True, exist_ok=True)

    os.chdir(source_dir)
    if not os.path.isfile(tsv_source_path):
        run_siegfried(source_dir, target_dir, tsv_source_path, zipped)

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

    table = etl.select(table, lambda rec: rec.source_file_path != '')
    table.row_count = etl.nrows(table)

    file_count = sum([len(files) for r, d, files in os.walk(source_dir)])

    if table.row_count == 0:
        print('No files to convert. Exiting.')
        return 'Error', file_count
    if file_count != table.row_count:
        print('Row count: ' + str(table.row_count))
        print('File count: ' + str(file_count))
        print("Files listed in '" + tsv_source_path + "' doesn't match files on disk. Exiting.")
        return 'Error', file_count
    if not zipped:
        print('Converting files..')

    table = add_fields(table, 'version', 'norm_file_path', 'result', 'id')

    # Remove Siegfried generated columns
    table = remove_fields(table, 'namespace', 'basis', 'warning')

    tsv_file.append_tsv_row(etl.header(table))

    # Treat csv (detected from extension only) as plain text:
    table = etl.convert(table, 'mime_type',
                        lambda v, row: 'text/plain' if row.id == 'x-fmt/18' else v,
                        pass_row=True)

    # Update for missing mime types where id is known:
    table = etl.convert(table, 'mime_type',
                        lambda v, row: 'application/xml' if row.id == 'fmt/979' else v,
                        pass_row=True)

    table.row_count = 0
    for row in etl.dicts(table):
        # Remove Thumbs.db files
        if os.path.basename(row['source_file_path']) == 'Thumbs.db':
            os.remove(row['source_file_path'])
            file_count -= 1
            continue

        table.row_count += 1

        row['mime_type'] = row['mime_type'].split(';')[0]

        if not row['mime_type']:
            # Siegfried sets mime type only to xml files with xml declaration
            if os.path.splitext(row['source_file_path'])[1].lower() == '.xml':
                row['mime_type'] = 'application/xml'

        if not zipped:
            print('(' + str(table.row_count) + '/' + str(file_count) + '): ' +
                  '.../' + row['source_file_path'] + ' (' + row['mime_type'] + ')')

        if row['result'] not in ('Converted successfully', 'Manually converted'):
            source_file = File(row['source_file_path'], row['mime_type'], row['version'])
            normalized = source_file.convert(target_dir)

            row['result'] = normalized['msg']

            if row['result'] in ('Conversion failed', 'Conversion not supported'):
                errors = True
                result_file.append_txt(row['result'] + ': ' + row['source_file_path'] +
                                       ' (' + row['mime_type'] + ')')

            if row['result'] in ('Converted successfully', 'Manually converted'):
                converted_now = True

            if normalized['norm_file_path']:
                row['norm_file_path'] = relpath(normalized['norm_file_path'], target_dir)

        tsv_file.append_tsv_row(list(row.values()))

    shutil.move(tsv_file.path, tsv_source_path)

    msg = None
    if converted_now:
        msg = 'All files converted succcessfully.'
        if errors:
            msg = "Not all files were converted. See '" + result_file.path + "' for details."
    else:
        msg = 'All files converted previously.'

    print("\n" + msg)

    return msg, file_count, errors

if __name__ == "__main__":
    typer.run(convert_folder)
