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
from oslo_context import context
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


def request_context(func):
    @functools.wraps(func)
    def wrapped(self, ctx, *args, **kwargs):
        if ctx is not None and not isinstance(ctx, context.RequestContext):
            ctx = context.RequestContext.from_dict(ctx.to_dict())

        return func(self, ctx, *args, **kwargs)

    return wrapped


class ConductorAPI(object):
    RPC_API_VERSION = '1.0'

    def __init__(self, host, project, identification, mgr):
        super(ConductorAPI, self).__init__()
        self.topic = 'namos.conductor'
        self.project = project
        self.host = host
        self.server_topic = identification
        self.mgr = mgr

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

        self.server = rpc.get_rpc_server(host=self.host,
                                         topic='namos.CONF.%s' %
                                               identification,
                                         endpoint=self,
                                         version=self.RPC_API_VERSION)

    @wrapper_function
    def register_myself(self, context, registration_info):
        # TODO(mrkanag): is to be call instead of cast
        return self.client.cast(context,
                                'register_myself',
                                registration_info=registration_info)

    @wrapper_function
    def heart_beat(self, context, identification, dieing=False):
        return self.client.cast(context,
                                'heart_beat',
                                identification=identification,
                                dieing=dieing)

    def manage_me(self):
        self.server.start()

    def stop_me(self):
        try:
            self.server.stop()
            self.server.wait()
        except:  # noqa
            pass

    @request_context
    def regisgration_ackw(self, context, identification):
        self.mgr.regisgration_ackw(identification)

    @request_context
    def ping_me(self, context, identification):
        identification = self.mgr.ping_me(identification)
        return identification
