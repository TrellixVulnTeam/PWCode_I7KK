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

import tkinter as tk
from tkinter import ttk
from gui.dialog import multi_open
from settings import COLORS
from links import LinksFrame


class Project(ttk.LabelFrame):
    def __init__(self, parent, app, grandparent, entry_text, *args, **kwargs):
        super().__init__(parent, *args, **kwargs, style="Links.TFrame")
        self.parent = parent
        self.grandparent = grandparent
        self.merge_option = None
        self.merge_option_frame = None
        self.memory_option = None
        self.ddl_option = None
        self.package_option = None

        self.name_frame = ttk.Frame(self, style="SubHeading.TLabel")
        self.name_frame.pack(side=tk.TOP, anchor=tk.W, fill=tk.X)

        self.name_label = ttk.Label(self.name_frame, text=entry_text, width=16)
        self.name_label.pack(side=tk.LEFT, anchor=tk.N, padx=(8, 0), pady=(4, 3))

        self.name_entry = make_entry(self.name_frame, app, 56)
        self.name_entry.pack(side=tk.LEFT, anchor=tk.N, pady=(4, 3))
        self.name_entry.focus()

        self.cancel_button = ttk.Button(self.name_frame, text='Discard', style="Links.TButton", command=lambda: self.grandparent.show_help(app))
        self.cancel_button.pack(side=tk.RIGHT, anchor=tk.N, pady=3, padx=(0, 12))

    def choose_folder(self, app):
        if not hasattr(self, 'folders_frame'):
            self.folders_frame = LinksFrame(self, self.grandparent)
            self.folders_frame.pack(side=tk.TOP, anchor=tk.N, padx=(8, 0), pady=3, fill=tk.X)

        path = multi_open(app.data_dir, mode='dir')
        self.folders_frame.add_folder(path, lambda p=path: app.command_callable("open_folder")(p), 70)


class SubProject(ttk.LabelFrame):
    def __init__(self, parent, app, grandparent, type, *args, **kwargs):
        super().__init__(parent, *args, **kwargs, style="Links.TFrame")
        self.grandparent = grandparent
        self.parent = parent
        self.type = type

        self.frame1 = ttk.Frame(self, style="SubHeading.TLabel")
        self.frame1.pack(side=tk.TOP, anchor=tk.W, fill=tk.X)

        self.db_name_label = ttk.Label(self.frame1, text="DB Name:", width=8)
        self.db_name_label.pack(side=tk.LEFT, anchor=tk.N, padx=(8, 0), pady=(4, 3))
        self.db_name_entry = make_entry(self.frame1, app, 25)
        self.db_name_entry.pack(side=tk.LEFT, anchor=tk.N, pady=(4, 3))
        self.db_name_entry.focus()
        self.db_schema_label = ttk.Label(self.frame1, text="Schema Name:", width=12)
        self.db_schema_label.pack(side=tk.LEFT, anchor=tk.N, padx=(12, 0), pady=(4, 3))
        self.db_schema_entry = make_entry(self.frame1, app, 25)
        self.db_schema_entry.pack(side=tk.LEFT, anchor=tk.N, pady=(4, 3))
        self.cancel_button = ttk.Button(self.frame1, text='Discard', style="Links.TButton", command=lambda: self.subsystem_remove())
        self.cancel_button.pack(side=tk.RIGHT, anchor=tk.N, pady=3, padx=(0, 12))

        if type == 'export':
            self.folder_button = ttk.Button(self.frame1, text='Add Folder', style="Entry.TButton", command=lambda: self.choose_folder(app))
            self.folder_button.pack(side=tk.RIGHT, anchor=tk.N, pady=3, padx=(0, 12))

        self.frame2 = ttk.Frame(self, style="SubHeading.TLabel")
        self.frame2.pack(side=tk.TOP, anchor=tk.W, fill=tk.X)
        self.jdbc_url_label = ttk.Label(self.frame2, text="JDBC Url:", width=8)
        self.jdbc_url_label.pack(side=tk.LEFT, anchor=tk.N, padx=(8, 0), pady=3)
        self.jdbc_url_entry = make_entry(self.frame2, app, 64)
        self.jdbc_url_entry.pack(side=tk.LEFT, anchor=tk.N, pady=3)

        self.frame3 = ttk.Frame(self, style="SubHeading.TLabel")
        self.frame3.pack(side=tk.TOP, anchor=tk.W, fill=tk.X)
        self.db_user_label = ttk.Label(self.frame3, text="DB User:", width=8)
        self.db_user_label.pack(side=tk.LEFT, anchor=tk.N, padx=(8, 0), pady=3)
        self.db_user_entry = make_entry(self.frame3, app, 25)
        self.db_user_entry.pack(side=tk.LEFT, anchor=tk.N, pady=3)
        self.db_pwd_label = ttk.Label(self.frame3, text="DB Password:", width=12)
        self.db_pwd_label.pack(side=tk.LEFT, anchor=tk.N, padx=(12, 0), pady=3)
        self.db_pwd_entry = make_entry(self.frame3, app, 25)
        self.db_pwd_entry.pack(side=tk.LEFT, anchor=tk.N, pady=3)

        if type == 'export':
            self.frame5 = ttk.Frame(self, style="SubHeading.TLabel")
            self.frame5.pack(side=tk.TOP, anchor=tk.W, fill=tk.X)

            options = ['', 'Exclude Tables (comma separated)', 'Include Tables (comma separated)']
            self.tbl_var = tk.StringVar()
            self.tbl_var.set(' '.join(options[1].split(' ')[:2]) + ':')
            self.tbl_var.trace("w", self.get_option)
            self.tables_option = ttk.OptionMenu(self.frame5, self.tbl_var, *options)
            self.tables_option.pack(side=tk.LEFT, anchor=tk.N, pady=3, padx=(8, 0))
            self.tables_option.configure(width=12)
            self.tables_entry = make_entry(self.frame5, app, 57)
            self.tables_entry.pack(side=tk.LEFT, anchor=tk.N, pady=3)

            self.frame6 = ttk.Frame(self, style="SubHeading.TLabel")
            self.frame6.pack(side=tk.TOP, anchor=tk.W, fill=tk.X)

            self.overwrite_label = ttk.Label(self.frame6, text="Overwrite Tables:", width=15)
            self.overwrite_label.pack(side=tk.LEFT, anchor=tk.N, padx=(8, 0), pady=3)
            self.overwrite_entry = make_entry(self.frame6, app, 57)
            self.overwrite_entry.pack(side=tk.LEFT, anchor=tk.N, pady=(3, 6))

            self.folders_frame = LinksFrame(self, self.grandparent)
            self.folders_frame.pack(side=tk.TOP, anchor=tk.N, padx=(8, 0), pady=3, fill=tk.X)

    def choose_folder(self, app):
        path = multi_open(app.data_dir, mode='dir')
        self.folders_frame.add_folder(path, lambda p=path: app.command_callable("open_folder")(p), 70)

    def get_option(self, *args):
        value = ' '.join(self.tbl_var.get().split(' ')[:2]) + ':'
        self.tbl_var.set(value)
        self.tables_option.configure(state=tk.NORMAL)  # Just for refreshing widget

    def subsystem_remove(self):
        self.grandparent.subsystem_frames.remove(self)
        self.destroy()

        if len(self.grandparent.subsystem_frames) == 0:
            self.grandparent.project_frame.pack_forget()
            self.grandparent.project_frame.pack(side=tk.TOP, anchor=tk.W, fill="both", expand=1)


def make_entry(parent, app, width):
    entry = tk.Entry(parent,
                     font=app.font,
                     bg=COLORS.sidebar_bg,
                     disabledbackground=COLORS.sidebar_bg,
                     fg=COLORS.fg,
                     disabledforeground=COLORS.sidebar_fg,
                     bd=0,
                     insertbackground=COLORS.link,
                     insertofftime=0,
                     width=width,
                     highlightthickness=0,
                     )

    return entry
