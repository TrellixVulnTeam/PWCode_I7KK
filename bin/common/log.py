# Copyright (C) 2022 Morten Eek

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

from loguru import logger
import sys


def configure_logging(log_file):
    config = {
        "handlers": [
            {"sink": sys.stderr,
             "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{message}</level>"
             },
            {"sink": log_file,
             "format": "{time:YYYY-MM-DD HH:mm:ss}<level> {level: <7}</level> <level>{message}</level>"
             },
        ]
    }

    logger.configure(**config)
