# Copyright (C) 2020 Morten Eek

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import tkinter as tk
from tkinter import ttk
import re
import codecs
import os
from functools import partial
import bs4

basestring = str


class VerticalScrolledFrame:
    """
    A vertically scrolled Frame that can be treated like any other Frame
    ie it needs a master and layout and it can be a master.
    keyword arguments are passed to the underlying Canvas (eg width, height)
    """

    def __init__(self, master, **kwargs):
        self.outer = tk.Frame(master)

        # self.vsb = tk.Scrollbar(self.outer, orient=tk.VERTICAL)
        # self.vsb.pack(fill=tk.Y, side=tk.RIGHT)
        self.canvas = tk.Canvas(self.outer, highlightthickness=0, **kwargs)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # self.canvas['yscrollcommand'] = self.vsb.set
        self.canvas.bind("<Enter>", self._bind_mouse)
        self.canvas.bind("<Leave>", self._unbind_mouse)
        # self.vsb['command'] = self.canvas.yview

        self.inner = tk.Frame(self.canvas)
        # pack the inner Frame into the Canvas with the topleft corner 4 pixels offset
        self.canvas.create_window(4, 4, window=self.inner, anchor='nw')
        self.inner.bind("<Configure>", self._on_frame_configure)

        self.outer_attr = set(dir(tk.Widget))
        self.frames = (self.inner, self.outer)

    def __getattr__(self, item):
        """geometry attributes etc (eg pack, destroy, tkraise) are passed on to self.outer
        all other attributes (_w, children, etc) are passed to self.inner"""
        return getattr(self.frames[item in self.outer_attr], item)

    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_mouse(self, event=None):
        """mouse event bind does not work, so this hack allows the use of bind_all
        Linux uses Buttons, Windows/Mac uses MouseWheel"""
        for ev in ("<Button-4>", "<Button-5>", "<MouseWheel>"):
            self.canvas.bind_all(ev, self._on_mousewheel)

    def _unbind_mouse(self, event=None):
        for ev in ("<Button-4>", "<Button-5>", "<MouseWheel>"):
            self.canvas.unbind_all(ev)

    def _on_mousewheel(self, event):
        """Linux uses event.num; Windows / Mac uses event.delta"""
        if event.num == 4 or event.delta == 120:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta == -120:
            self.canvas.yview_scroll(1, "units")


class AutoSelectEntry(ttk.Entry):
    elements = []

    def __init__(self, master, command=None, **kwargs):
        """Entry widget that auto selects when focused
        command is a function to execute on value change"""
        ttk.Entry.__init__(self, master, **kwargs)
        self.command = command
        self.old_value = None
        self.elements.append(self)
        self.dirty = False

        self.bind('<FocusIn>', self.select_all)
        self.bind('<Return>', self.input_change)
        self.bind('<FocusOut>', self.input_change)

    def select_all(self, event=None):
        self.selection_range(0, tk.END)

    def input_change(self, event=None, value=None):
        if value is None:
            value = self.get()
        if self.command is not None:
            if value == self.old_value:
                return  # check for a change; prevent command trigger when just tabbing through
            self.dirty = True
            self.old_value = value
            self.command(value)
        self.select_all()

    def set(self, text=None, run=False):
        if text is None:
            text = ""
        if len(text) > 500:
            text = "<too long to display>"
        self.delete(0, tk.END)
        self.insert(0, text)
        self.old_value = text
        if run:
            self.input_change(text)


class GUI(tk.Frame):
    def __init__(self, master):
        tk.Frame.__init__(self, master)

        self.fn = None
        self.bs = None
        master.title("Input")
        # icon = tk.PhotoImage(data=icondata)
        # master.tk.call('wm', 'iconphoto', master._w, icon)
        # master.geometry(opt.get('geometry'))
        master.protocol('WM_DELETE_WINDOW', self._quit)
        master.bind("<Control - S>", self.save)
        master.bind("<Control - s>", self.save)

        # self.top = FilePicker(self, command=self.load_file)
        # self.top.pack(fill=tk.X)

        # self.top.load_dir(opt.get('dir') or os.getcwd())

        self.data_frame = tk.Frame(self)
        self.display = VerticalScrolledFrame(self.data_frame)
        self.display.pack(fill=tk.BOTH, expand=True)
        self.data_frame.pack(fill=tk.BOTH, expand=True)
        self.load_file('/home/bba/bin/PWCode/bin/xml/edit.xml')

    def _quit(self):
        # if opt.get('save_position'):
        #     opt['geometry'] = self.master.geometry()
        # else:
        #     # strip the position information; keep only the size information
        #     opt['geometry'] = self.master.geometry().split('+')[0]
        self.master.destroy()

    def load_file(self, fn):
        print('loading', fn)
        self.fn = os.path.normpath(fn)
        AutoSelectEntry.elements = []
        # "rb" mode is python 2 and 3 compatibe; BS handles the unicode conversion.
        with open(fn, 'rb') as f:
            self.bs = bs4.BeautifulSoup(f, 'xml')
        elements, comments = [], []
        for e in self.bs.contents:
            if istag(e):
                elements.append(e)
            elif isinstance(e, basestring):
                comments.append(e)
            else:
                print("WARNING: unidentified elements found:", e)
        if len(elements) > 1:
            print("WARNING: %s root elements found; one expected")
        assert elements, "No XML data found"

        if self.display is not None:
            self.display.destroy()
            del self.display
        start = elements[0]
        self.display = VerticalScrolledFrame(self.data_frame)
        if comments:
            hlm = ttk.LabelFrame(self.display, text="File Comments")
            for comm in comments:
                lbl = tk.Label(hlm, text=comm, anchor='w', wraplength=300, justify=tk.LEFT)
                lbl.pack(fill=tk.X)
            hlm.pack()
        core = self.make_label_frame(self.display, start)
        core.pack()
        self.display.pack(expand=True, fill=tk.BOTH)

    def save(self, event=None):
        print("Saving data")

        # trigger current variable if needed
        current = self.focus_get()
        if hasattr(current, 'input_change'):
            current.input_change()

        try:
            self.save_core()
        except Exception as e:
            print("Save Error", "Could not save file.\n"+str(e))

    def save_core(self):
        if self.fn is None:
            print("cannot save - no file loaded")
            return
        name, ext = os.path.splitext(self.fn)
        # bkup_name = name + time.strftime("_%Y-%m-%d_%H-%M-%S") + ext + 'bak'
        # os.rename(self.fn, bkup_name)
        # print(self.fn, "backed up to", bkup_name)

        # whatever weirdness Andrew uses encodes in utf-16 and with windows-style line endings ... so I will too.
        # but beautifulsoup insists on normal output, so have to change it first.
        encoding = 'utf8'
        if encoding == 'autodetect':
            encoding = self.bs.original_encoding
            print(encoding, "encoding autodetected")
            if encoding.startswith('utf-16'):  # remove the "le" (MS BOM)
                encoding = 'utf-16'

        data = self.bs.prettify()
        data = MSiffy(data)
        data = data.replace('\n', '\r\n')  # Windows ... (sigh)
        data = data.replace('utf-8', encoding, 1)  # BS insists on utf8 output from prettify

        with codecs.open(self.fn, 'w', encoding) as f:
            f.write(data)

        for element in AutoSelectEntry.elements:
            element.dirty = False

    def make(self, frame, bs):
        children = list(filter(istag, bs.children))
        idx = 0

        # list out the attributes, then text, then grandchildren.
        for attr, value in bs.attrs.items():
            # attribute entry
            idx = self.make_entry(frame, idx, attr, value.strip(), partial(self.change_attr, bs, attr))
        if bs.string is not None:
            # text entry
            idx = self.make_entry(frame, idx, "", bs.text.strip(), partial(self.change_attr, bs, None))
        for child in children:
            num_children = len(child.findChildren()) + len(child.attrs)
            if num_children == 0 and child.string is not None:
                # special case of only 1 text - making entry
                idx = self.make_entry(frame, idx, child.name, child.string.strip(), partial(self.change_attr, child, None))
            elif num_children > 0:
                # child has one attribute or one grandchild; make new frame
                h = self.make_label_frame(frame, child)
                h.pack()
                # h.grid(row=idx, column=0, columnspan=2, sticky='ew', padx=10, pady=10)
                idx += 1
            # else: tag has no children and no text; ignore

    @staticmethod
    def make_entry(master, row, name, value, command):
        lbl = tk.Label(master, text=name, anchor='e')
        # lbl.grid(row=row, column=0, sticky='ew')
        lbl.pack()
        ent = AutoSelectEntry(master, width=50, command=command)
        ent.set(value)
        ent.pack()
        # ent.grid(row=row, column=1, sticky='e')
        return row + 1

    def make_label_frame(self, master, bs):
        frame = ttk.LabelFrame(master, text=bs.name)
        hlm = tk.Frame(frame)
        hlm.columnconfigure(0, weight=1)
        self.make(hlm, bs)
        hlm.pack(side=tk.RIGHT)
        return frame

    def dirty_status(self):
        changes = "{} unsaved changes".format(sum(x.dirty for x in AutoSelectEntry.elements))
        print(changes)

    def change_attr(self, bs, attr, new_text):
        if attr is None:
            bs.string = new_text
        else:
            bs[attr] = new_text
        self.dirty_status()


def istag(test):
    return isinstance(test, bs4.Tag)


def MSiffy(data):
    """convert the beautifulsoup prettify output to a microsoft .NET style
    Basically this means moving the contents of tags into the same line as the tag"""
    hlm = []
    state = False
    leading_spaces = re.compile(r"^\s*")
    for line in data.splitlines():
        if "<" in line:
            if state:
                line = line.strip()
            else:
                spaces = leading_spaces.search(line).group(0)
                line = spaces + line
            hlm.append(line)
            state = False
        else:
            hlm.append("\n" + line.strip() + "\n")
            state = True
    nd = "\n".join(hlm)
    return nd.replace("\n\n", "")


def main():
    root = tk.Tk()
    window = GUI(root)
    window.pack(fill=tk.BOTH, expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
