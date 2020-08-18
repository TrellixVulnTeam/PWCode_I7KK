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

from text.monokai_pro import MonokaiProStyle
from pygments.util import shebang_matches
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.formatters.html import HtmlFormatter
from pygments.styles import get_style_by_name, get_all_styles
from pygments.lexers.markup import MarkdownLexer
from pygments.lexers.dotnet import CSharpLexer
from pygments.lexers.diff import DiffLexer
from pygments.lexers.shell import BashLexer
from pygments.lexers.configs import IniLexer
from pygments.lexers.ruby import RubyLexer
from pygments.lexers.perl import Perl6Lexer
from pygments.lexers.templates import HtmlPhpLexer
from pygments.lexers.html import XmlLexer
from pygments.lexers.html import HtmlLexer
from pygments.lexers.python import PythonLexer
import os
import pathlib
import sys
import tkinter as tk
from settings import COLORS
from home import HomeTab
from text.tktextext import EnhancedText
from gui.scrollbar_autohide import AutoHideScrollbar
from collections import deque
from console import ConsoleUi, Processing

# python3 -m pip download --only-binary=wheel pygments
# sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/vendor/pygments')

# pylint: disable=too-many-ancestors

# TODO: Legg inn sjekk på shebang også: https://kite.com/python/docs/pygments.lexers.ruby.shebang_matches
lexer_from_ext = {  # WAIT: Denne bør hentes fra configfil heller
    'py': PythonLexer(),
    'pyw': PythonLexer(),
    'htm': HtmlLexer(),
    'html': HtmlLexer(),
    'xml': XmlLexer(),  # WAIT: Se om finnes bedre
    'xsl': XmlLexer(),
    'rss': XmlLexer(),
    'xslt': XmlLexer(),
    'xsd': XmlLexer(),
    'wsdl': XmlLexer(),
    'php': HtmlPhpLexer(),
    'php5': HtmlPhpLexer(),
    'pl': Perl6Lexer(),
    'pm': Perl6Lexer(),
    'nqp': Perl6Lexer(),
    'p6': Perl6Lexer(),
    '6pl': Perl6Lexer(),
    'p6l': Perl6Lexer(),
    'pl6': Perl6Lexer(),
    'p6m': Perl6Lexer(),
    'pm6': Perl6Lexer(),
    't': Perl6Lexer(),
    'rb': RubyLexer(),
    'rbw': RubyLexer(),
    'rake': RubyLexer(),
    'rbx': RubyLexer(),
    'duby': RubyLexer(),
    'gemspec': RubyLexer(),
    'ini': IniLexer(),
    'init': IniLexer(),
    'sh': BashLexer(),
    'diff': DiffLexer(),
    'patch': DiffLexer(),
    'cs': CSharpLexer(),
    'md': MarkdownLexer(),  # WAIT: Virker dårlig
}

known_extensions = list(lexer_from_ext.keys())

# class EditorFrame(ScrollableNotebook):


class EditorFrame(tk.ttk.Frame):
    """ A container for the notebook, including bottom console """

    def __init__(
        self,
        parent,
        app,
    ):
        super().__init__(parent)

        self.app = app
        app.model.add_observer(self)
        self.notebook = tk.ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=tk.YES)
        self.path2id = {}
        self.id2path = {}
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.home_id = None
        self.previous_tab_paths = deque(2*[None], 2)

    def focus(self):
        self.lift()

    def get_lexer(self, path):
        lexer = None
        extension = os.path.splitext(path)[1][1:].lower()
        if extension in known_extensions:
            lexer = lexer_from_ext.get(extension)
        return lexer

    def show_home(self):
        """ show home tab at the first notebook position """
        if not self.home_id:
            if self.notebook.index("end"):
                self.notebook.insert(0, HomeTab(self, self.app), text="Home")
            else:
                self.notebook.add(HomeTab(self, self.app), text="Home")
            self.home_id = self.notebook.tabs()[0]

        self.notebook.select(self.home_id)

    def on_file_open(self, file_obj):
        """open the file object in a tab """
        # check if not already opened
        if file_obj in self.id2path.values():
            self.on_file_selected(file_obj)
            return

        lexer = self.get_lexer(file_obj.path)
        editor = TextEditorFrame(self.notebook, file_obj, lexer, self.app)
        tab_id = self.notebook.select()

        if tab_id:
            pos = self.notebook.index(tab_id)

            pos = pos + 1
            if not pos < self.notebook.index("end"):
                pos = "end"
            self.notebook.insert(pos, editor, text=file_obj.basename)

            if pos == "end":
                pos = -1
            tab_id = self.notebook.tabs()[pos]
        else:
            self.notebook.add(editor, text=file_obj.basename)
            tab_id = self.notebook.tabs()[-1]

        # fill cache and indices
        self.path2id[file_obj.path] = tab_id
        self.id2path[tab_id] = file_obj

        self.notebook.select(tab_id)

    def on_file_selected(self, file_obj):
        """select an opened file"""
        if file_obj:
            tab_id = self.notebook.select()
            if tab_id not in self.id2path or self.id2path[tab_id] is not file_obj:
                self.notebook.select(self.path2id[file_obj.path])

    def on_file_closed(self, file_obj):
        """remove the tab associated with the file object"""
        tab_id = self.path2id[file_obj.path]
        self.notebook.forget(tab_id)
        del self.path2id[file_obj.path]
        del self.id2path[tab_id]

    # TODO: Save as overskriver ikke eksisterende fil?

    def on_file_save(self, file_obj, new_path=None):
        """ save editor content to file """
        pathlib.Path(self.app.tmp_dir).mkdir(parents=True, exist_ok=True)  # TODO: Flytte til commands?
        original_path = file_obj.path
        path = original_path
        if new_path:
            path = new_path

        # lexer = self.get_lexer(path)
        tab_id = self.notebook.select()
        if tab_id:
            text_editor = self.notebook.nametowidget(tab_id)
            content = text_editor.get_content()

            try:
                with open(path, 'w') as file:
                    file.write(content)
            except Exception:
                pass
            finally:
                text_editor.modified = False

                if new_path:
                    self.app.model.close_file(file_obj)
                    self.app.model.open_file(new_path)

                    if original_path.startswith(self.app.tmp_dir + '/Untitled-'):
                        if os.path.isfile(original_path):
                            os.remove(original_path)

    def on_tab_changed(self, event):
        """tell the model the current file has changed"""
        tab_id = self.notebook.select()
        if tab_id in self.id2path:
            self.app.select_file(self.id2path[tab_id], self)

        if str(tab_id) == '.!panedwindow.!editorframe.!hometab':
            self.app.on_file_selected(None)
            self.app.statusbar.lc_label.config(text='')
            self.previous_tab_paths.append(None)
        else:
            text_editor = self.notebook.nametowidget(tab_id)
            text_editor.set_line_and_column()
            text_editor.text.focus()
            file_obj = self.id2path[tab_id]
            self.previous_tab_paths.append(file_obj.path)


class TextEditorFrame(tk.ttk.Frame):
    """ A frame that contains a text editor """

    def __init__(
        self,
        parent,
        file_obj=None,
        lexer=None,
        app=None,
        vertical_scrollbar=True,
        console=True
    ):

        super().__init__(parent)

        self.modified = False
        self.current_line = None
        self.app = app
        self.font_style = tk.font.Font(family="Ubuntu Monospace", size=11)
        # self.font_style = tk.font.Font(size=11)  # WAIT: Virker og -> ha som backup når ikke ønsket font finnes?
        self.lexer = lexer

        tab_to_spaces = False
        if self.lexer:  # WAIT: Trengs flere varianter her?
            tab_to_spaces = True

        self.text = EnhancedText(
            self,
            font=self.font_style,
            background=COLORS.text_bg,
            foreground=COLORS.text_fg,
            insertbackground=COLORS.status_bg,
            # line_numbers=True,
            # insertbackground="#eeeeee",
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            takefocus=1,
            insertofftime=0,  # Disable blinking cursor
            insertwidth=2,
            spacing1=0,
            spacing3=0,
            selectbackground=COLORS.sidebar_bg,
            inactiveselectbackground=COLORS.sidebar_bg,
            selectforeground=COLORS.text_fg,
            undo=True,
            wrap=tk.NONE,
            padx=5,
            pady=5,
            indent_with_tabs=False,
            replace_tabs=tab_to_spaces
        )

        if self.lexer:
            self.create_tags()

            def tab(arg):  # WAIT: Flytt denne og anent i app og tktextext slik at samlet alle bindings ett sted
                self.text.insert(tk.INSERT, " " * 4)  # WAIT: SJekk at ikke blir spaces for tsv-filer
                return 'break'
            self.text.bind("<Tab>", tab)

        font = tk.font.Font(font=self.text['font'])
        tab_width = font.measure(' ' * 4)  # compute desired width of tabs
        self.text.config(tabs=(tab_width,))  # configure Text widget tab stops

        if vertical_scrollbar:
            self.text.v_scrollbar = AutoHideScrollbar(
                self.text,
                command=self.v_scrollbar_scroll,
                width=10,
                troughcolor=COLORS.bg,
                buttoncolor=COLORS.bg,
                thumbcolor=COLORS.status_bg,
            )
            self.text["yscrollcommand"] = self.text.v_scrollbar.set
            self.text.v_scrollbar.pack(side="right", fill="y")

        if console and file_obj:
            self.console = ConsoleUi(self, file_obj)
            self.processing = Processing(file_obj, self.app)
            self.processing.show_message('run_file [Ctrl+Enter]\nkill_process [Ctrl+k]\n')

        self.text.pack(expand=tk.YES, fill=tk.BOTH)

        self.set_file_obj(file_obj)

        self.text.bind("<<TextChange>>", self.unsaved_text, True)
        self.text.bind("<<CursorMove>>", self.cursor_moved, True)

    def run_file(self, file_obj, stop=False):
        if not stop:
            self.console.text.config(state=tk.NORMAL)
            self.console.text.delete('1.0', tk.END)
            # self.processing.show_message('run_file [Ctrl+Enter]\nkill_process [Ctrl+k]\n')
            self.console.text.config(state=tk.DISABLED)

        self.processing.run_file(file_obj, stop)

    def toggle_comment(self, file_obj):
        def text_get_selected(text):
            if text.tag_ranges("sel"):
                return text.get(tk.SEL_FIRST, tk.SEL_LAST)
            else:
                return ""

        selection = text_get_selected(self.text)
        if selection:
            self.insert_comment(self.text.index(tk.SEL_FIRST), self.text.index(tk.SEL_LAST), file_obj)
        else:
            self.insert_comment(self.text.index(self.current_line + '.0'), self.text.index(self.current_line + '.end'), file_obj)

    def get_comment_token(self, file_obj):
        extension = os.path.splitext(file_obj.path)[1][1:].lower()
        if extension in ("py", "yml", "yaml"):  # TODO: Legg inn støtte for flere extensions
            return ("#", "")
        elif extension == "xml":
            return ("<--", "-->")
        else:
            return ("", "")

    def insert_comment(self, start, end, file_obj):
        token_start, token_end = self.get_comment_token(file_obj)
        while int(start.split(".")[0]) <= int(end.split(".")[0]):
            line = self.text.get(start + " linestart", start + " lineend")
            if line.lstrip().startswith(token_start):
                # remove comment token
                if token_start:
                    self.text.delete(start + " linestart", start + f" linestart +{len(token_start)}c")
                if token_end:
                    self.text.delete(start + f" lineend -{len(token_start)}c", start + " lineend")
            else:
                # insert comment token
                if token_start:
                    self.text.insert(start + ' linestart', token_start)
                if token_end:
                    self.text.insert(start + ' lineend', token_end)
            start = str(int(start.split(".")[0]) + 1) + ".0"
        pass

    def set_line_and_column(self):
        # text_line_count = int(self.text.index("end").split(".")[0])
        line, column = self.text.index("insert").split('.')
        self.current_line = line  # WAIT: Lagre også i recent files så huske linje når åpner fil igjen
        lc_text = str(line) + ' : ' + str(column)
        self.app.statusbar.lc_label.config(text=lc_text)

    def cursor_moved(self, event):
        self.set_line_and_column()

    def unsaved_text(self, event):
        self.set_line_and_column()
        self.modified = True
        if self.lexer:
            self.colorize(self.current_line)  # TODO: Ser ut til å oppdatere hele filen heller enn kun endret linje -> fiks

    def get_content(self):
        return self.text.get(0.0, tk.END)

    def set_file_obj(self, file_obj):
        self.file_obj = file_obj
        if file_obj:
            self.text.delete("0.0", tk.END)
            if file_obj.content != 'empty_buffer':
                self.text.insert(tk.END, file_obj.content)
            self.text.focus_set()
            if self.lexer:
                self.colorize()

    def v_scrollbar_scroll(self, *args):
        self.text.yview(*args)
        self.text.event_generate("<<VerticalScroll>>")

    def create_tags(self):
        bold_font = tk.font.Font(self.text, self.text.cget("font"))
        bold_font.configure(weight=tk.font.BOLD)
        italic_font = tk.font.Font(self.text, self.text.cget("font"))
        italic_font.configure(slant=tk.font.ITALIC)
        bold_italic_font = tk.font.Font(self.text, self.text.cget("font"))
        bold_italic_font.configure(weight=tk.font.BOLD, slant=tk.font.ITALIC)
        # style = get_style_by_name('murphy') # Eks på bruk av innebygget style
        style = HtmlFormatter(style=MonokaiProStyle).style  # Eks på bruk av custom style

        for ttype, ndef in style:
            tag_font = None

            if ndef['bold'] and ndef['italic']:
                tag_font = bold_italic_font
            elif ndef['bold']:
                tag_font = bold_font
            elif ndef['italic']:
                tag_font = italic_font

            if ndef['color']:
                foreground = "#%s" % ndef['color']
            else:
                foreground = None

            self.text.tag_configure(str(ttype), foreground=foreground, font=tag_font)

    def colorize(self, current_line=None):
        if current_line:
            code = self.text.get(self.current_line + '.0', self.current_line + '.end')
            self.text.mark_set("range_start", tk.INSERT + " linestart")
        else:
            code = self.text.get("1.0", "end-1c")
            self.text.mark_set("range_start", "1.0")

        for tag in self.text.tag_names():
            if current_line:
                self.text.tag_remove(tag, "range_start", "range_start lineend")

        tokensource = self.lexer.get_tokens(code)
        for ttype, value in tokensource:
            self.text.mark_set("range_end", f"range_start+{len(value)}c")
            self.text.tag_add(str(ttype), "range_start", "range_end")
            self.text.mark_set("range_start", "range_end")
