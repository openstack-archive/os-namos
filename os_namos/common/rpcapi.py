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

"""
Client side of the OSLO CONFIG NAMOS
"""
import functools

import json
import oslo_messaging
from oslo_messaging import RemoteError

from os_namos.common import exception as namos_exception
from os_namos.common import messaging as rpc


def wrapper_function(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RemoteError as e:
            kwargs = json.loads(e.value)
            raise namos_exception.NamosException(**kwargs)

    return wrapped


class ConductorAPI(object):
    RPC_API_VERSION = '1.0'

    def __init__(self, project):
        super(ConductorAPI, self).__init__()
        self.topic = 'namos.conductor'

        # Setup the messaging tweaks ! here
        rpc._ALIASES.update(
            {
                '%s.openstack.common.rpc.impl_kombu' % project: 'rabbit',
                '%s.openstack.common.rpc.impl_qpid' % project: 'qpid',
                '%s.openstack.common.rpc.impl_zmq' % project: 'zmq',
            }
        )

        oslo_messaging.set_transport_defaults('namos')

        self.client = rpc.get_rpc_client(version=self.RPC_API_VERSION,
                                         topic=self.topic)

    @wrapper_function
    def register_myself(self, context, registration_info):
        # TODO(mrkanag): is to be call instead of cast
        return self.client.cast(context,
                                'register_myself',
                                registration_info=registration_info)
