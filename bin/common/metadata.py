# Copyright (C) 2020 Morten Eek

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

import subprocess
import shutil
import json
import os
import glob
from pathlib import Path
import csv


def merge_json_files(tmp_dir, json_path):
    glob_data = []
    for file in glob.glob(os.path.join(tmp_dir, '*.json')):
        with open(file) as json_file:
            data = json.load(json_file)
            i = 0
            while i < len(data):
                glob_data.append(data[i])
                i += 1

    with open(json_path, 'w') as f:
        json.dump(glob_data, f, indent=4)


def run_tika(tsv_path, base_source_dir, tika_tmp_dir):
    Path(tika_tmp_dir).mkdir(parents=True, exist_ok=True)

    json_path = os.path.join(tika_tmp_dir, 'merged.json')
    # TODO: Endre linje under så cross platform mm
    tika_path = '~/bin/tika/tika-app.jar'  # WAIT: Som configvalg hvor heller?

    # TODO: java - jar tika-app.jar - -config = <tika-config.xml >
    # -> path for mappe og så path for jar og config og så bruk disse i cmd under

    # TODO: Ha sjekk på om tsv finnes allerede?
    # if not os.path.isfile(tsv_path):
    print('\nIdentifying file types and extracting metadata...')
    subprocess.run(  # TODO: Denne blir ikke avsluttet ved ctrl-k -> fix (kill prosess gruppe?)
        # TODO: Endre så bruker bundlet java
        'java -jar ' + tika_path + ' -J -m -i ' + base_source_dir + ' -o ' + tika_tmp_dir,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        shell=True,
    )

    # Flatten dir hierarchy:
    flatten_dir(tika_tmp_dir)

    # Merge Tika-generated files:
    if not os.path.isfile(json_path):
        merge_json_files(tika_tmp_dir, json_path)

    if not os.path.isfile(tsv_path):
        json_to_tsv(json_path, tsv_path)

    if os.path.isfile(tsv_path):
        shutil.rmtree(tika_tmp_dir)


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
