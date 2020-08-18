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

# pylint: disable=too-many-ancestors


class StatusBar(ttk.Frame):
    """A basic status bar with a label (static for now).
    TODO: be notified when command object are executed, add widgets ...
    """

    def __init__(self, parent, app, initial_status):
        super().__init__(parent, style="StatusBar.TFrame")

        self.lc_label = ttk.Label(self)
        self.lc_label.config(text=initial_status, style="StatusBar.TLabel", padding=(2, 0, 0, 0))
        self.lc_label.pack(side=tk.LEFT)

        # self.status_label = ttk.Label(self)
        # self.status_label.config(text=initial_status, style="StatusBar.TLabel", padding=(2, 0, 0, 0))
        # self.status_label.pack(side=tk.LEFT)

        # system_name_entry.pack(side=tk.LEFT, anchor=tk.N, pady=6)

        # self.status_line.config(text='ny tekst')
        # v = tk.StringVar()
        # v.set('hhh')
        # self.status_line = ttk.Label(self, textvariable=v.get(), style="StatusBar.TLabel", padding=(5, 0, 0, 0)).pack(
        #     side=tk.LEFT
        # )
        # app.update_idletasks()

        # v.set(str(initial_status))
        # print(initial_status)
        # self.status_line.configure(text="new text")
