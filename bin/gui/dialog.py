# GPL3 License

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


import subprocess, os, shutil
from tkinter import filedialog


# WAIT: Remember last used directory?
def multi_open(data_dir, mode = None):
    path = None
    title = "Open File"
    x_arg = ''
    use_tk = True

    if mode == 'dir':
        title = "Open Folder"
        x_arg = " --directory "
    elif mode == 'save':
        title = "Save As"
        x_arg = " --save  "

    if os.name == "posix":
        if shutil.which('zenity') is not None:
            use_tk = False
            try:
                path = subprocess.check_output(
                    "zenity --file-selection  --title='" + title + "' --filename=" + data_dir + x_arg + "/ 2> >(grep -v 'GtkDialog' >&2)",
                    shell=True, executable='/bin/bash').decode("utf-8").strip()
            except subprocess.CalledProcessError:
                pass

    if use_tk: # WAIT: Separat farge theme for dialog hvordan?
        if mode == 'dir':
            path = filedialog.askdirectory(title = title, initialdir=data_dir)
        elif mode == 'save':
            path = filedialog.asksaveasfilename(title = title, initialdir=data_dir)
        else:
            path = filedialog.askopenfilename(title = title, initialdir=data_dir)

    return os.path.normpath(path)


