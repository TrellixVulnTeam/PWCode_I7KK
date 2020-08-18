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

import tkinter.ttk

from settings import Palette


def build_style(colors: Palette):
    """Create a flat design style based on a palette of colors"""

    style = tkinter.ttk.Style()

    style.theme_create(
        "pwcode",
        parent="default",
        settings={
            ".": {"configure": {"background": colors.bg, "foreground": colors.fg}},
            "TNotebook": {
                "configure": {
                    "tabmargins": [0, 0, 0, 0],
                    "background": colors.bg,
                    "borderwidth": 0,
                }
            },
            "TNotebook.Tab": {
                "configure": {
                    "padding": [8, 12, 18, 12],
                    "background": colors.bg,
                    "foreground": colors.fg,
                    "borderwidth": 0,
                },
                "map": {
                    "background": [
                        ("selected", colors.tab_bg),
                        ("!selected", colors.tab_inactive_bg),
                    ],
                    "foreground": [("selected", colors.tab_fg)],
                    "expand": [("selected", [1, 1, 1, 0])],
                },
            },
            "TPanedwindow": {
                "configure": {"background": colors.tab_bg, "foreground": colors.tab_bg}
            },
            "SideBar.TFrame": {"configure": {"background": colors.sidebar_bg}},
            "SideBar.TButton": {
                "configure": {
                    "background": colors.sidebar_bg,
                    "foreground": colors.sidebar_fg,
                }
            },
            "SidePanel.TFrame": {"configure": {"background": colors.bg}},
            "SidePanel.Label": {
                "configure": {"background": colors.bg, "foreground": colors.fg}
            },
            "SidePanel.Treeview": {
                "configure": {
                    "background": colors.bg,
                    "fieldbackground": colors.bg,
                    "foreground": colors.fg,
                },
                "map": {
                    "background": [("selected", colors.selected_bg)],
                    "foreground": [("selected", colors.selected_fg)],
                },
            },
            "StatusBar.TFrame": {
                "configure": {
                    "background": colors.status_bg,
                    "foreground": colors.status_fg,
                }
            },
            "StatusBar.TLabel": {
                "configure": {
                    "background": colors.status_bg,
                    "foreground": colors.status_fg,
                    "font": ("", 8, ""),
                }
            },
            "Home.TFrame": {"configure": {"background": colors.tab_bg}},
            "Heading.TLabel": {
                "configure": {
                    "background": colors.tab_bg,
                    "foreground": colors.tab_fg,
                    "font": ("", 24, ""),
                }
            },
            "SubHeading.TLabel": {
                "configure": {
                    "background": colors.tab_bg,
                    "foreground": colors.fg,
                    "font": ("", 16, ""),
                }
            },
            "Text.TLabel": {
                "configure": {
                    "background": colors.tab_bg,
                    "foreground": colors.fg,
                    "font": ("", 16, ""),
                }
            },
            "Text.TEntry": {
                "configure": {
                    "background": 'red',
                    "foreground": colors.fg,
                    "font": ("", 16, ""),
                }
            },

            "Links.TFrame": {
                "configure": {"background": colors.tab_bg, "foreground": colors.fg}
            },
            "Links.TLabel": {
                "configure": {"background": colors.tab_bg, "foreground": colors.fg}
            },
            "Links.TButton": {
                "configure": {"background": colors.tab_bg, "foreground": colors.link}
            },
            "Run.TButton": {
                "configure": {"background": colors.tab_bg, "foreground": colors.green}
            },
            "Entry.TButton": {
                "configure": {"background": colors.tab_bg, "foreground": colors.fg}
            },
            "PaletteSelected.TFrame": {
                "configure": {
                    "background": colors.selected_bg,
                    "foreground": colors.selected_fg,
                }
            },
            "PaletteSelected.TLabel": {
                "configure": {
                    "background": colors.selected_bg,
                    "foreground": colors.selected_fg,
                }
            },
        },
    )

    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    return style
