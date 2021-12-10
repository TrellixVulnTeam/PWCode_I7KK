# Copyright (C) 2021 Morten Eek

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import fileinput
import os
import sys
import subprocess
from pathlib import Path
from common.print import pretty_size, print_progress_bar
import hashlib
import blake3
import csv
import shutil
import errno
import glob


def check_for_files(filepath):
    for filepath_object in glob.glob(filepath):
        if os.path.isfile(filepath_object):
            return True

    return False


def delete_file_or_dir(path):
    if os.path.isfile(path):
        os.remove(path)

    if os.path.isdir(path):
        shutil.rmtree(path)


def copy_file_or_dir(src, dst):
    try:
        shutil.copytree(src, dst)
    except OSError as exc:
        if exc.errno in (errno.ENOTDIR, errno.EINVAL):
            shutil.copy(src, dst)
        else:
            raise


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


def get_unique_dir(directory):
    counter = 0
    while True:
        counter += 1
        path = Path(directory + str(counter))
        if not path.exists():
            return str(path)


def replace_text_in_file(file_path, search_text, new_text):
    with fileinput.input(file_path, inplace=True) as f:
        for line in f:
            new_line = line.replace(search_text, new_text)
            print(new_line, end='')


def xdg_open_file(filename):
    if sys.platform == "win32":
        os.startfile(filename)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, filename])


def get_checksum(filename, blocksize=65536):
    hash = blake3.blake3()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()


def md5sum(filename, blocksize=65536):
    hash = hashlib.md5()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()


def copy_file_progress(source, destination, prefix='Copy', suffix='done', decimals=1, length=50):
    with open(source, 'rb') as src, open(destination, 'wb') as dest:
        full_size = os.stat(source).st_size
        full = 0
        increment = 10485760
        tot_count = int(full_size/increment) + 1
        count = 0
        while full < full_size:
            count += 1
            chunk = src.read(increment)
            full += increment
            calc = full
            if calc + increment > full_size:
                calc += full_size - full
            dest.write(chunk)
            str_full = pretty_size(full)
            if count == tot_count:
                str_full = pretty_size(full_size)
            cust_bar = str_full + ' of ' + pretty_size(full_size)
            print_progress_bar(count, tot_count, cust_bar, prefix=prefix, suffix=suffix, decimals=decimals, length=length)
