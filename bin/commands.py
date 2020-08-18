# MIT License

# Original work Copyright (c) 2018 François Girault
# Modified work Copyright 2020 Morten Eek

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
from gettext import gettext as _get
from palette import PaletteFrame
from commander import command
import tkinter as tk
from tkinter import messagebox
from common.file import xdg_open_file
from vendor import filetype
from gui.dialog import multi_open

# WAIT: Lag file/folder chooser i left_menu -> endre dagens kode så har en knapp øverst bare og eget ikon?


def focus_app(app):
    app.editor_frame.focus()


@command(title=_get("Show Home"), description=_get("Show Home Screen"))
def show_home(app):
    """ show home tab """
    app.editor_frame.show_home()


@command(
    title=_get("Next Tab in Index"),
    category=_get("APP"),
    description=_get("Next Tab in Index"),
    shortcut=_get("<Control-Right>"),
)
def next_tab_in_index(app):
    """ Switch to next tab in tab index """
    tab_id = app.editor_frame.notebook.select()
    if tab_id:
        pos = app.editor_frame.notebook.index(tab_id) + 1

    if not tab_id or pos == app.editor_frame.notebook.index("end"):
        pos = 0

    app.editor_frame.notebook.select(pos)


@command(
    title=_get("Previous Tab in Index"),
    category=_get("APP"),
    description=_get("Previous Tab in Index"),
    shortcut=_get("<Control-Left>"),
)
def previous_tab_in_index(app):
    """ Switch to previous tab in tab index """
    tab_id = app.editor_frame.notebook.select()
    if tab_id:
        pos = app.editor_frame.notebook.index(tab_id) - 1
        if pos < 0:
            pos = app.editor_frame.notebook.index("end") - 1
    else:
        pos = 0

    app.editor_frame.notebook.select(pos)


@command(
    title=_get("Previous Tab by use"),
    category=_get("APP"),
    description=_get("Previous Tab by use"),
    shortcut=_get("<Control-Tab>"),
)
def previous_tab(app):
    """ Switch to previous tab by use """
    # app.editor_frame.focus_set() # TODO: Virket ikke
    # app.editor_frame.focus()  # TODO: Virket ikke
    path = app.editor_frame.previous_tab_paths[0]
    if path:
        open_file(app, path)
    else:
        show_home(app)


@command(
    title=_get("Quit App"),
    category=_get("APP"),
    description=_get("Exit program"),
    shortcut=_get("<Control-q>"),
)
def quit_app(app):
    """ Exit program """
    app.quit_app()


@command(
    title=_get("Show Commands"),
    category=_get("APP"),
    description=_get("Show available commands"),
    shortcut=_get("<Alt-x>"),
)
def show_commands(app):
    """ Show available commands """
    palette = PaletteFrame(app.editor_frame, app.commander)
    palette.show()


@command(
    title=_get("New File"),
    category=_get("FILE"),
    description=_get("Open new empty file"),
    shortcut=_get("<Control-n>"),
)
def new_file(app, originator=None):
    """ open new empty file """
    app.model.new_file(app.tmp_dir)


@command(
    title=_get("Open File"),
    category=_get("FILE"),
    description=_get("Open file from filesystem"),
    shortcut=_get("<Control-o>"),
)
def open_file(app, path=None):
    """ Open file from filesystem  """
    if not path:
        path = multi_open(app.data_dir)

    if path:
        if os.path.isfile(path):
            kind = filetype.guess(path)
            if kind:
                xdg_open_file(path)  # WAIT: Make Windows-version of xdg_open
            else:
                app.model.open_file(path)


@command(
    title=_get("Open Folder"),
    category=_get("FILE"),
    description=_get("Open folder from filesystem"),
    shortcut=_get("<Control-Shift-o>"),
)
def open_folder(app, path=None):
    """" Open folder from filesystem  """
    if not path:
        path = multi_open(app.data_dir, mode='dir')
    if path:
        app.model.open_folder(path)


@command(
    title=_get("Close file"),
    category=_get("FILE"),
    description=_get("Close file"),
    shortcut=_get("<Control-W>"),
)
def close_file(app, originator=None):
    """ Close file """
    tab_id = app.editor_frame.notebook.select()
    if '!hometab' not in str(tab_id):
        cancel = False
        file_obj = app.model.current_file
        text_editor = app.editor_frame.notebook.nametowidget(tab_id)

        if text_editor.modified:  # WAIT: Test med zenity yes no heller
            answer = tk.messagebox.askyesnocancel(
                title="Unsaved changes",
                message="Do you want to save changes you made to " + file_obj.basename + "?",
                default=messagebox.YES,
                parent=app.editor_frame)

            if str(answer) == 'True':
                app.model.save_file(file_obj, None, originator)
            elif str(answer) == 'None':
                cancel = True

        if not cancel:
            app.model.close_file(file_obj, originator)


@command(
    title=_get("Save file"),
    category=_get("FILE"),
    description=_get("Save file"),
    shortcut=_get("<Control-s>"),
)
def save_file(app, originator=None):
    """ Save file """
    tab_id = app.editor_frame.notebook.select()
    if '!hometab' not in str(tab_id):
        file_obj = app.model.current_file
        app.model.save_file(file_obj, None, originator)


@command(
    title=_get("Save As..."),
    category=_get("FILE"),
    description=_get("Save As..."),
    shortcut=_get("<Alt-s>"),
)
def save_file_as(app, originator=None):
    """ Save As... """
    tab_id = app.editor_frame.notebook.select()
    if '!hometab' not in str(tab_id):
        file_obj = app.model.current_file
        new_path = multi_open(app.data_dir, mode='save')
        app.model.save_file(file_obj, new_path, originator)


@command(
    title=_get("Increase Font Size"),
    category=_get("FILE"),
    description=_get("Increase Font Size"),
    shortcut=_get("<Control-+>"),
)
def increase_text_font(app):
    """ Increase Text Font Size """
    tab_id = app.editor_frame.notebook.select()
    if '!hometab' not in str(tab_id):
        text_editor = app.editor_frame.notebook.nametowidget(tab_id)
        font_size = text_editor.font_style['size']
        text_editor.font_style.configure(size=font_size + 2)


@command(
    title=_get("Decrease Font Size"),
    category=_get("FILE"),
    description=_get("Decrease Font Size"),
    shortcut=_get("<Control-->"),  # TODO: Vises ikke riktig i M-x -> pluss, eller minustegn som std i visning mellom keys?
)
def decrease_text_font(app):
    """ Decrease Text Font Size """
    tab_id = app.editor_frame.notebook.select()
    if '!hometab' not in str(tab_id):
        text_editor = app.editor_frame.notebook.nametowidget(tab_id)
        font_size = text_editor.font_style['size']
        text_editor.font_style.configure(size=font_size - 2)


@command(
    title=_get("Run File"),
    category=_get("FILE"),
    description=_get("Run File"),
    shortcut=_get("<Control-Return>"),
)
def run_file(app, stop=False):
    """ Run File """
    tab_id = app.editor_frame.notebook.select()
    if '!hometab' not in str(tab_id):
        save_file(app)
        file_obj = app.model.current_file
        text_editor = app.editor_frame.notebook.nametowidget(tab_id)
        text_editor.run_file(file_obj, stop)


@command(
    title=_get("Kill Process"),
    category=_get("FILE"),
    description=_get("Kill Process"),
    shortcut=_get("<Control-k>"),
)
def kill_process(app):
    """ Kill Process """
    run_file(app, True)


@command(
    title=_get("Toggle Comment"),
    category=_get("FILE"),
    description=_get("Toggle Comment"),
    shortcut=_get("<Alt-c"),
)
def toggle_comment(app):
    """ Toggle Comment """
    tab_id = app.editor_frame.notebook.select()
    if '!hometab' not in str(tab_id):
        file_obj = app.model.current_file
        text_editor = app.editor_frame.notebook.nametowidget(tab_id)
        text_editor.toggle_comment(file_obj)
