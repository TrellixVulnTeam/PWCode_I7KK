#! python3

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

from petl.util.base import Table
from petl.compat import text_type

def pwb_lower_case_header(table):
    return LowerCaseHeaderView(table)


class LowerCaseHeaderView(Table):
    def __init__(self, table):
        self.table = table

    def __iter__(self):
        it = iter(self.table)
        hdr = next(it)
        outhdr = tuple((text_type(f.lower())) for f in hdr)
        yield outhdr
        for row in it:
            yield row