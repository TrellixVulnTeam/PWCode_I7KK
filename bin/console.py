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

import logging
import threading
import time
import queue
import os
import subprocess
import selectors
from text.tktextext import EnhancedText
from settings import COLORS
import tkinter as tk
from gui.scrollbar_autohide import AutoHideScrollbar


# class Processing(threading.Thread):
# Original her: https://github.com/beenje/tkinter-logging-text-widget/blob/master/main.py
class ConsoleUi:
    def __init__(self, frame, file_obj):
        self.frame = frame
        self.file_obj = file_obj
        self.text = EnhancedText(
            frame,
            state='disabled',  # TODO: Denne som gjør at ikke shortcuts for copy mm virker?
            background=COLORS.bg,
            # background=COLORS.text_bg,
            # background=COLORS.sidebar_bg,
            foreground="#eeeeee",
            insertbackground=COLORS.status_bg,
            # insertbackground="#eeeeee",
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            takefocus=1,
            insertofftime=0,  # Disable blinking cursor
            insertwidth=2,
            spacing1=0,
            spacing3=0,
            # selectbackground=COLORS.sidebar_bg,
            # inactiveselectbackground = COLORS.sidebar_bg,
            # selectforeground=COLORS.text_fg,
            padx=5,
            pady=5,
            height=10)

        self.text.pack(side="bottom", fill="both")
        self.text.pack_propagate(0)
        self.text.configure(font='TkFixedFont')
        self.text.tag_config('INFO', foreground='green')
        self.text.tag_config('DEBUG', foreground=COLORS.status_bg)
        self.text.tag_config('WARNING', foreground='blue')
        self.text.tag_config('ERROR', foreground='red')
        self.text.tag_config('CRITICAL', foreground='red', underline=1)

        # Create a logging handler using a queue
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        # formatter = logging.Formatter('%(asctime)s: %(message)s')
        formatter = logging.Formatter('%(message)s')
        self.queue_handler.setFormatter(formatter)
        self.logger = logging.getLogger(self.file_obj.path)
        self.logger.setLevel('DEBUG')
        self.logger.addHandler(self.queue_handler)
        # Start polling messages from the queue
        self.frame.after(100, self.poll_log_queue)

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

    def v_scrollbar_scroll(self, *args):
        self.text.yview(*args)
        self.text.event_generate("<<VerticalScroll>>")

    def display(self, record):
        msg = self.queue_handler.format(record)
        self.text.configure(state='normal')
        self.text.insert(tk.END, msg + '\n', record.levelname)
        # self.text.update_idletasks()
        self.text.configure(state='disabled')
        # Autoscroll to the bottom
        self.text.yview(tk.END)

    def poll_log_queue(self):
        # Check every 100ms if there is a new message in the queue to display
        while True:
            try:
                record = self.log_queue.get(block=False)
            except queue.Empty:
                break
            else:
                self.display(record)
        self.frame.after(100, self.poll_log_queue)


class Processing():
    def __init__(self, file_obj, app):
        self.file_obj = file_obj
        self.app = app
        super().__init__()
        self.logger = logging.getLogger(self.file_obj.path)

    def show_message(self, message):
        def log_message(message):
            self.logger.log(logging.DEBUG, message)

        threading.Thread(target=log_message, args=(message,), daemon=True).start()

    def run_file(self, file_obj, stop=False):
        def log_run(file_obj):
            os.environ['PYTHONUNBUFFERED'] = "1"
            # from functools import partial
            # printerr = partial(print, flush=True, file=sys.stderr)

            # WAIT: Gjør generelt så ikke bare python kan brukes
            # WAIT: Bruke -u eller '-m pdb'? Eller konfigurerbart? Pr plugin?
            self.process = subprocess.Popen([self.app.python_path, '-u', file_obj.path],
                                            bufsize=1,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            universal_newlines=True  # required for line buffering
                                            )

            selector = selectors.DefaultSelector()
            selector.register(self.process.stdout, selectors.EVENT_READ)
            selector.register(self.process.stderr, selectors.EVENT_READ)

            while self.process.poll() is None:  # poll() returns None while the program is still running
                for key, mask in selector.select():
                    data = key.fileobj.readline().strip()
                    if key.fileobj is self.process.stdout:
                        self.logger.log(logging.INFO, data)
                    else:
                        self.logger.log(logging.ERROR, data)

            return_code = self.process.wait()
            selector.close()
            success = (return_code == 0)
            return (success)  # TODO: Gjøre hva når registrert at script ferdig samt om success eller ikke?

        delay = False  # WAIT: Find better method when time
        for thread in threading.enumerate():
            if thread.name == file_obj.path:
                delay = True
                self.process.terminate()
                # self.process.kill()  # WAIT: Legg inn test med delay og så kjøre process.kill hvis terminate ikke virket?

        if not stop:
            if delay:
                time.sleep(2)  # Give terminated process time to cleanup
            t = threading.Thread(name=file_obj.path, target=log_run, args=(file_obj,), daemon=True)
            t.start()


class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)
