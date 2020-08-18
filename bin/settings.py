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

import collections
import os

# application name
APP_NAME = "PWCode"

# a short description
APP_DESC = "\nPreserve data in style"

# a long description
APP_LONG_DESC = """Data and code editor for digital preservation work\n"""

# application version
APP_VERSION = "0.0a"

# default dark palette
COLOR_DATA = dict(
    bg="#252526",  # background
    fg="#adadad",  # foreground
    sidebar_bg="#333333",  # sidebar background
    sidebar_fg="#adadad",  # sidebar foreground
    tab_bg="#1e1e1e",  # tab background
    tab_fg="#ffffff",  # tab foreground
    tab_inactive_bg="#2d2d2d",  # inactive tab background
    link="#d35400",  # link color
    status_bg="#d35400",  # status bar background
    status_fg="#ffffff",  # status bar foreground
    selected_bg="#d35400",  # active selection background
    selected_fg="#ffffff",  # active selection foreground
    text_bg="#1e1e1e",  # default text editor background
    text_fg="#eeeeee",  # default text editor foreground
    green="#7bd88f",  # default text editor foreground
)

# END OF USER SETTING

# DEVELOPER SETTINGS

# command metadata as tuple:
# label, method name to call on the app object, description (optional), shortcut (optional)
# COMMAND_DATA = [
#     ("Show Home", "show_home", "Show home tab"),
#     ("FILE: Open", "open_file", "Open file from filesystem", "<Control-o>"),
#     (
#         "FILE: Open folder",
#         "open_folder",
#         "Open file from filesystem",
#         "<Control-Shift-o>",
#     ),
#     ("FILE: Close", "close_file", "Open file from filesystem", "<Control-w>"),
# ]


# List of availabled palette properties
PALETTE_PROPERTIES = [
    "bg",
    "fg",
    "sidebar_bg",
    "sidebar_fg",
    "tab_bg",
    "tab_fg",
    "tab_inactive_bg",
    "link",
    "status_bg",
    "status_fg",
    "selected_bg",
    "selected_fg",
    "text_bg",
    "text_fg",
    "green"
]

# A data structure that contains colors for theming
Palette = collections.namedtuple("Palette", PALETTE_PROPERTIES)

COLORS = Palette(**COLOR_DATA)

# image directory base on the path of this file
IMG_DIR = os.path.join(os.path.dirname(__file__), "img")


class Settings:
    """An api over setting data that also listen to model changes """

    def __init__(self, model, name=APP_NAME):
        self.model = model
        self.name = name

        model.add_observer(self)

    desc = property(lambda self: APP_DESC)
    long_desc = property(lambda self: APP_LONG_DESC)
    colors = property(lambda self: COLORS)

    def load(self):
        """ TODO """
        pass

    def save(self):
        """ TODO """
        pass

    # def on_folder_open(self, folder):
    #     """demo callback"""
    #     print("demo callback: folder '{}'' has be opened".format(folder))
