# GPL3 License

# Original work Copyright (c) 2019 Rene Bakker
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


import jaydebeapi

class ServiceNotFoundException(RuntimeError):
    """
    Thrown when the configured database server cannot be configured.
    """
    pass


class DriverNotFoundException(RuntimeError):
    """
    Thrown when the JDBC driver cannot be loaded into the JVM
    """
    def __init__(self, message):
        super(DriverNotFoundException, self).__init__('Jar file for JDBC not found: ' + message)


class SQLExcecuteException(Exception):
    """
    Thrown when the SQL cannot be parsed
    """
    pass

class DatabaseError(jaydebeapi.DatabaseError):
    pass

class CommitException(Exception):
    """
    Thrown when jdbc.commmit() fails
    """
    pass

class UnsupportedDatabaseTypeException(Exception):
    pass

class EmptyFileError(Exception):
    """
    Thrown if an input data buffer is empty
    """
    pass