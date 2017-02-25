# Copyright 2017 ZTE Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import traceback
from threading import Thread

from lcm.nf.vnfs.const import VNF_STATUS
from lcm.pub.database.models import JobStatusModel, NfInstModel, VmInstModel, NetworkInstModel, StorageInstModel, \
    FlavourInstModel, PortInstModel, SubNetworkInstModel
from lcm.pub.exceptions import NFLCMException
from lcm.pub.msapi.nfvolcm import apply_grant_to_nfvo
from lcm.pub.utils.jobutil import JobUtil
from lcm.pub.utils.timeutil import now_time
from lcm.pub.utils.values import ignore_case_get
from lcm.pub.vimapi import adaptor

logger = logging.getLogger(__name__)


class TermVnf(Thread):
    def __init__(self, data, nf_inst_id, job_id):
        super(TermVnf, self).__init__()
        self.data = data
        self.nf_inst_id = nf_inst_id
        self.job_id = job_id
        self.terminationType = ignore_case_get(self.data, "terminationType")
        self.gracefulTerminationTimeout = ignore_case_get(self.data, "gracefulTerminationTimeout")
        self.inst_resource = {'volumn': [],  # [{"vim_id": ignore_case_get(ret, "vim_id")},{}]
                              'network': [],
                              'subnet': [],
                              'port': [],
                              'flavor': [],
                              'vm': [],
                              }

    def run(self):
        try:
            self.term_pre()
            self.grant_resource()
            self.query_inst_resource()
            # self.delete_resource()
            # self.lcm_notify()
            JobUtil.add_job_status(self.job_id, 100, "Terminate Vnf success.")
        except NFLCMException as e:
            self.vnf_term_failed_handle(e.message)
        except:
            logger.error(traceback.format_exc())
            self.vnf_term_failed_handle(traceback.format_exc())

    def term_pre(self):
        vnf_insts = NfInstModel.objects.filter(nfinstid=self.nf_inst_id)
        if not vnf_insts.exists():
            raise NFLCMException('VnfInst(%s) does not exist' % self.nf_inst_id)
        sel_vnf = vnf_insts[0]
        if sel_vnf.status != 'VNF_INSTANTIATED':
            raise NFLCMException("Don't allow to delete vnf(status:[%s])" % sel_vnf.status)
        if self.terminationType == 'GRACEFUL' and not self.gracefulTerminationTimeout:
            raise NFLCMException("Graceful termination must set timeout")

        NfInstModel.objects.filter(nfinstid=self.nf_inst_id).update(status=VNF_STATUS.TERMINATING)
        JobUtil.add_job_status(self.job_id, 10, 'Nf terminating pre-check finish')
        logger.info("Nf terminating pre-check finish")

    def grant_resource(self):
        logger.info("nf_cancel_task grant_resource begin")
        content_args = {'vnfInstanceId': self.nf_inst_id, 'vnfDescriptorId': '',
                        'lifecycleOperation': 'Instantiate', 'jobId': self.job_id,
                        'addResource': [], 'removeResource': [],
                        'placementConstraint': [], 'additionalParam': {}}

        vdus = VmInstModel.objects.filter(instid=self.nf_inst_id, is_predefined=1)
        res_index = 1
        for vdu in vdus:
            res_def = {'type': 'VDU',
                       'resDefId': str(res_index),
                       'resDesId': vdu.resouceid}
            content_args['removeResource'].append(res_def)
            res_index += 1

        logger.info('content_args=%s' % content_args)
        self.apply_result = apply_grant_to_nfvo(content_args)
        vim_info = ignore_case_get(self.apply_result, "vim")
        logger.info("nf_cancel_task grant_resource end")
        JobUtil.add_job_status(self.job_id, 20, 'Nf terminating grant_resource finish')

    def query_inst_resource(self):
        logger.info('[query_resource begin]:inst_id=%s' % self.nf_inst_id)
        # query_volumn_resource
        vol_list = StorageInstModel.objects.filter(instid=self.nf_inst_id, is_predefined=1)
        for vol in vol_list:
            vol_info = {}
            if not vol.resouceid:
                continue
            vol_info["vim_id"] = vol.vimid
            vol_info["tenant_id"] = vol.tenant
            vol_info["res_id"] = vol.resouceid
            self.inst_resource['volumn'].append(vol_info)
        logger.info('[query_volumn_resource]:ret_volumns=%s' % self.inst_resource['volumn'])

        # query_network_resource
        network_list = NetworkInstModel.objects.filter(instid=self.nf_inst_id, is_predefined=1)
        for network in network_list:
            network_info = {}
            if not network.resouceid:
                continue
            network_info["vim_id"] = network.vimid
            network_info["tenant_id"] = network.tenant
            network_info["res_id"] = network.resouceid
            self.inst_resource['network'].append(network_info)
        logger.info('[query_network_resource]:ret_networks=%s' % self.inst_resource['network'])

        # query_subnetwork_resource
        subnetwork_list = SubNetworkInstModel.objects.filter(instid=self.nf_inst_id, is_predefined=1)
        for subnetwork in subnetwork_list:
            subnetwork_info = {}
            if not subnetwork.resouceid:
                continue
            subnetwork_info["vim_id"] = subnetwork.vimid
            subnetwork_info["tenant_id"] = subnetwork.tenant
            subnetwork_info["res_id"] = subnetwork.resouceid
            self.inst_resource['subnet'].append(subnetwork_info)
        logger.info('[query_subnetwork_resource]:ret_networks=%s' % self.inst_resource['subnet'])

        # query_port_resource
        port_list = PortInstModel.objects.filter(instid=self.nf_inst_id, is_predefined=1)
        for port in port_list:
            port_info = {}
            if not port.resouceid:
                continue
            port_info["vim_id"] = port.vimid
            port_info["tenant_id"] = port.tenant
            port_info["res_id"] = port.resouceid
            self.inst_resource['port'].append(port_info)
        logger.info('[query_port_resource]:ret_networks=%s' % self.inst_resource['port'])

        # query_flavor_resource
        flavor_list = FlavourInstModel.objects.filter(instid=self.nf_inst_id, is_predefined=1)
        for flavor in flavor_list:
            flavor_info = {}
            if not flavor.resouceid:
                continue
            flavor_info["vim_id"] = flavor.vimid
            flavor_info["tenant_id"] = flavor.tenant
            flavor_info["res_id"] = flavor.resouceid
            self.inst_resource['flavor'].append(flavor_info)
        logger.info('[query_flavor_resource]:ret_networks=%s' % self.inst_resource['flavor'])

        # query_vm_resource
        vm_list = VmInstModel.objects.filter(instid=self.nf_inst_id, is_predefined=1)
        for vm in vm_list:
            vm_info = {}
            if not vm.resouceid:
                continue
            vm_info["vim_id"] = vm.vimid
            vm_info["tenant_id"] = vm.tenant
            vm_info["res_id"] = vm.resouceid
            self.inst_resource['vm'].append(vm_info)
        logger.info('[query_vm_resource]:ret_vms=%s' % self.inst_resource['vm'])

    def delete_resource(self):
        adaptor.delete_vim_res(self.inst_resource, self.do_notify_delete)
        logger.error('rollback resource complete')

        StorageInstModel.objects.filter(instid=self.nf_inst_id).delete()
        NetworkInstModel.objects.filter(instid=self.nf_inst_id).delete()
        SubNetworkInstModel.objects.filter(instid=self.nf_inst_id).delete()
        PortInstModel.objects.filter(instid=self.nf_inst_id).delete()
        FlavourInstModel.objects.filter(instid=self.nf_inst_id).delete()
        VmInstModel.objects.filter(instid=self.nf_inst_id).delete()
        logger.error('delete table complete')
        raise NFLCMException("Delete resource failed")

    def do_notify_delete(self, ret):
        logger.error('Deleting [%s] resource' % ret)
        pass

    def lcm_notify(self):
        pass

    # def load_nfvo_config(self):
    #     logger.info("[NF instantiation]get nfvo connection info start")
    #     reg_info = NfvoRegInfoModel.objects.filter(vnfminstid='vnfm111').first()
    #     if reg_info:
    #         self.vnfm_inst_id = reg_info.vnfminstid
    #         self.nfvo_inst_id = reg_info.nfvoid
    #         logger.info("[NF instantiation] Registered nfvo id is [%s]" % self.nfvo_inst_id)
    #     else:
    #         raise NFLCMException("Nfvo was not registered")
    #     logger.info("[NF instantiation]get nfvo connection info end")

    def vnf_term_failed_handle(self, error_msg):
        logger.error('VNF termination failed, detail message: %s' % error_msg)
        NfInstModel.objects.filter(nfinstid=self.nf_inst_id).update(status='failed', lastuptime=now_time())
        JobUtil.add_job_status(self.job_id, 255, error_msg)