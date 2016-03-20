# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


class NamosException(Exception):
    def __init__(self, **kwargs):
        self.message = kwargs.get('message') or "UNKNOWN"
        self.data = kwargs.get('data') or {}
        self.error_code = kwargs.get('error_code') or -1
        self.http_status_code = kwargs.get('http_status_code') or 500

    def __str__(self):
        return unicode(self.message).encode('UTF-8')

    def __unicode__(self):
        return unicode(self.message)

    def __deepcopy__(self, memo):
        return self.__class__(**self.kwargs)
