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

import os
import socket

from oslo_context import context

from os_namos.common import rpcapi


NAMOS_RPCAPI = None


class RegistrationInfo(object):
    def __init__(self,
                 host,
                 project_name,
                 prog_name,
                 fqdn=socket.gethostname(),
                 pid=os.getpid(),
                 config_file_list=None,
                 config_dict=None):
        self.host = host
        self.project_name = project_name
        self.fqdn = fqdn
        self.prog_name = prog_name
        self.pid = pid
        self.config_file_list = config_file_list or list()

        # List of configuration which CONF is already updated with
        self.config_dict = config_dict or dict()


class Config(object):
    def __init__(self,
                 name,
                 type,
                 value,
                 help=None,
                 default_value=None,
                 required=False,
                 secret=False,
                 file=None):
        self.name = name
        self.default_value = default_value
        self.help = help
        self.type = type
        self.value = value
        self.required = required
        self.secret = secret
        self.file = file


def collect_registration_info():
    from oslo_config import cfg
    self = cfg.CONF

    def normalize_type(type):
        if str(type).find('function'):
            return 'String'
        return type

    def get_host():
        try:
            return getattr(self, 'host')
        except:  # noqa
            import socket
            return socket.gethostname()

    reg_info = RegistrationInfo(host=get_host(),
                                project_name=self.project,
                                prog_name=self.prog,
                                config_file_list=self.default_config_files)

    config_dict = dict()
    for opt_name in sorted(self._opts):
        opt = self._get_opt_info(opt_name)['opt']
        cfg = Config(name='%s' % opt_name,
                     type='%s' % normalize_type(opt.type),
                     value='%s' % getattr(self, opt_name),
                     help='%s' % opt.help,
                     required=opt.required,
                     secret=opt.secret,
                     default_value='%s' % opt.default)
        config_dict[cfg.name] = cfg

    for group_name in self._groups:
        group_attr = self.GroupAttr(self, self._get_group(group_name))
        for opt_name in sorted(self._groups[group_name]._opts):
            opt = self._get_opt_info(opt_name, group_name)['opt']
            cfg = Config(name="%s.%s" % (group_name, opt_name),
                         type='%s' % normalize_type(opt.type),
                         value='%s' % getattr(group_attr, opt_name),
                         help='%s' % opt.help,
                         required=opt.required,
                         secret=opt.secret,
                         default_value='%s' % opt.default)
            config_dict[cfg.name] = cfg
    reg_info.config_dict = config_dict

    return reg_info


def register_myself(registration_info=None):
    global NAMOS_RPCAPI

    if registration_info is None:
        registration_info = collect_registration_info()

    if NAMOS_RPCAPI is None:
        NAMOS_RPCAPI = rpcapi.ConductorAPI(
            project=registration_info.project_name)

    ctx = context.RequestContext()
    return NAMOS_RPCAPI.register_myself(ctx, registration_info)


def add_config(config):
    pass


def remove_config(config):
    pass


def update_config(config):
    pass


if __name__ == '__main__':
    # TODO(mrkanag) Remove this before production !
    from os_namos.common import config

    config.init_log()
    config.init_conf('test-run')

    reg_info = RegistrationInfo(
        host='namos_development',
        project_name=config.PROJECT_NAME,
        prog_name='sync',
        config_file_list=['/etc/namos/namos.conf'],
        config_dict={})

    print (reg_info.__dict__)

    print (register_myself(reg_info))
