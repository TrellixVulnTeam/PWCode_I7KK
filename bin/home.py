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

# from console import ConsoleUi, Processing
from common.xml_settings import XMLSettings
import inspect
import commands
import os
import webbrowser
import pickle
import shutil
import tkinter as tk
from tkinter import ttk
# from tkinter import filedialog
from settings import COLORS
from gui.dialog import multi_open
import pathlib


class HomeTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="Home.TFrame", padding=[56, 12, 8, 8])
        self.heading = ttk.Label(self, text=app.settings.name, style="Heading.TLabel")
        self.heading.pack(side=tk.TOP, anchor=tk.W)

        global subsystem_frames
        subsystem_frames = []
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

        # self.folder_list = LinksFrame(self)
        # self.folder_list.pack(side=tk.TOP, anchor=tk.N, padx=(8, 0), pady=3, fill=tk.X)

    def open_home_url(self):
        webbrowser.open('https://github.com/BBATools/PWCode', new=2)

    def show_help(self, app):
        self.subheading = ttk.Label(self, text=app.settings.desc, style="SubHeading.TLabel")
        self.subheading.pack(side=tk.TOP, anchor=tk.W, after=self.heading)
        self.description = ttk.Label(self, text=app.settings.long_desc, style="Text.TLabel")
        self.description.pack(side=tk.TOP, anchor=tk.W, after=self.subheading)

        for widget in self.right_frame.winfo_children():
            widget.destroy()

        subsystem_frames.clear()
        self.project_dir_created = False

        LinksFrame(
            self.right_frame,
            "Help",
            (
                ("GitHub repository", self.open_home_url),
            ),
        ).pack(side=tk.TOP, anchor=tk.W, pady=12)

    def show_start(self, app):
        LinksFrame(
            self.left_frame,
            "Start",
            (
                ("Export Data", lambda: self.export_data_project(app)),
                ("Convert Files", lambda: self.convert_files_project(app)),  # TODO: Legg inn sjekk på at på PWLinux for at denne skal vises
                ("New File", app.command_callable("new_file")),
                ("Open File ...", app.command_callable("open_file")),
                ("Open Folder ...", app.command_callable("open_folder")),
            ),
        ).pack(side=tk.TOP, anchor=tk.W, pady=12)

        self.recent_links_frame = RecentLinksFrame(self.left_frame, app).pack(side=tk.TOP, anchor=tk.W, pady=12)
        # self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

    def system_entry_check(self, app): # TODO: Slå sammen med run_plugin? Med arg om run? Også duplisering av kode i selve plugin main
        system_name = self.project_frame.name_entry.get()
        if not system_name:
            msg = 'Missing system name'
            msg_label.config(text=msg)
            return
        else:
            msg_label.config(text='')

        self.system_dir = app.data_dir + system_name + '_'  # --> projects/[system_]
        system_dir = self.system_dir

        archive = system_dir[:-1] + '/' + system_name + '.tar' 
        # TODO: Flere sjekker? Sjekke mot config xml fil og, eller bare?
        # TODO: Gjenbruke mappe hvis finnes og tom eller bare visse typer innhold?

        if os.path.isfile(archive):
            msg = "'" + archive + "' already exists"
            msg_label.config(text=msg)
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
                msg_label.config(text=msg)
                return

        pathlib.Path(path + '/.pwcode').mkdir(parents=True, exist_ok=True)
        self.project_frame.configure(text=' ' + project_name + ' ')
        self.project_frame.name_entry.configure(state=tk.DISABLED)

        return 'ok'


    def reset_rhs(self, header):
        global msg_label

        self.project_dir_created = False

        self.subheading.pack_forget()
        self.description.pack_forget()

        for widget in self.right_frame.winfo_children():
            widget.destroy()

        frame = ttk.Frame(self.right_frame, style="SubHeading.TLabel")
        frame.pack(side=tk.TOP, anchor=tk.W, pady=12, fill=tk.X)
        header_label = ttk.Label(frame, text=header, style="SubHeading.TLabel")
        header_label.pack(side=tk.LEFT, anchor=tk.N, pady=4, padx=1, fill="both", expand="yes")
        msg_label = ttk.Label(frame, text="", style="Links.TButton")
        msg_label.pack(side=tk.LEFT, anchor=tk.E, pady=4, padx=(0, 12))


    def config_init(self, def_name):
        config_dir = os.environ["pwcode_config_dir"]  # Get PWCode config path
        config_path = config_dir + '/tmp/' + def_name + '.xml'

        if os.path.isfile(config_path):
            os.remove(config_path)
 
        return  XMLSettings(config_path), config_dir    


    def run_plugin(self, app, project_name, config_dir, def_name):
        base_path = app.data_dir + project_name
        if def_name == 'export_data':
            base_path = app.data_dir + project_name + '_'

        for filename in os.listdir(config_dir + def_name):
            new_path = base_path + '/.pwcode/' + filename           
            if filename == 'main.py':
                new_path = base_path + '/.pwcode/' + project_name + '_' + def_name + '.py'
                path = new_path

            shutil.copy(config_dir + def_name + '/' + filename, new_path)

        app.model.open_file(path)
        tab_id = app.editor_frame.path2id[path]
        file_obj = app.editor_frame.id2path[tab_id]
        text_editor = app.editor_frame.notebook.nametowidget(tab_id)
        self.show_help(app)
        text_editor.run_file(file_obj, False)            


    def export_data(self, app):
        def_name = inspect.currentframe().f_code.co_name
        config_dir = self.export_check(app)

        if config_dir:
            project_name = self.project_frame.name_entry.get()
            self.run_plugin(app, project_name, config_dir, def_name)

   
    # TODO: Må lese fra xml i tmp først og så kopiere xml til prosjektmappe. Fortsatt riktig?
    def convert_files(self, app):
        def_name = inspect.currentframe().f_code.co_name
        config, config_dir = self.config_init(def_name)

        if not hasattr(self.project_frame, 'folders_frame'):
            msg_label.config(text='No folders added')
            return

        project_name = self.project_frame.name_entry.get()
        if not project_name:
            msg_label.config(text='Missing project name')
            return

        ok = self.create_project_dir(app.data_dir + project_name, project_name)
        if ok:
            msg_label.config(text='')
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
        # self.project_frame.name_frame.folder_button.configure(state=tk.DISABLED)

        config.save()
        self.run_plugin(app, project_name, config_dir, def_name)            


    def convert_files_project(self, app):
        self.reset_rhs("Convert Files")

        self.project_frame = Project(self.right_frame, app, self, "Project Name:", text=" New Data Project ", relief=tk.GROOVE)
        self.project_frame.pack(side=tk.TOP, anchor=tk.W, fill="both", expand=1, pady=12)
        name_frame = self.project_frame.name_frame

        name_frame.folder_button = ttk.Button(name_frame, text='Add Folder', style="Entry.TButton", command=lambda: self.project_frame.choose_folder(app))
        name_frame.folder_button.pack(side=tk.RIGHT, anchor=tk.N, pady=3, padx=(0, 12))

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


    def export_data_project(self, app):
        self.reset_rhs("Export Data")

        self.project_frame = Project(self.right_frame, app, self, "System Name:", text=" New Data Project ", relief=tk.GROOVE)
        self.project_frame.pack(side=tk.TOP, anchor=tk.W, fill="both", expand=1, pady=12)
        name_frame = self.project_frame.name_frame

        subsystem_button = ttk.Button(name_frame, text='Add Subsystem', style="Entry.TButton", command=lambda: self.subsystem_entry(app))
        subsystem_button.pack(side=tk.RIGHT, anchor=tk.N, pady=3, padx=(0, 12))

        # TODO: Lag def export_data(self, app):
        run_button = ttk.Button(name_frame, text='Run', style="Run.TButton", command=lambda: self.export_data(app))
        run_button.pack(side=tk.RIGHT, anchor=tk.N, pady=3, padx=(0, 12))

        options_frame = ttk.Frame(self.project_frame, style="SubHeading.TLabel")
        options_frame.pack(side=tk.TOP, anchor=tk.W, fill=tk.X, pady=(0, 20))
        options_label = ttk.Label(options_frame, text="Database Options:", width=16)
        options_label.pack(side=tk.LEFT, anchor=tk.N, padx=(8, 0), pady=3)
        # # TODO: Flytt denne linjen opp på system nivå
        # # TODO: Legg inn sjekk på at ikke duplikat folder --> i choose_folder kode?

        memory_label = ttk.Label(options_frame, text="Allocated memory:")
        memory_label.pack(side=tk.LEFT, anchor=tk.N, pady=3)
        options = ['', '3 Gb', '4 Gb', '5 Gb', '6 Gb', '7 Gb', '8 Gb']
        self.project_frame.memory_option = tk.StringVar()
        self.project_frame.memory_option.set(options[2])
        memory_option = ttk.OptionMenu(options_frame, self.project_frame.memory_option, *options)
        memory_option.pack(side=tk.LEFT, anchor=tk.N, pady=3, padx=(0, 55))
        memory_option.configure(width=4)

        ddl_label = ttk.Label(options_frame, text="DDL Generation:")
        ddl_label.pack(side=tk.LEFT, anchor=tk.N, pady=3)
        options = ['', 'Native', 'SQL Workbench']
        self.project_frame.ddl_option = tk.StringVar()
        self.project_frame.ddl_option.set(options[1])
        ddl_option = ttk.OptionMenu(options_frame, self.project_frame.ddl_option, *options)
        ddl_option.pack(side=tk.LEFT, anchor=tk.N, pady=3)
        ddl_option.configure(width=12)


    def subsystem_entry(self, app):
        ok = None
        if len(subsystem_frames) == 0:
            ok = self.system_entry_check(app)
        else:
            ok = self.export_check(app) # TODO: Riktig med 'ok' her?

        if ok:
            if len(subsystem_frames) == 0:
                self.project_frame.pack_forget()
                self.project_frame.pack(side=tk.TOP, anchor=tk.W, fill="both", expand=0, pady=(0, 12))

            subsystem_frame = SubSystem(self.right_frame, app, self, text=" New Subsystem ", relief=tk.GROOVE)
            subsystem_frame.pack(side=tk.TOP, anchor=tk.W, fill="both", expand=1, pady=12)
            subsystem_frames.append(subsystem_frame)


    def export_check(self, app):
        # TODO: Sjekk kobling eller at kan brukes som mappenavn her hvis db subsystem og ikke bare filer

        config, config_dir = self.config_init('pwcode')
        config.put('name', self.project_frame.name_entry.get())
        config.put('options/memory', self.project_frame.memory_option.get()) 
        config.put('options/ddl', self.project_frame.ddl_option.get())         

        i = 0
        subsystem_names = []
        for subsystem in subsystem_frames:
            subsystem_name = None

            folder_paths = []
            for frame, path in subsystem.folders_frame.folders.items():
                folder_paths.append(path)

            db_name = subsystem.db_name_entry.get().lower() 
            db_schema = subsystem.db_schema_entry.get().lower()

            msg = None
            if (len(db_name) == 0 or len(db_schema) == 0):
                if folder_paths:
                    subsystem_name = 'files' + str(i)
                    i += 1
                else:                    
                    msg = 'Missing subsystem name'
            elif subsystem_name in subsystem_names:
                msg = 'Duplicate subsystem name'
            else: 
                subsystem_name = db_name + '_' + db_schema              

            if msg:
                msg_label.config(text=msg)
                # WAIT: Slette system mappe hvis tom her? Også når cancel?
                return

            msg_label.config(text='')
            subsystem_names.append(subsystem_name)
            subsystem.configure(text=' ' + subsystem_name + ' ')

            config.put('subsystems/' + subsystem_name + '/db_name', db_name)
            config.put('subsystems/' + subsystem_name + '/schema_name', db_schema)

            j = 0
            for path in folder_paths: 
                config.put('subsystems/' + subsystem_name + '/folders/folder' + str(j), path)
                j += 1                           

        config.save()
        return config_dir


class Project(ttk.LabelFrame):
    def __init__(self, parent, app, grandparent, entry_text, *args, **kwargs):
        super().__init__(parent, *args, **kwargs, style="Links.TFrame")
        self.grandparent = grandparent
        self.merge_option = None
        self.merge_option_frame = None
        self.memory_option = None
        self.ddl_option = None

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
            self.folders_frame = LinksFrame(self)
            self.folders_frame.pack(side=tk.TOP, anchor=tk.N, padx=(8, 0), pady=3, fill=tk.X)

        path = multi_open(app.data_dir, mode='dir')
        self.folders_frame.add_folder(path, lambda p=path: app.command_callable("open_folder")(p), 70)


class SubSystem(ttk.LabelFrame):
    def __init__(self, parent, app, grandparent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs, style="Links.TFrame")
        self.grandparent = grandparent

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

        self.frame5 = ttk.Frame(self, style="SubHeading.TLabel")
        self.frame5.pack(side=tk.TOP, anchor=tk.W, fill=tk.X)

        options = ['', 'Exclude Tables (comma separated)', 'Include Tables (comma separated)']
        self.var = tk.StringVar()
        self.var.set(' '.join(options[1].split(' ')[:2]) + ':')
        self.var.trace("w", self.get_option)
        self.tables_option = ttk.OptionMenu(self.frame5, self.var, *options)
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

        self.folders_frame = LinksFrame(self)
        self.folders_frame.pack(side=tk.TOP, anchor=tk.N, padx=(8, 0), pady=3, fill=tk.X)

    def choose_folder(self, app):
        path = multi_open(app.data_dir, mode='dir')
        self.folders_frame.add_folder(path, lambda p=path: app.command_callable("open_folder")(p), 70)

    def get_option(self, *args):
        value = ' '.join(self.var.get().split(' ')[:2]) + ':'
        self.var.set(value)
        self.tables_option.configure(state=tk.NORMAL)  # Just for refreshing widget

    def subsystem_remove(self):
        subsystem_frames.remove(self)
        self.destroy()

        if len(subsystem_frames) == 0:
            self.grandparent.project_frame.pack_forget()
            self.grandparent.project_frame.pack(side=tk.TOP, anchor=tk.W, fill="both", expand=1)


class LinksFrame(ttk.Frame):
    """ A container of links and label that packs vertically"""

    def __init__(self, parent, title=None, links=None):
        super().__init__(parent, style="Links.TFrame")

        self.folders = {}

        if title:
            self.title = ttk.Label(self, text=title, style="SubHeading.TLabel")
            self.title.pack(side=tk.TOP, anchor=tk.W, pady=4, padx=1)

        if links:
            for label, action in links:
                if action:
                    self.add_link(label, action)
                else:
                    self.add_label(label)

    def add_link(self, label, action):
        ttk.Button(self, text=label, style="Links.TButton", command=action).pack(side=tk.TOP, anchor=tk.W)

    def add_folder(self, path, action, width):
        if not path:
            msg_label.config(text='Not a valid path.')
            return

        if path in self.folders.values():
            msg_label.config(text='Duplicate folder')
            return

        label = 'Folder: ' + path

        folder_frame = ttk.Frame(self, style="SubHeading.TLabel")
        folder_frame.pack(side=tk.TOP, anchor=tk.W, fill=tk.X)

        self.folders[folder_frame] = path

        folder_frame.folder = ttk.Button(folder_frame, text=label, style="SideBar.TButton", command=action, width=width)
        folder_frame.folder.pack(side=tk.LEFT, anchor=tk.N, pady=(1, 0))
        folder_frame.remove_button = ttk.Button(folder_frame, text=' x', style="SideBar.TButton", command=lambda: self.remove_folder(folder_frame))
        folder_frame.remove_button.pack(side=tk.LEFT, anchor=tk.N, pady=(1, 0))

        msg_label.config(text='')

    def remove_folder(self, folder_frame):
        del self.folders[folder_frame]
        folder_frame.pack_forget()

    def add_label(self, text):
        ttk.Label(self, text=text, style="Links.TLabel").pack(side=tk.TOP, anchor=tk.W)


class RecentLinksFrame(LinksFrame):
    """A frame display a list of last opened  in the model"""

    def __init__(self, parent, app):
        super().__init__(parent, "Open Recent")
        self.app = app

        app.model.add_observer(self)

        if os.path.exists(self.app.tmp_dir + "/recent_files.p"):
            self.app.recent_links = pickle.load(open(self.app.tmp_dir + "/recent_files.p", "rb"))
            self.update_recent_links(None)

    def update_recent_links(self, new_file_obj):
        if new_file_obj:
            if new_file_obj.path in self.app.recent_links.keys():
                del self.app.recent_links[new_file_obj.path]
            self.app.recent_links.update({new_file_obj.path: new_file_obj})

        for widget in self.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.destroy()

        for path, file_obj in reversed(self.app.recent_links.items()):
            if os.path.isfile(file_obj.path):
                if 'PWCode/bin/tmp/Untitled-' in file_obj.path:
                    if os.path.getsize(file_obj.path) == 0:
                        os.remove(file_obj.path)
                    continue

                if file_obj in self.app.model.openfiles:
                    continue

                self.add_link(file_obj.basename, lambda p=path: self.app.command_callable("open_file")(p))

    def on_file_closed(self, file_obj):
        """model callback"""
        self.update_recent_links(file_obj)

    def on_file_open(self, file_obj):
        """model callback"""
        self.update_recent_links(None)


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
