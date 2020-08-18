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


from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, Text, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


DARK_GREY = "#363537"
LIGHT_GREY= "#69676c"
RED = "#fc618d"
GREEN = "#7bd88f"
YELLOW = "#fce566"
ORANGE = "#fd9353"
PURPLE = "#948ae3"
CYAN = "#5ad4e6"
WHITE = "#f7f1ff"

class MonokaiProStyle(Style):
    """
    This style mimics the Monokai Pro color scheme.
    """

    background_color = DARK_GREY
    highlight_color = "#49483e"

    styles = {
        # No corresponding class for the following:
        Text:                      WHITE, # class:  ''
        Error:                     "#fc618d bg:#1e0010", # class: 'err'

        Comment:                   LIGHT_GREY, # class: 'c'
        Comment.Multiline:         YELLOW,        # class: 'cm'

        Keyword:                   RED, # class: 'k'
        Keyword.Namespace:         GREEN, # class: 'kn'

        Operator:                  RED, # class: 'o'

        Punctuation:               WHITE, # class: 'p'

        Name:                      WHITE, # class: 'n'
        Name.Attribute:            GREEN, # class: 'na' - to be revised
        Name.Builtin:              CYAN,        # class: 'nb'
        Name.Builtin.Pseudo:       ORANGE,        # class: 'bp'
        Name.Class:                GREEN, # class: 'nc' - to be revised
        Name.Decorator:            PURPLE, # class: 'nd' - to be revised
        Name.Exception:            GREEN, # class: 'ne'
        Name.Function:             GREEN, # class: 'nf'
        Name.Property:             ORANGE,        # class: 'py'

        Number:                    PURPLE, # class: 'm'

        Literal:                   PURPLE, # class: 'l'
        Literal.Date:              ORANGE, # class: 'ld'

        String:                    YELLOW, # class: 's'
        String.Regex:              ORANGE,        # class: 'sr'

        Generic.Deleted:           YELLOW, # class: 'gd',
        Generic.Emph:              "italic",  # class: 'ge'
        Generic.Inserted:          GREEN, # class: 'gi'
        Generic.Strong:            "bold",    # class: 'gs'
        Generic.Subheading:        LIGHT_GREY, # class: 'gu'
    }
