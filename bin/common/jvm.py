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

import jpype as jp
import jpype.imports
import jpype.config


# TODO: Fjern java path som arg når testet nok først. Eller enklere med den på win?
def init_jvm(class_paths, max_heap_size):

    if jp.isJVMStarted():
        return

    jp.config.destroy_jvm = False
    jp.startJVM(jp.getDefaultJVMPath(),  # java_path,
                '-Djava.class.path=%s' % class_paths,
                '-Dfile.encoding=UTF8',
                '-ea', max_heap_size,
                )



def wb_batch(class_paths, max_java_heap):
    # Start Java virtual machine if not started already:
    init_jvm(class_paths, max_java_heap)

    # Create instance of sqlwb Batchrunner:
    WbManager = jp.JPackage('workbench').WbManager
    WbManager.prepareForEmbedded()
    batch = jp.JPackage('workbench.sql').BatchRunner()
    batch.setAbortOnError(True)
    return batch
