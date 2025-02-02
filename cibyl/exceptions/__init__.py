#    Copyright 2022 Red Hat
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import sys

from cibyl.utils.colors import Colors


class CibylException(Exception):
    def __init__(self, message=''):
        """Constructor.
        """
        super().__init__(*[message])

    @staticmethod
    def setup_quiet_exceptions():
        """Sets up quiet exceptions, without tracebacks, if they are
        of the type CibylException
        """

        def quiet_hook(kind, message, traceback):
            if CibylException in kind.__bases__:
                print(Colors.red(f'{message}'))
            else:
                sys.__excepthook__(kind, message, traceback)

        sys.excepthook = quiet_hook
