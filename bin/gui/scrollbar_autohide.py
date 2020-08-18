# GPL3 License

# Original work Copyright (c) 2019 Juliette Monsel
# Modified work Copyright 2020 Morten Eek

# Based on an idea by Fredrik Lundh (effbot.org/zone/tkinter-autoscrollbar.htm)
# adapted to support all layouts

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


from gui.scrollbar import PWScrollbar 


class AutoHideScrollbar(PWScrollbar):
    """Scrollbar that automatically hides when not needed."""
    def __init__(self, master=None, **kwargs):
        """
        Create a scrollbar.

        :param master: master widget
        :type master: widget
        :param kwargs: options to be passed on to the :class:`PWScrollbar` initializer
        """
        PWScrollbar.__init__(self, master=master, **kwargs)
        self._pack_kw = {}
        self._place_kw = {}
        self._layout = 'place'

    def set(self, lo, hi):
        """
        Set the fractional values of the slider position.
        
        :param lo: lower end of the scrollbar (between 0 and 1)
        :type lo: float
        :param hi: upper end of the scrollbar (between 0 and 1)
        :type hi: float
        """
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            if self._layout == 'place':
                self.place_forget()
            elif self._layout == 'pack':
                self.pack_forget()
            else:
                self.grid_remove()
        else:
            if self._layout == 'place':
                self.place(**self._place_kw)
            elif self._layout == 'pack':
                self.pack(**self._pack_kw)
            else:
                self.grid()
        PWScrollbar.set(self, lo, hi)

    def _get_info(self, layout):
        """Alternative to pack_info and place_info in case of bug."""
        info = str(self.tk.call(layout, 'info', self._w)).split("-")
        dic = {}
        for i in info:
            if i:
                key, val = i.strip().split()
                dic[key] = val
        return dic

    def place(self, **kw):
        """
        Place a widget in the parent widget.
        
        :param in\_: master relative to which the widget is placed
        :type in\_: widget
        :param x: locate anchor of this widget at position x of master
        :type x: int
        :param y: locate anchor of this widget at positiony of master
        :type y: int
        :param relx: locate anchor of this widget between 0 and 1
                      relative to width of master (1 is right edge)
        :type relx: float
        :param rely: locate anchor of this widget between 0 and 1
                      relative to height of master (1 is bottom edge)
        :type rely: float
        :param anchor: position anchor according to given direction 
                        ("n", "s", "e", "w" or combinations)
        :type anchor: str
        :param width: width of this widget in pixel
        :type width: int
        :param height: height of this widget in pixel
        :type height: int
        :param relwidth: width of this widget between 0.0 and 1.0
                          relative to width of master (1.0 is the same width
                          as the master)
        :type relwidth: float
        :param relheight: height of this widget between 0.0 and 1.0
                           relative to height of master (1.0 is the same
                           height as the master)
        :type relheight: float
        :param bordermode: "inside" or "outside": whether to take border width of master widget into account
        :type bordermode: str
        """
        PWScrollbar.place(self, **kw)
        try:
            self._place_kw = self.place_info()
        except TypeError:
            # bug in some tkinter versions
            self._place_kw = self._get_info("place")
        self._layout = 'place'

    def pack(self, **kw):
        """
        Pack a widget in the parent widget.
        
        :param after: pack it after you have packed widget
        :type after: widget
        :param anchor: position anchor according to given direction 
                        ("n", "s", "e", "w" or combinations)
        :type anchor: str
        :param before: pack it before you will pack widget
        :type before: widget
        :param expand: expand widget if parent size grows
        :type expand: bool
        :param fill: "none" or "x" or "y" or "both": fill widget if widget grows
        :type fill: str
        :param in\_: widget to use as container
        :type in\_: widget
        :param ipadx: add internal padding in x direction
        :type ipadx: int
        :param ipady: add internal padding in y direction
        :type ipady: int
        :param padx: add padding in x direction
        :type padx: int
        :param pady: add padding in y irection
        :type pady: int
        :param side: "top" (default), "bottom", "left" or "right": where to add this widget
        :type side: str
        """
        PWScrollbar.pack(self, **kw)
        try:
            self._pack_kw = self.pack_info()
        except TypeError:
            # bug in some tkinter versions
            self._pack_kw = self._get_info("pack")
        self._layout = 'pack'

    def grid(self, **kw):
        """
        Position a widget in the parent widget in a grid. 
        
        :param column: use cell identified with given column (starting with 0)
        :type column: int
        :param columnspan: this widget will span several columns
        :type columnspan: int
        :param in\_: widget to use as container
        :type in\_: widget
        :param ipadx: add internal padding in x direction
        :type ipadx: int
        :param ipady: add internal padding in y direction
        :type ipady: int
        :param padx: add padding in x direction
        :type padx: int
        :param pady: add padding in y irection
        :type pady: int
        :param row: use cell identified with given row (starting with 0)
        :type row: int
        :param rowspan: this widget will span several rows
        :type rowspan: int
        :param sticky: "n", "s", "e", "w" or combinations: if cell is 
                       larger on which sides will this widget stick to 
                       the cell boundary
        :type sticky: str
        """
        PWScrollbar.grid(self, **kw)
        self._layout = 'grid'
