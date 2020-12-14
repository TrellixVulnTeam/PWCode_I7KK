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

import os
from pathlib import Path

# pylint: disable=too-few-public-methods


class FSEntryFactory:
    """A factory of model objects with a cache"""

    def __init__(self, cache_size=1024):
        self.__cache = {}
        self.cache_size = cache_size

    def get_entry(self, path, class_obj):
        """ build a FSEntry instance or use cache"""
        path = os.path.abspath(path)
        # path = str(Path(path))
        if path in self.__cache:
            file_obj = self.__cache[path]
        else:
            file_obj = class_obj(path)
            # if len(self.__cache) > self.cache_size:
            #     self.clear_cache()
            self.__cache[file_obj.path] = file_obj

        file_obj.factory = self
        return file_obj

    def get_folder(self, path):
        """build a Folder instance using cache """
        # path = str(Path(path))
        return self.get_entry(path, Folder)

    def get_file(self, path):
        """build a FileEntry instance using cache """
        # path = str(Path(path))
        return self.get_entry(path, FileEntry)

    # def clear_cache(self): # TODO: For mye bugs med denne. Trengs den?
    #     for index, (path, _) in enumerate(self.__cache.keys()).items():
    #         if index < self.cache_size:
    #             del self.__cache[path]
    #         else:
    #             break


class FSEntry:
    """Base class for the model """

    def __init__(self, path):
        assert isinstance(path, str)
        self.path = os.path.abspath(path)
        # self.path = str(Path(os.path.abspath(path)))
        self.modified = False
        self.__basename = None
        self.parent = None
        self.factory = None

    def __get_basename(self):
        if self.__basename is None:
            self.__basename = os.path.basename(self.path)
        return self.__basename

    basename = property(__get_basename)

    dirname = property(lambda self: os.path.dirname(self.path))

    def __hash__(self):
        return self.path

    def __eq__(self, other):
        return self.path == other.path

    def __lt__(self, other):
        return self.path < other.path


class FileEntry(FSEntry):
    """File entry model class"""

    def __get_content(self):
        content = None
        if os.path.isfile(self.path):
            content = open(self.path).read()
        else:
            content = 'empty_buffer'

        return content

    content = property(__get_content)


class Folder(FSEntry):
    """Folder model: contains other entries """

    def __get_entries(self):
        dir_entries = []
        file_entries = []
        for path in os.listdir(self.path):
            path = os.path.join(self.path, path)
            bname = os.path.basename(path)

            if not os.path.islink(path) and not bname.startswith('.'):
                if os.path.isdir(path) and os.access(path, os.W_OK):
                    dir_entries.append(self.factory.get_folder(path))
                else:
                    file_entries.append(self.factory.get_file(path))
        dir_entries.sort()
        file_entries.sort()
        return dir_entries + file_entries

    entries = property(__get_entries)


class PWCodeModel:
    """A model that implements a simple observer pattern """

    def __init__(self):
        """ constructor """
        self.factory = FSEntryFactory()
        self.openfiles = []
        self.folders = []
        self.recent_folders = []
        self.recent_files = []  # TODO: Sjekk hva denne brukes til ift. Kombinere med recent_links i app?
        self.initial_activity = None
        self.observers = []
        self.current_file = None
        self.current_folder = None
        self.preview = None

    def add_observer(self, obverser):
        """ add an observer to the model """
        self.observers.append(obverser)

    def update_observers(self, method_name, *args, originator=None, **kw):
        """
        execute method_name callback in observers, skipping originator.
        returns list of return value of all callbacks
        """

        return [
            getattr(observer, method_name)(*args, **kw)
            for observer in self.observers
            if hasattr(observer, method_name)
            and getattr(observer, method_name).__self__ is not originator
        ]

    def open_folder(self, path, originator=None):
        """open a folder """
        path = str(Path(path))
        folder = self.factory.get_folder(path)

        if folder in self.recent_folders:
            self.recent_folders.remove(folder)

        self.recent_folders.insert(0, folder)

        if folder in self.folders:
            self.set_current_folder(folder, originator)
        else:
            self.folders.append(folder)
            self.update_observers("on_folder_open", folder, originator=originator)

    def open_file(self, path, originator=None):
        """open a single file"""
        path = str(Path(path))
        file_obj = self.factory.get_file(path)

        if file_obj in self.recent_files:
            self.recent_files.remove(file_obj)

        if file_obj in self.openfiles:
            self.set_current_file(file_obj, originator)
        else:
            self.openfiles.append(file_obj)
            self.update_observers("on_file_open", file_obj, originator=originator)

    def close_file(self, file_obj, originator=None):
        """ remove a file entry from the model """
        if file_obj not in self.openfiles:
            return

        self.recent_files.insert(0, file_obj)

        i = self.openfiles.index(file_obj)
        self.openfiles.remove(file_obj)
        self.update_observers("on_file_closed", file_obj, originator=originator)
        if self.openfiles:
            if i == 0:
                self.set_current_file(self.openfiles[0])
            else:
                self.set_current_file(self.openfiles[i - 1])
        else:
            self.set_current_file(None)

    def set_current_file(self, file_obj, originator=None):
        """ fire on_file_selected event to observers"""
        self.current_file = file_obj
        self.update_observers("on_file_selected", file_obj, originator=originator)

    def set_current_folder(self, folder, originator=None):
        """ fire on_folder_selected event to observers"""
        self.current_folder = folder
        self.update_observers("on_folder_selected", folder, originator=originator)

    def save_file(self, file_obj, new_path, originator=None):
        """ save file """
        new_path = str(Path(new_path))
        self.update_observers("on_file_save", file_obj, new_path, originator=originator)

    def get_file_obj(self, path_or_obj):
        """If path_or_obj is a string, build and return a FileEntry instance.
        If path_or_obj is a FileEntry instance, return it.
        Seems strange but sometime useful
            """
        if isinstance(path_or_obj, str):
            return self.factory.get_file(path_or_obj)
        elif isinstance(path_or_obj, FileEntry):
            return path_or_obj

    def new_file(self, tmp_dir, originator=None):
        """open new empty file"""
        # WAIT: Slå sammen med open_file. For mye duplisering nå.
        i = 1
        while True:
            file_name = 'Untitled-' + str(i)
            file_path = tmp_dir + '/' + file_name
            file_path = str(Path(file_path))

            if self.factory.get_file(file_path) not in self.openfiles and not os.path.isfile(file_path):
                file_obj = self.factory.get_file(file_path)

                if file_obj in self.recent_files:
                    self.recent_files.remove(file_obj)

                if file_obj in self.openfiles:
                    self.set_current_file(file_obj, originator)
                else:
                    self.openfiles.append(file_obj)
                    self.update_observers("on_file_open", file_obj, originator=originator)
                break
            else:
                i += 1

        Path(file_path).touch()  # WAIT: Bør flyttes fra model
