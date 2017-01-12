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
import uuid

from oslo_config import cfg
from oslo_context import context
from oslo_log import log

from os_namos.common import rpcapi
from oslo_utils import netutils

NAMOS_RPCAPI = None
logger = log.getLogger(__name__)

IDENTIFICATION = str(uuid.uuid4())
HEART_BEAT_STARTED = False
NAMOS_RPCSERVER_STARTED = False

cfg_opts = [
    cfg.StrOpt('region_name',
               default='RegionOne',
               help='Keystone Region Name'),
    cfg.BoolOpt('enable',
                default=True,
                help='Enable or Disable'),
]


cfg.CONF.register_opts(cfg_opts, 'os_namos')


def list_opts():
    yield 'os_namos', cfg_opts


class RegistrationInfo(object):
    def __init__(self,
                 host,
                 project_name,
                 prog_name,
                 fqdn=socket.gethostname(),
                 pid=os.getpid(),
                 config_file_list=None,
                 config_list=None,
                 region_name=None,
                 i_am_launcher=False):
        self.host = host
        self.project_name = project_name
        self.fqdn = fqdn
        self.prog_name = prog_name
        self.pid = pid
        self.config_file_dict = self.get_config_files(config_file_list)
        self.config_list = config_list or list()
        self.identification = IDENTIFICATION
        self.region_name = region_name or cfg.CONF.os_namos.region_name
        self.i_am_launcher = i_am_launcher
        self.ips = [netutils.get_my_ipv4()]

    def get_config_files(self, config_file_list):
        files = {}
        for f in config_file_list:
            files[f] = open(f).read()

        return files


class Config(object):
    def __init__(self,
                 name,
                 type,
                 value,
                 group='DEFAULT',
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
        self.group = group


def collect_registration_info():
    from oslo_config import cfg
    CFG = cfg.CONF

    def normalize_type(type):
        try:
            if str(type).find('function'):
                return 'String'
        except TypeError:  # noqa
            # TODO(mrkanag) why this type error occurs?
            return 'String'

        return type

    def get_host():
        try:
            return getattr(CFG, 'host')
        except:  # noqa
            import socket
            return socket.gethostname()

    reg_info = RegistrationInfo(host=get_host(),
                                project_name=CFG.project,
                                prog_name=CFG.prog,
                                config_file_list=CFG.config_file
                                if CFG.config_file else
                                CFG.default_config_files)

    config_list = list()
    for opt_name in sorted(CFG._opts):
        opt = CFG._get_opt_info(opt_name)['opt']
        cfg = Config(name='%s' % opt_name,
                     type='%s' % normalize_type(opt.type),
                     value='%s' % getattr(CFG, opt_name),
                     help='%s' % opt.help,
                     required=opt.required,
                     secret=opt.secret,
                     default_value='%s' % opt.default)
        config_list.append(cfg)

    for group_name in CFG._groups:
        group_attr = CFG.GroupAttr(CFG, CFG._get_group(group_name))
        for opt_name in sorted(CFG._groups[group_name]._opts):
            opt = CFG._get_opt_info(opt_name, group_name)['opt']
            cfg = Config(name="%s" % opt_name,
                         type='%s' % normalize_type(opt.type),
                         value='%s' % getattr(group_attr, opt_name),
                         help='%s' % opt.help,
                         required=opt.required,
                         secret=opt.secret,
                         default_value='%s' % opt.default,
                         group='%s' % group_name)
            config_list.append(cfg)
    reg_info.config_list = config_list

    return reg_info


def register_myself(registration_info=None,
                    start_heart_beat=True,
                    start_rpc_server=True,
                    i_am_launcher=False):
    if not cfg.CONF.os_namos.enable:
        return

    if not hasattr(cfg.CONF, 'project'):
        logger.info("NOT USING GLOABL OSLO CONF !!!")
        return

    global NAMOS_RPCAPI

    if registration_info is None:
        registration_info = collect_registration_info()

    registration_info.i_am_launcher = i_am_launcher
    import sys
    current_module = sys.modules[__name__]

    if NAMOS_RPCAPI is None:
        NAMOS_RPCAPI = rpcapi.ConductorAPI(
            project=registration_info.project_name,
            host=registration_info.host,
            identification=registration_info.identification,
            mgr=current_module
        )

    if start_rpc_server:
        manage_me()

    ctx = context.RequestContext()
    NAMOS_RPCAPI.register_myself(ctx, registration_info)

    logger.info("*** [%s ]Registeration with Namos started successfully. ***" %
                registration_info.identification)

    return registration_info.identification


def regisgration_ackw(identification):
    logger.info("*** [%s ]Registeration with Namos completed successfully. ***"
                % identification)
    heart_beat(identification)


def heart_beat(identification):
    global HEART_BEAT_STARTED

    if HEART_BEAT_STARTED:
        return

    HEART_BEAT_STARTED = True

    if NAMOS_RPCAPI:
        from oslo_service import loopingcall
        th = loopingcall.FixedIntervalLoopingCall(
            NAMOS_RPCAPI.heart_beat,
            context=context.RequestContext(),
            identification=identification)
        # TODO(mrkanag) make this periods configurable
        th.start(60, 120)

        logger.info("*** [%s] HEART-BEAT with Namos is started successfully."
                    " ***" % identification)


# TO(mrkanag) make sure this is called on process exit, hook it to right place
def i_am_dieing():
    if NAMOS_RPCAPI:
        NAMOS_RPCAPI.heart_beat(context,
                                IDENTIFICATION,
                                True)
        logger.info("*** [%s] HEART-BEAT with Namos is stopping. ***" %
                    IDENTIFICATION)
        NAMOS_RPCAPI.stop_me()
        logger.info("*** [%s] RPC Server for Namos is stopping. ***" %
                    IDENTIFICATION)


def manage_me():
    global NAMOS_RPCSERVER_STARTED

    if NAMOS_RPCSERVER_STARTED:
        return

    NAMOS_RPCSERVER_STARTED = True

    if NAMOS_RPCAPI:
        NAMOS_RPCAPI.manage_me()

        logger.info("*** [%s] RPC Server for Namos is started successfully."
                    " ***" % IDENTIFICATION)


def ping_me(id_):
    logger.info("*** PING [%s] . ***" %
                id_)
    return id_


def update_config_file(id_, name, content):
    # TODO(mrkanag) backup the existing file
    with open(name, 'w') as file:
        file.write(content)
        logger.info("*** CONF FILE [%s] UPDATE [%s] DONE. ***" % (name, id_))


def add_config(config):
    pass


def remove_config(config):
    pass


def update_config(config):
    pass


# TODO(mrkanag) Remove this before production !
if __name__ == '__main__':
    from oslo_config import cfg
    from oslo_log import log as logging

    import os_namos  # noqa

    PROJECT_NAME = 'namos'
    VERSION = '0.0.1'
    CONF = cfg.CONF

    def init_conf(prog):
        CONF(project=PROJECT_NAME,
             version=VERSION,
             prog=prog)

    def init_log(project=PROJECT_NAME):
        logging.register_options(cfg.CONF)
        logging.setup(cfg.CONF,
                      project,
                      version=VERSION)

    def read_confs():
        r = RegistrationInfo('', '', '',
                             config_file_list=['/etc/nova/nova.conf'])
        print (r.get_config_files())

    init_log()
    init_conf('test-run')

    print (register_myself())
    read_confs()
