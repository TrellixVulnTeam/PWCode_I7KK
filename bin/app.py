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
import model
import settings
import theme
import commands
import threading
import pickle
import sys
import tkinter as tk
from commander import Commander
from sidebar import SideBar
from editor import EditorFrame
from statusbar import StatusBar
from xmlrpc.server import SimpleXMLRPCServer
from tkinter import messagebox
from collections import OrderedDict


class App:
    """
    Tk Code application : builds the ui and exposes an api for business logic
    like a controller
    """

    def __init__(self, tmp_dir, port_file, icon_file, python_path, data_dir):
        self.model = model.PWCodeModel()  # observable data model
        self.model.add_observer(self)
        self.settings = settings.Settings(self.model)
        self.root = None

        self.sidebar = None
        self.notebook = None
        self.statusbar = None
        self.commander = None

        self.tmp_dir = tmp_dir
        self.data_dir = data_dir
        self.port_file = port_file
        self.icon_file = icon_file
        self.python_path = python_path
        self.recent_links = OrderedDict()

    def build_ui(self):
        """  builds the user interface """
        self.root = root = tk.Tk(className=self.settings.name.lower())  # --> StartupWMClass = pwcode
        root.protocol("WM_DELETE_WINDOW", self.quit_app)

        # img = tk.Image('photo', file=self.icon_file) # TODO: Denne virker med tk8.6 men ikke tk8.5
        # img = tk.PhotoImage(self.icon_file)

        root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(file=self.icon_file))

        # root.tk.call('wm','iconphoto',root._w,img)
        # root.iconphoto(False, img)

        w = 1400  # width for the Tk root
        h = 900  # height for the Tk root
        ws = root.winfo_screenwidth()
        hs = root.winfo_screenheight()

        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)

        root.geometry('%dx%d+%d+%d' % (w, h, x, y))
        # root.option_add( "*font", "gothic" )
        # root.option_add("*Font", "Times 20 bold")

        # def_font = tk.font.nametofont("TkDefaultFont")
        # def_font.config(size=16)

        self.font = tk.font.nametofont("TkDefaultFont")
        self.font.config(size=10)  # WAIT: Gjør denne konfigurerbar. Også brukes av editor, eller fortsatt separat?

        style = theme.build_style(self.settings.colors)
        style.theme_use("pwcode")

        self.commander = Commander(self)

        # WAIT: Lag funksjon som leser ut dette auto fra commands.py
        root.bind("<Alt-x>", lambda x: self.run_command('show_commands'))
        root.bind("<Control-q>", lambda x: self.run_command('quit_app'))
        root.bind("<Control-o>", lambda x: self.run_command('open_file'))
        root.bind("<Control-O>", lambda x: self.run_command('open_folder'))
        root.bind("<Control-n>", lambda x: self.run_command('new_file'))
        root.bind("<Control-w>", lambda x: self.run_command('close_file'))
        root.bind("<Control-s>", lambda x: self.run_command('save_file'))
        root.bind("<Control-S>", lambda x: self.run_command('save_file_as'))
        root.bind("<Control-Tab>", self.perform_ctrl_tab, True)

        root.bind("<Control-Right>", lambda x: self.run_command('next_tab_in_index'))
        # TODO: Linje under gir FM kun på windows: _tkinter.TclError: bad event type or keysym "KP_Right"
        #root.bind("<Control-KP_Right>", lambda x: self.run_command('next_tab_in_index'))  # on keypad
        root.bind("<Control-KP_6>", lambda x: self.run_command('next_tab_in_index'))  # on keypad with num lock

        root.bind("<Control-Left>", lambda x: self.run_command('previous_tab_in_index'))
        # TODO: Linje under gir FM kun på windows: _tkinter.TclError: bad event type or keysym "KP_Left"
        #root.bind("<Control-KP_Left>", lambda x: self.run_command('previous_in_index'))  # on keypad
        root.bind("<Control-KP_4>", lambda x: self.run_command('previous_tab_in_index'))  # on keypad with num lock

        root.bind("<Control-plus>", lambda x: self.run_command('increase_text_font'))
        root.bind("<Control-minus>", lambda x: self.run_command('decrease_text_font'))

        root.bind("<Control-Return>", self.perform_ctrl_return, True)
        root.bind_class("Text", "<Control-Return>", lambda e: None)
        root.bind_class("Text", "<Control-k>", lambda e: None)
        root.bind("<Control-k>", lambda x: self.run_command('kill_process'))

        root.bind_class("Text", "<Alt-c>", lambda e: None)
        root.bind_class("Text", "<Alt_L><c>", lambda e: None)
        root.bind("<Alt-c>", lambda x: self.run_command('toggle_comment'))
        root.bind("<Alt_L><c>", lambda x: self.run_command('toggle_comment'))  # WAIT: Denne varianten for Alt-x også?

        # horizontal layout for the sidebar to expand / collapse panels
        self.paned = paned = tk.ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=1)

        self.sidebar = SideBar(paned, self)
        paned.add(self.sidebar)

        self.editor_frame = EditorFrame(paned, self)
        paned.add(self.editor_frame)

        initial_status = ''
        self.statusbar = StatusBar(root, self, initial_status)
        self.statusbar.pack(fill=tk.X, side=tk.BOTTOM)

    def perform_ctrl_tab(self, event=None):
        self.run_command('previous_tab')
        return "break"

    def perform_ctrl_return(self, event=None):
        self.run_command('run_file')
        return "break"

    def quit_app(self):
        """ Exit program """
        unsaved = False
        for tab_id in self.editor_frame.notebook.tabs():
            if '!hometab' not in str(tab_id):
                file_obj = self.editor_frame.id2path[tab_id]
                if file_obj.path in self.recent_links.keys():
                    del self.recent_links[file_obj.path]
                self.recent_links.update({file_obj.path: file_obj})

                text_editor = self.editor_frame.notebook.nametowidget(tab_id)
                if text_editor.modified and not unsaved:
                    unsaved = True

        if unsaved:
            confirm = messagebox.askyesno(
                message='You have unsaved changes. Are you sure you want to quit?',
                icon='question',
                title='Confirm Quit'
            )

            if unsaved and not confirm:
                return

        if os.path.exists(self.port_file):
            os.remove(self.port_file)

        for r, d, f in os.walk(self.tmp_dir):
            for file in f:
                path = self.tmp_dir + '/' + file
                if 'Untitled-' in file and os.path.getsize(path) == 0:
                    os.remove(path)

        self.root.destroy()
        pickle.dump(self.recent_links, open(self.tmp_dir + "/recent_files.p", "wb"))

    def run(self, port):
        """ launch application and server """
        threading.Thread(target=self.start_rcp_server, args=(port,), daemon=True).start()

        if not self.root:
            self.build_ui()
        self.root.mainloop()

    def focus(self):
        """ Focus existing frame """
        self.root.wm_state('iconic')
        self.root.wm_state('normal')

    def start_rcp_server(self, port):
        server = SimpleXMLRPCServer(('localhost', int(port)), logRequests=False, allow_none=True)
        server.register_instance(self)
        server.serve_forever()

    def after(self, delay, command):
        """ proxy method to Tk.after() """
        self.root.after(delay, command)

    def on_file_selected(self, file_obj):
        """ callback on file selection : set the window title """
        base_title = ''
        if file_obj:
            if file_obj.path.startswith(self.tmp_dir + '/Untitled-'):
                base_title = file_obj.basename + ' - '
            else:
                base_title = file_obj.path + ' - '

        self.root.title(base_title + self.settings.name)

    def command_callable(self, name):
        """create a callable of a command """

        def _callback(*args, **kwargs):
            self.commander.run(name, *args, **kwargs)

        return _callback

    def run_command(self, name, *args, **kwargs):
        self.commander.run(name, *args, **kwargs)

    def select_file(self, file_obj, originator):
        """ set a file as selected """
        self.model.set_current_file(file_obj, originator)
