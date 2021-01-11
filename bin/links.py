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
import tkinter as tk
from tkinter import ttk
import pickle


class LinksFrame(ttk.Frame):
    """ A container of links and label that packs vertically"""

    def __init__(self, parent, grandparent, title=None, links=None):
        super().__init__(parent, style="Links.TFrame")
        self.parent = parent
        self.grandparent = grandparent
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
            self.grandparent.msg_label.config(text='Not a valid path.')
            return

        if path in self.folders.values():
            self.grandparent.msg_label.config(text='Duplicate folder')
            return

        label = 'Folder: ' + path

        folder_frame = ttk.Frame(self, style="SubHeading.TLabel")
        folder_frame.pack(side=tk.TOP, anchor=tk.W, fill=tk.X)

        self.folders[folder_frame] = path

        folder_frame.folder = ttk.Button(folder_frame, text=label, style="SideBar.TButton", command=action, width=width)
        folder_frame.folder.pack(side=tk.LEFT, anchor=tk.N, pady=(1, 0))
        folder_frame.remove_button = ttk.Button(folder_frame, text=' x', style="SideBar.TButton", command=lambda: self.remove_folder(folder_frame))
        folder_frame.remove_button.pack(side=tk.LEFT, anchor=tk.N, pady=(1, 0))

        self.grandparent.msg_label.config(text='')

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

        if os.path.exists(os.path.join(self.app.tmp_dir, "recent_files.p")):
            self.app.recent_links = pickle.load(open(os.path.join(self.app.tmp_dir, "recent_files.p"), "rb"))
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
                if os.path.join('PWCode', 'bin', 'tmp', 'Untitled-') in file_obj.path:
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
