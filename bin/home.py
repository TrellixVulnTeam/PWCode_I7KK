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

from common.xml_settings import XMLSettings
from collections import Counter
from pathlib import Path
import inspect
import os
import webbrowser
import shutil
import tkinter as tk
from tkinter import ttk
from gui.dialog import multi_open
import pathlib
from project import Project, SubProject
from links import LinksFrame, RecentLinksFrame


class HomeTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="Home.TFrame", padding=[56, 12, 8, 8])
        self.heading = ttk.Label(self, text=app.settings.name, style="Heading.TLabel")
        self.heading.pack(side=tk.TOP, anchor=tk.W)

        self.subproject_frames = []
        self.msg_label = None
        self.system_dir = None
        self.project_dir_created = False

        frame = ttk.Frame(self, style="Home.TFrame")
        frame.pack(fill=tk.BOTH, expand=1, pady=12)
        frame.pack_propagate(False)

        self.left_frame = ttk.Frame(frame, style="Home.TFrame")
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        self.right_frame = ttk.Frame(frame, style="Home.TFrame")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1, padx=(0, 56))

        self.show_start(app)
        self.show_help(app)

    def show_help(self, app):
        self.subheading = ttk.Label(self, text=app.settings.desc, style="SubHeading.TLabel")
        self.subheading.pack(side=tk.TOP, anchor=tk.W, after=self.heading)
        self.description = ttk.Label(self, text=app.settings.long_desc, style="Text.TLabel")
        self.description.pack(side=tk.TOP, anchor=tk.W, after=self.subheading)

        for widget in self.right_frame.winfo_children():
            widget.destroy()

        self.subproject_frames.clear()
        self.project_dir_created = False

        LinksFrame(
            self.right_frame,
            self,
            "Help",
            (
                ("GitHub Repository", open_home_url),
                # ("Update PWCode", lambda: update(app)), TODO: Gjør synlig når update kode er ferdig
            ),
        ).pack(side=tk.TOP, anchor=tk.W, pady=12)

    def show_start(self, app):
        LinksFrame(
            self.left_frame,
            self,
            "Start",
            (
                ("Export Data as SIP", lambda: self.export_data_project(app)),
                ("Create AIP from SIP", lambda: self.normalize_data(app)),
                ("Convert Files", lambda: self.convert_files_project(app)),  # TODO: Legg inn sjekk på at på PWLinux for at denne skal vises
                ("Copy Database", lambda: self.copy_db_project(app)),
                ("New File", app.command_callable("new_file")),
                ("Open File ...", app.command_callable("open_file")),
                ("Open Folder ...", app.command_callable("open_folder")),
            ),
        ).pack(side=tk.TOP, anchor=tk.W, pady=12)

        RecentLinksFrame(self.left_frame, self, app).pack(side=tk.TOP, anchor=tk.W, pady=12)

    def project_entry_check(self, app, type):  # TODO: Slå sammen med run_plugin? Med arg om run? Også duplisering av kode i selve plugin main
        system_name = self.project_frame.name_entry.get()
        if not system_name:
            msg = 'Missing system name'
            if type == 'copy':
                msg = 'Missing project name'
            self.msg_label.config(text=msg)
            return
        else:
            self.msg_label.config(text='')

        self.system_dir = os.path.join(app.data_dir, system_name)  # --> projects/[system]
        system_dir = self.system_dir

        archive = os.path.join(system_dir[:-1], system_name + '.tar')
        # TODO: Flere sjekker? Sjekke mot config xml fil og, eller bare?
        # TODO: Gjenbruke mappe hvis finnes og tom eller bare visse typer innhold?

        if os.path.isfile(archive):
            msg = "'" + archive + "' already exists"
            self.msg_label.config(text=msg)
            return

        ok = self.create_project_dir(system_dir, system_name)
        if not ok:
            return

        return 'ok'

    def create_project_dir(self, path, project_name):
        if not self.project_dir_created:
            try:
                os.mkdir(path)
                self.project_dir_created = True
            except OSError:
                msg = "Can't create destination directory '%s'" % (path)
                self.msg_label.config(text=msg)
                return

        pathlib.Path(os.path.join(path, '.pwcode')).mkdir(parents=True, exist_ok=True)
        self.project_frame.configure(text=' ' + project_name + ' ')
        self.project_frame.name_entry.configure(state=tk.DISABLED)

        return 'ok'

    def reset_rhs(self, header):
        # global msg_label

        self.project_dir_created = False

        self.subheading.pack_forget()
        self.description.pack_forget()

        for widget in self.right_frame.winfo_children():
            widget.destroy()

        frame = ttk.Frame(self.right_frame, style="SubHeading.TLabel")
        frame.pack(side=tk.TOP, anchor=tk.W, pady=12, fill=tk.X)
        header_label = ttk.Label(frame, text=header, style="SubHeading.TLabel")
        header_label.pack(side=tk.LEFT, anchor=tk.N, pady=4, padx=1, fill="both", expand="yes")
        self.msg_label = ttk.Label(frame, text="", style="Links.TButton")
        self.msg_label.pack(side=tk.LEFT, anchor=tk.E, pady=4, padx=(0, 12))

    def export_data(self, app, type):
        def_name = inspect.currentframe().f_code.co_name
        config_dir = self.export_check(app)

        if len(self.subproject_frames) == 0:
            self.msg_label.config(text='No subsystems added')
            return

        if config_dir:
            project_name = self.project_frame.name_entry.get()
            self.run_plugin(app, project_name, config_dir, def_name)

    # TODO: Må lese fra xml i tmp først og så kopiere xml til prosjektmappe. Fortsatt riktig?

    def copy_db_project(self, app):
        self.reset_rhs("Copy Database")

        self.project_frame = Project(self.right_frame, app, self, "Project Name:", text=" New Data Project ", relief=tk.GROOVE)
        self.project_frame.pack(side=tk.TOP, anchor=tk.W, fill="both", expand=1, pady=12)
        name_frame = self.project_frame.name_frame

        # TODO: Endre tekst på denne til "Add Target" når en har valgt source allerede
        name_frame.add_button = ttk.Button(name_frame, text='Add Source', style="Entry.TButton", command=lambda: self.subproject_entry(app, 'copy'))
        name_frame.add_button.pack(side=tk.RIGHT, anchor=tk.N, pady=3, padx=(0, 12))

        run_button = ttk.Button(name_frame, text='Run', style="Run.TButton", command=lambda: self.copy_db(app))
        run_button.pack(side=tk.RIGHT, anchor=tk.N, pady=3, padx=(0, 12))

        options_frame = ttk.Frame(self.project_frame, style="SubHeading.TLabel")
        options_frame.pack(side=tk.TOP, anchor=tk.W, fill=tk.X, pady=(0, 20))

        memory_label = ttk.Label(options_frame, text="Allocated Memory:")
        memory_label.pack(side=tk.LEFT, anchor=tk.N, padx=(8, 0), pady=3)
        options = ['', '3 Gb', '4 Gb', '5 Gb', '6 Gb', '7 Gb', '8 Gb']
        self.project_frame.memory_option = tk.StringVar()
        self.project_frame.memory_option.set(options[2])
        memory_option = ttk.OptionMenu(options_frame, self.project_frame.memory_option, *options)
        memory_option.pack(side=tk.LEFT, anchor=tk.N, pady=3, padx=(0, 6))
        memory_option.configure(width=4)

        ddl_label = ttk.Label(options_frame, text="DDL Generation:")
        ddl_label.pack(side=tk.LEFT, anchor=tk.N, padx=(20, 0), pady=3)
        options = ['', 'Native', 'SQL Workbench']
        self.project_frame.ddl_option = tk.StringVar()
        self.project_frame.ddl_option.set(options[1])
        ddl_option = ttk.OptionMenu(options_frame, self.project_frame.ddl_option, *options)
        ddl_option.pack(side=tk.LEFT, anchor=tk.N, pady=3, padx=(0, 6))
        ddl_option.configure(width=12)

    def copy_check(self, app):
        config, config_dir = config_init('pwcode')
        config.put('name', self.project_frame.name_entry.get())
        config.put('options/memory', self.project_frame.memory_option.get())
        config.put('options/ddl', self.project_frame.ddl_option.get())

        i = 0
        for conn in self.subproject_frames:
            i += 1
            conn_name = "'Source'"
            if i > 1:
                conn_name = "'Target'"

            db_name = conn.db_name_entry.get()
            db_schema = conn.db_schema_entry.get()
            jdbc_url = conn.jdbc_url_entry.get()
            db_user = conn.db_user_entry.get()
            db_pwd = conn.db_pwd_entry.get()

            msg = None

            if len(db_name) == 0:
                msg = 'Missing Database Name in ' + conn_name
            elif len(db_schema) == 0:
                msg = 'Missing Schema Name in ' + conn_name
            elif len(jdbc_url) == 0:
                msg = 'Missing JDBC Url in ' + conn_name
            # TODO: Legg inn sjekk på user og pwd for bare visse dbtyper
            # elif len(db_user) == 0:
            #     msg = 'Missing User Name in ' + conn_name
            # elif len(db_pwd) == 0:
            #     msg = 'Missing User Password in ' + conn_name

            if msg:
                self.msg_label.config(text=msg)
                return

            self.msg_label.config(text='')

            conn_name = conn_name.replace("'", "").lower()
            config.put(conn_name + '/name', db_name)
            config.put(conn_name + '/schemas', db_schema)
            config.put(conn_name + '/jdbc_url', jdbc_url)
            config.put(conn_name + '/user', db_user)
            config.put(conn_name + '/password', db_pwd)

        config.save()
        return config_dir

    def copy_db(self, app):
        def_name = inspect.currentframe().f_code.co_name
        config_dir = self.copy_check(app)

        if len(self.subproject_frames) < 2:
            self.msg_label.config(text='Missing Source or Target')
            return

        if config_dir:
            project_name = self.project_frame.name_entry.get()
            self.run_plugin(app, project_name, config_dir, def_name)

    def convert_files(self, app):
        def_name = inspect.currentframe().f_code.co_name
        config, config_dir = config_init(def_name)

        if not hasattr(self.project_frame, 'folders_frame'):
            self.msg_label.config(text='No folders added')
            return

        project_name = self.project_frame.name_entry.get()
        if not project_name:
            self.msg_label.config(text='Missing project name')
            return

        ok = self.create_project_dir(os.path.join(app.data_dir, project_name), project_name)
        if ok:
            self.msg_label.config(text='')
        else:
            return

        config.put('name', self.project_frame.name_entry.get())
        config.put('options/merge', self.project_frame.merge_option.get())

        i = 1
        for frame, path in self.project_frame.folders_frame.folders.items():
            # frame.remove_button.configure(state=tk.DISABLED)
            config.put('folders/folder' + str(i), path)
            i += 1

        # self.project_frame.merge_option_frame.configure(state=tk.DISABLED)
        # self.project_frame.name_frame.add_button.configure(state=tk.DISABLED)

        config.save()
        self.run_plugin(app, project_name, config_dir, def_name)

    def convert_files_project(self, app):
        self.reset_rhs("Convert Files")

        self.project_frame = Project(self.right_frame, app, self, "Project Name:", text=" New Data Project ", relief=tk.GROOVE)
        self.project_frame.pack(side=tk.TOP, anchor=tk.W, fill="both", expand=1, pady=12)
        name_frame = self.project_frame.name_frame

        name_frame.add_button = ttk.Button(name_frame, text='Add Folder', style="Entry.TButton", command=lambda: self.project_frame.choose_folder(app))
        name_frame.add_button.pack(side=tk.RIGHT, anchor=tk.N, pady=3, padx=(0, 12))

        run_button = ttk.Button(name_frame, text='Run', style="Run.TButton", command=lambda: self.convert_files(app))
        run_button.pack(side=tk.RIGHT, anchor=tk.N, pady=3, padx=(0, 12))

        options_frame = ttk.Frame(self.project_frame, style="SubHeading.TLabel")
        options_frame.pack(side=tk.TOP, anchor=tk.W, fill=tk.X)
        # options_label = ttk.Label(options_frame, text="Options:", width=16)
        # options_label.pack(side=tk.LEFT, anchor=tk.N, padx=(8, 0), pady=3)

        merge_label = ttk.Label(options_frame, text="Merge Subfolders:")
        merge_label.pack(side=tk.LEFT, anchor=tk.N, pady=3, padx=(8, 0))
        options = ['', 'False', 'True']
        self.project_frame.merge_option = tk.StringVar()
        self.project_frame.merge_option.set(options[1])
        merge_option = ttk.OptionMenu(options_frame, self.project_frame.merge_option, *options)
        merge_option.pack(side=tk.LEFT, anchor=tk.N, pady=3, padx=(0, 55))
        merge_option.configure(width=4)
        # self.project_frame.merge_option = var
        self.project_frame.merge_option_frame = merge_option

    def normalize_data(self, app):
        project_dir = multi_open(app.data_dir + os.path.sep, mode='dir')
        os.environ['pwcode_project_dir'] = project_dir

        if not project_dir:
            return 'No folder chosen.'

        config_path = os.path.join(project_dir, 'pwcode.xml')
        if not os.path.isfile(config_path):
            return 'Not a PWCode SIP project'

        config = XMLSettings(config_path)
        project_name = config.get('name')
        def_name = inspect.currentframe().f_code.co_name
        config_dir = os.environ["pwcode_config_dir"]  # Get PWCode config path

        self.run_plugin(app, project_name, config_dir, def_name, project_dir)

    def export_data_project(self, app):
        self.reset_rhs("Export Data")

        self.project_frame = Project(self.right_frame, app, self, "System Name:", text=" New Data Project ", relief=tk.GROOVE)
        self.project_frame.pack(side=tk.TOP, anchor=tk.W, fill="both", expand=1, pady=12)
        name_frame = self.project_frame.name_frame

        subsystem_button = ttk.Button(name_frame, text='Add Subsystem', style="Entry.TButton", command=lambda: self.subproject_entry(app, 'export'))
        subsystem_button.pack(side=tk.RIGHT, anchor=tk.N, pady=3, padx=(0, 12))

        run_button = ttk.Button(name_frame, text='Run', style="Run.TButton", command=lambda: self.export_data(app, 'export'))
        run_button.pack(side=tk.RIGHT, anchor=tk.N, pady=3, padx=(0, 12))

        options_frame = ttk.Frame(self.project_frame, style="SubHeading.TLabel")
        options_frame.pack(side=tk.TOP, anchor=tk.W, fill=tk.X, pady=(0, 20))
        # options_label = ttk.Label(options_frame, text="Database Options:", width=16)
        # options_label.pack(side=tk.LEFT, anchor=tk.N, padx=(8, 0), pady=3)
        # # TODO: Flytt denne linjen opp på system nivå
        # # TODO: Legg inn sjekk på at ikke duplikat folder --> i choose_folder kode?

        memory_label = ttk.Label(options_frame, text="Allocated Memory:")
        memory_label.pack(side=tk.LEFT, anchor=tk.N, padx=(8, 0), pady=3)
        options = ['', '3 Gb', '4 Gb', '5 Gb', '6 Gb', '7 Gb', '8 Gb']
        self.project_frame.memory_option = tk.StringVar()
        self.project_frame.memory_option.set(options[2])
        memory_option = ttk.OptionMenu(options_frame, self.project_frame.memory_option, *options)
        memory_option.pack(side=tk.LEFT, anchor=tk.N, pady=3, padx=(0, 6))
        memory_option.configure(width=4)

        ddl_label = ttk.Label(options_frame, text="DDL Generation:")
        ddl_label.pack(side=tk.LEFT, anchor=tk.N, pady=3)
        options = ['', 'Native', 'SQL Workbench']
        self.project_frame.ddl_option = tk.StringVar()
        self.project_frame.ddl_option.set(options[1])
        ddl_option = ttk.OptionMenu(options_frame, self.project_frame.ddl_option, *options)
        ddl_option.pack(side=tk.LEFT, anchor=tk.N, pady=3, padx=(0, 6))
        ddl_option.configure(width=12)

        package_label = ttk.Label(options_frame, text="Tar with Checksum:")
        package_label.pack(side=tk.LEFT, anchor=tk.N, pady=3)
        options = ['', 'Yes', 'No']
        self.project_frame.package_option = tk.StringVar()
        self.project_frame.package_option.set(options[1])
        package_option = ttk.OptionMenu(options_frame, self.project_frame.package_option, *options)
        package_option.pack(side=tk.LEFT, anchor=tk.N, pady=3)
        package_option.configure(width=3)

    def subproject_entry(self, app, type):
        count = len(self.subproject_frames)
        ok = None

        if count == 0:
            ok = self.project_entry_check(app, type)
            if ok:
                if self.project_frame.name_frame.add_button:
                    self.project_frame.name_frame.add_button.configure(text='Add target')
        else:
            if type == 'export':
                ok = self.export_check(app)
            elif type == 'copy':
                ok = self.copy_check(app)
                if ok:
                    self.project_frame.name_frame.add_button.destroy()

        if ok:
            if count == 0:
                self.project_frame.pack_forget()
                self.project_frame.pack(side=tk.TOP, anchor=tk.W, fill='both', expand=0, pady=(0, 12))

            title = " New Subsystem "
            if type == 'copy':
                title = " Source "
                if count > 0:
                    title = " Target "

            subproject_frame = SubProject(self.right_frame, app, self, type, text=title, relief=tk.GROOVE)
            subproject_frame.pack(side=tk.TOP, anchor=tk.W, fill='both', expand=1, pady=12)
            self.subproject_frames.append(subproject_frame)

    def export_check(self, app):
        # TODO: Sjekk kobling mm her heller enn i subprocess så kan endre i gui enklere hvis noe er feil

        config, config_dir = config_init('pwcode')
        config.put('name', self.project_frame.name_entry.get())
        config.put('checksum', 'null')
        config.put('checksum_verified', 'No')
        config.put('multi_schema', 'No')
        config.put('options/memory', self.project_frame.memory_option.get())
        config.put('options/ddl', self.project_frame.ddl_option.get())
        config.put('options/create_package', self.project_frame.package_option.get())
        config.put('options/convert_files', 'Yes')
        config.put('options/upload', 'Yes')

        doc_count = 0
        db_count = 0
        subsystem_names = []
        multi_schema = False
        for subsystem in self.subproject_frames:
            subsystem_name = None

            folder_paths = []
            for frame, path in subsystem.folders_frame.folders.items():
                folder_paths.append(path)

            db_name = subsystem.db_name_entry.get()
            db_schema = subsystem.db_schema_entry.get()
            jdbc_url = subsystem.jdbc_url_entry.get()
            db_user = subsystem.db_user_entry.get()
            db_pwd = subsystem.db_pwd_entry.get()
            tables_option = subsystem.tbl_var.get().lower()[:-1]
            tables = subsystem.tables_entry.get()
            overwrite_tables = subsystem.overwrite_entry.get()

            msg = None
            # if (len(db_name) == 0 or len(db_schema) == 0):
            # if folder_paths:
            #     subsystem_name = 'doc' + str(doc_count)
            #     doc_count += 1
            #     # else:
            #     #     msg = 'Missing subsystem name'
            # elif subsystem_name in subsystem_names:
            #     msg = 'Duplicate subsystem name'
            # else:
            subsystem_name = 'db' + str(db_count)
            db_count += 1

            if ',' in db_schema:
                multi_schema = True

            if len(jdbc_url) == 0:
                msg = "Missing jdbc connection url for '" + subsystem_name + "'"
            elif (len(db_user) == 0 or len(db_pwd) == 0):
                if not jdbc_url.lower().startswith('jdbc:h2:'):
                    # WAIT: Andre enn h2 som skal unntas? Slå sammen med kode i get_db_details?
                    msg = "Missing user or password for '" + subsystem_name + "'"

            if msg:
                self.msg_label.config(text=msg)
                # WAIT: Slette system mappe hvis tom her? Også når cancel?
                return

            self.msg_label.config(text='')
            subsystem_names.append(subsystem_name)
            subsystem.configure(text=' ' + subsystem_name + ' ')

            config.put('subsystems/' + subsystem_name + '/name', db_name)
            config.put('subsystems/' + subsystem_name + '/schemas', db_schema)
            config.put('subsystems/' + subsystem_name + '/jdbc_url', jdbc_url)
            config.put('subsystems/' + subsystem_name + '/user', db_user)
            config.put('subsystems/' + subsystem_name + '/password', db_pwd)
            config.put('subsystems/' + subsystem_name + '/' + tables_option.replace(' ', '_'), tables)
            config.put('subsystems/' + subsystem_name + '/overwrite_tables', overwrite_tables)

            if jdbc_url:
                config.put('subsystems/' + subsystem_name + '/status', 'null')

            j = 0
            for path in folder_paths:
                config.put('subsystems/' + subsystem_name + '/folders/folder' + str(j) + '/path', path)
                config.put('subsystems/' + subsystem_name + '/folders/folder' + str(j) + '/status', 'null')
                j += 1

        duplicate_names = [k for k, v in Counter(subsystem_names).items() if v > 1]
        for name in duplicate_names:
            self.msg_label.config(text="Duplicate subsystem name '" + name + "'.")
            return

        if multi_schema:
            config.put('multi_schema', 'Yes')

        config.save()
        return config_dir

    def run_plugin(self, app, project_name, config_dir, def_name, project_dir=None):
        if project_dir is None:
            project_dir = os.path.join(app.data_dir, project_name)

        project_dir = os.path.join(project_dir, '.pwcode', def_name)
        Path(project_dir).mkdir(parents=True, exist_ok=True)

        for filename in os.listdir(os.path.join(config_dir, def_name)):
            # TODO: Endre kode så ikke defs.py overskriver hverandre
            new_path = os.path.join(project_dir, filename)
            if filename == 'main.py':
                new_path = os.path.join(project_dir, project_name + '_' + def_name + '.py')
                path = new_path

            shutil.copy(os.path.join(config_dir, def_name, filename), new_path)

        path = str(Path(path))
        app.model.open_file(path)
        tab_id = app.editor_frame.path2id[path]
        file_obj = app.editor_frame.id2path[tab_id]
        text_editor = app.editor_frame.notebook.nametowidget(tab_id)
        if def_name != 'normalize_data':  # WAIT: Endre når gui for normalize for messages mm
            self.show_help(app)
        text_editor.run_file(file_obj, False)


def update(app):
    # from dulwich import porcelain
    from dulwich.repo import Repo
    config = Repo(Path(app.data_dir).parent).get_config()
    print(config.get(('remote', 'origin'), 'url'))
    # TODO: Gjør ferdig kode for git pull mm
    # -> må også hente info om deps og versjon av disse og sjekke mot installert (bruke dulwich eller curl for det?)

    # webbrowser.open('https://github.com/Preservation-Workbench/PWCode', new=2)


def open_home_url():
    webbrowser.open('https://github.com/Preservation-Workbench/PWCode', new=2)


def config_init(def_name):
    config_dir = os.environ["pwcode_config_dir"]  # Get PWCode config path
    config_path = os.path.join(config_dir, 'tmp', def_name + '.xml')

    if os.path.isfile(config_path):
        os.remove(config_path)

    return XMLSettings(config_path), config_dir
