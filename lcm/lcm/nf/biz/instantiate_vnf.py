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

import json
import logging
import traceback
import uuid
from threading import Thread

from lcm.pub.database.models import NfInstModel, VmInstModel, NetworkInstModel, \
    SubNetworkInstModel, PortInstModel, StorageInstModel, FlavourInstModel, VNFCInstModel
from lcm.pub.exceptions import NFLCMException
from lcm.pub.msapi.gvnfmdriver import apply_grant_to_nfvo, notify_lcm_to_nfvo
from lcm.pub.msapi.sdc_run_catalog import query_vnfpackage_by_id
from lcm.pub.utils.jobutil import JobUtil
from lcm.pub.utils.timeutil import now_time
from lcm.pub.utils.values import ignore_case_get, get_none, get_boolean, get_integer
from lcm.pub.vimapi import adaptor

logger = logging.getLogger(__name__)


class InstantiateVnf(Thread):
    def __init__(self, data, nf_inst_id, job_id):
        super(InstantiateVnf, self).__init__()
        self.data = data
        self.nf_inst_id = nf_inst_id
        self.job_id = job_id
        self.vim_id = ignore_case_get(ignore_case_get(self.data, "additionalParams"), "vimId")

    def run(self):
        try:
            self.inst_pre()
            self.apply_grant()
            self.create_res()
            self.lcm_notify()
            JobUtil.add_job_status(self.job_id, 100, "Instantiate Vnf success.")
        except NFLCMException as e:
            self.vnf_inst_failed_handle(e.message)
        except Exception as e:
            logger.error(e.message)
            logger.error(traceback.format_exc())
            self.vnf_inst_failed_handle('unexpected exception')

    def inst_pre(self):
        vnf_insts = NfInstModel.objects.filter(nfinstid=self.nf_inst_id)
        if not vnf_insts.exists():
            raise NFLCMException('VNF nf_inst_id is not exist.')

        if vnf_insts[0].status != 'NOT_INSTANTIATED':
            raise NFLCMException('VNF instantiationState is not NOT_INSTANTIATED.')

        JobUtil.add_job_status(self.job_id, 5, 'Get packageinfo by vnfd_id')
        self.vnfd_id = vnf_insts[0].vnfdid
        JobUtil.add_job_status(self.job_id, 10, 'Get vnf package info from catalog by csar_id')
        input_parameters = []
        inputs = ignore_case_get(self.data, "additionalParams")
        if inputs:
            if isinstance(inputs, (str, unicode)):
                inputs = json.loads(inputs)
            for key, val in inputs.items():
                input_parameters.append({"key": key, "value": val})
        vnf_package_info = query_vnfpackage_by_id(self.vnfd_id)
        self.vnfd_info = json.loads(ignore_case_get(ignore_case_get(vnf_package_info, "packageInfo"), "vnfdModel"))

        self.update_cps()
        metadata = ignore_case_get(self.vnfd_info, "metadata")
        csar_id = ignore_case_get(metadata, "id")
        version = ignore_case_get(metadata, "vnfdVersion")
        vendor = ignore_case_get(metadata, "vendor")
        netype = ignore_case_get(metadata, "type")
        vnfsoftwareversion = ignore_case_get(metadata, "version")
        NfInstModel.objects.filter(nfinstid=self.nf_inst_id).\
            update(package_id=csar_id,
                   flavour_id=ignore_case_get(self.data, "flavourId"),
                   version=version,
                   vendor=vendor,
                   netype=netype,
                   vnfd_model=self.vnfd_info,
                   status='NOT_INSTANTIATED',
                   vnfdid=self.vnfd_id,
                   localizationLanguage=ignore_case_get(self.data, 'localizationLanguage'),
                   input_params=input_parameters,
                   vnfSoftwareVersion=vnfsoftwareversion,
                   lastuptime=now_time())

        logger.info("VimId = %s" % self.vim_id)
        '''
        is_exist = NfvoRegInfoModel.objects.filter(nfvoid=self.nf_inst_id).exists()
        if not is_exist:
            NfvoRegInfoModel.objects.create(
                nfvoid=self.nf_inst_id,
                vnfminstid=ignore_case_get(self.data, "vnfmId"),
                apiurl=self.vim_id)
        '''
        JobUtil.add_job_status(self.job_id, 15, 'Nf instancing pre-check finish')
        logger.info("Nf instancing pre-check finish")

    def apply_grant(self):
        logger.info('Send resource grand request to nfvo')
        content_args = {
            'vnfInstanceId': self.nf_inst_id,
            'vnfDescriptorId': '',
            'lifecycleOperation': 'Instantiate',
            'jobId': self.job_id,
            'addResource': [],
            'removeResource': [],
            'placementConstraint': [],
            'additionalParam': {}
        }

        vdus = ignore_case_get(self.vnfd_info, "vdus")
        res_index = 1
        for vdu in vdus:
            res_def = {
                'type': 'VDU',
                'resDefId': str(res_index),
                'resDesId': ignore_case_get(vdu, "vdu_id")
            }
            content_args['addResource'].append(res_def)
            res_index += 1

        logger.debug("VnfInst = %s", self.nf_inst_id)
        '''
        vnfmInfo = NfvoRegInfoModel.objects.filter(nfvoid=self.nf_inst_id)
        if len(vnfmInfo) == 0:
            raise NFLCMException('VnfInst(%s) does not exist' % self.nf_inst_id)
        '''
        nfInsts = NfInstModel.objects.filter(nfinstid=self.nf_inst_id)
        content_args['additionalParam']['vnfmid'] = nfInsts[0].vnfminstid
        content_args['additionalParam']['vimid'] = self.vim_id
        logger.info('Grant request data = %s', content_args)

        apply_result = apply_grant_to_nfvo(json.dumps(content_args))
        self.set_location(apply_result)

        logger.info('VnfdInfo = %s' % self.vnfd_info)
        NfInstModel.objects.filter(nfinstid=self.nf_inst_id).update(status='INSTANTIATED', lastuptime=now_time())
        JobUtil.add_job_status(self.job_id, 20, 'Nf instancing apply grant finish')
        logger.info("Nf instancing apply grant finish")

    def create_res(self):
        logger.info("Create resource start")
        adaptor.create_vim_res(self.vnfd_info, self.do_notify)
        JobUtil.add_job_status(self.job_id, 70, '[NF instantiation] create resource finish')
        logger.info("Create resource finish")

    def lcm_notify(self):
        logger.info('Send notify request to nfvo')
        affected_vnfcs = []
        vnfcs = VNFCInstModel.objects.filter(instid=self.nf_inst_id)
        for vnfc in vnfcs:
            vm_resource = {}
            if vnfc.vmid:
                vm = VmInstModel.objects.filter(vmid=vnfc.vmid)
                if vm:
                    vm_resource = {
                        'vimId': vm[0].vimConnectionId,
                        'resourceId': vm[0].resouceid,
                        'resourceProviderId': vm[0].vmname,
                        'vimLevelResourceType': 'vm'
                    }
                    # TODO: is resourceName mapped to resourceProviderId?
            affected_vnfcs.append({
                'id': vnfc.vnfcinstanceid,
                'vduId': vnfc.vduid,
                'changeType': 'ADDED',
                'computeResource': vm_resource
            })
        affected_vls = []
        networks = NetworkInstModel.objects.filter(instid=self.nf_inst_id)
        for network in networks:
            network_resource = {
                'vimConnectionId': network.vimid,
                'resourceId': network.resouceid,
                'resourceProviderId': network.name,
                'vimLevelResourceType': 'network'
            }
            # TODO: is resourceName mapped to resourceProviderId?
            affected_vls.append({
                'id': network.networkid,
                'virtualLinkDescId': network.nodeId,
                'changeType': 'ADDED',
                'networkResource': network_resource
            })
        ext_link_ports = []
        ports = PortInstModel.objects.filter(instid=self.nf_inst_id)
        for port in ports:
            ext_link_ports.append({
                'id': port.portid,  # TODO: port.portid or port.nodeid?
                'resourceHandle': {
                    'vimConnectionId': port.vimid,
                    'resourceId': port.resouceid,
                    'resourceProviderId': port.name,
                    'vimLevelResourceType': 'port'
                },
                # TODO: is resourceName mapped to resourceProviderId?
                'cpInstanceId': port.cpinstanceid
            }),
        affected_vss = []
        vss = StorageInstModel.objects.filter(instid=self.nf_inst_id)
        for vs in vss:
            affected_vss.append({
                'id': vs.storageid,
                'virtualStorageDescId': vs.nodeId,
                'changeType': 'ADDED',
                'storageResource': {
                    'vimConnectionId': vs.vimid,
                    'resourceId': vs.resouceid,
                    'resourceProviderId': vs.name,
                    'vimLevelResourceType': 'volume'
                }
            })
            # TODO: is resourceName mapped to resourceProviderId?
        content_args = {
            "notificationType": 'VnfLcmOperationOccurrenceNotification',
            "notificationStatus": 'RESULT',
            "vnfInstanceId": self.nf_inst_id,
            "operation": 'INSTANTIATE',
            "vnfLcmOpOccId": self.job_id,
            'affectedVnfcs': affected_vnfcs,
            'affectedVirtualLinks': affected_vls,
            'affectedVirtualStorages': affected_vss,
            'chengedExtConnectivity': [{
                'id': None,  # TODO
                'resourceHandle': None,  # TODO
                'extLinkPorts': ext_link_ports
            }]
        }

        '''
        vnfmInfo = NfvoRegInfoModel.objects.filter(nfvoid=self.nf_inst_id)
        if len(vnfmInfo) == 0:
            raise NFLCMException('nf_inst_id(%s) does not exist in NfvoRegInfoModel' % self.nf_inst_id)
        '''
        nfInsts = NfInstModel.objects.filter(nfinstid=self.nf_inst_id)
        content_args['vnfmInstId'] = nfInsts[0].vnfminstid
        logger.info('Notify request data = %s' % content_args)
        resp = notify_lcm_to_nfvo(json.dumps(content_args))
        logger.info('Lcm notify end, response %s' % resp)

    def vnf_inst_failed_handle(self, error_msg):
        logger.error('VNF instantiation failed, detail message: %s' % error_msg)
        NfInstModel.objects.filter(nfinstid=self.nf_inst_id).update(status='NOT_INSTANTIATED', lastuptime=now_time())
        JobUtil.add_job_status(self.job_id, 255, error_msg)

    def do_notify(self, res_type, ret):
        logger.info('Creating [%s] resource' % res_type)
        resource_save_method = globals().get(res_type + '_save')
        resource_save_method(self.job_id, self.nf_inst_id, ret)

    def update_cps(self):
        for extlink in ignore_case_get(self.data, "extVirtualLinks"):
            for ext_cp in ignore_case_get(extlink, "extCps"):
                cpdid = ignore_case_get(ext_cp, "cpdId")
                for cp in ignore_case_get(self.vnfd_info, "cps"):
                    if cpdid == ignore_case_get(cp, "cp_id"):
                        cp["networkId"] = ignore_case_get(extlink, "resourceId")
                        cp["subnetId"] = ignore_case_get(extlink, "resourceSubnetId")
                        break

    def set_location(self, apply_result):
        for resource_type in ['vdus', 'vls']:
            for resource in ignore_case_get(self.vnfd_info, resource_type):
                if "location_info" in resource["properties"]:
                    resource["properties"]["location_info"]["vimid"] = ignore_case_get(apply_result, "vimid")
                    resource["properties"]["location_info"]["tenant"] = ignore_case_get(apply_result, "tenant")
                else:
                    resource["properties"]["location_info"] = {
                        "vimid": ignore_case_get(apply_result, "vimid"),
                        "tenant": ignore_case_get(apply_result, "tenant")}

    '''
    def get_subnet_ids(self, ext_cp):
        subnet_ids = []
        for cp_conf in ignore_case_get(ext_cp, "cpConfig"):
            for cp_protocol in ignore_case_get(ext_cp, "cpProtocolData"):
                ip_over_ethernet = ignore_case_get(cp_protocol, "ipOverEthernet")
                for ip_address in ignore_case_get(ip_over_ethernet, "ipAddresses"):
                    subnet_ids.append(ignore_case_get(ip_address, "subnetId"))
        return subnet_ids
    '''


def volume_save(job_id, nf_inst_id, ret):
    JobUtil.add_job_status(job_id, 25, 'Create vloumns!')
    StorageInstModel.objects.create(
        storageid=str(uuid.uuid4()),
        vimid=ignore_case_get(ret, "vimId"),
        resouceid=ignore_case_get(ret, "id"),
        name=ignore_case_get(ret, "name"),
        tenant=ignore_case_get(ret, "tenantId"),
        create_time=ignore_case_get(ret, "createTime"),
        storagetype=get_none(ignore_case_get(ret, "type")),
        size=ignore_case_get(ret, "size"),
        insttype=0,
        is_predefined=ignore_case_get(ret, "returnCode"),
        nodeId=ignore_case_get(ret, "nodeId"),
        instid=nf_inst_id)


def network_save(job_id, nf_inst_id, ret):
    JobUtil.add_job_status(job_id, 35, 'Create networks!')
    NetworkInstModel.objects.create(
        networkid=str(uuid.uuid4()),
        name=ignore_case_get(ret, "name"),
        vimid=ignore_case_get(ret, "vimId"),
        resouceid=ignore_case_get(ret, "id"),
        tenant=ignore_case_get(ret, "tenantId"),
        segmentid=str(ignore_case_get(ret, "segmentationId")),
        network_type=ignore_case_get(ret, "networkType"),
        physicalNetwork=ignore_case_get(ret, "physicalNetwork"),
        vlantrans=get_boolean(ignore_case_get(ret, "vlanTransparent")),
        is_shared=get_boolean(ignore_case_get(ret, "shared")),
        routerExternal=get_boolean(ignore_case_get(ret, "routerExternal")),
        insttype=0,
        is_predefined=ignore_case_get(ret, "returnCode"),
        nodeId=ignore_case_get(ret, "nodeId"),
        instid=nf_inst_id)


def subnet_save(job_id, nf_inst_id, ret):
    JobUtil.add_job_status(job_id, 40, 'Create subnets!')
    SubNetworkInstModel.objects.create(
        subnetworkid=str(uuid.uuid4()),
        name=ignore_case_get(ret, "name"),
        vimid=ignore_case_get(ret, "vimId"),
        resouceid=ignore_case_get(ret, "id"),
        tenant=ignore_case_get(ret, "tenantId"),
        networkid=ignore_case_get(ret, "networkId"),
        cidr=ignore_case_get(ret, "cidr"),
        ipversion=ignore_case_get(ret, "ipversion"),
        isdhcpenabled=ignore_case_get(ret, "enableDhcp"),
        gatewayip=ignore_case_get(ret, "gatewayIp"),
        dnsNameservers=ignore_case_get(ret, "dnsNameservers"),
        hostRoutes=ignore_case_get(ret, "hostRoutes"),
        allocationPools=ignore_case_get(ret, "allocationPools"),
        insttype=0,
        is_predefined=ignore_case_get(ret, "returnCode"),
        instid=nf_inst_id)


def port_save(job_id, nf_inst_id, ret):
    JobUtil.add_job_status(job_id, 50, 'Create ports!')
    PortInstModel.objects.create(
        portid=str(uuid.uuid4()),
        networkid=ignore_case_get(ret, "networkId"),
        subnetworkid=ignore_case_get(ret, "subnetId"),
        name=ignore_case_get(ret, "name"),
        vimid=ignore_case_get(ret, "vimId"),
        resouceid=ignore_case_get(ret, "id"),
        tenant=ignore_case_get(ret, "tenantId"),
        macaddress=ignore_case_get(ret, "macAddress"),
        ipaddress=ignore_case_get(ret, "ip"),
        typevirtualnic=ignore_case_get(ret, "vnicType"),
        securityGroups=ignore_case_get(ret, "securityGroups"),
        insttype=0,
        is_predefined=ignore_case_get(ret, "returnCode"),
        nodeId=ignore_case_get(ret, "nodeId"),
        instid=nf_inst_id)


def flavor_save(job_id, nf_inst_id, ret):
    JobUtil.add_job_status(job_id, 60, 'Create flavors!')
    FlavourInstModel.objects.create(
        flavourid=str(uuid.uuid4()),
        name=ignore_case_get(ret, "name"),
        vimid=ignore_case_get(ret, "vimId"),
        resouceid=ignore_case_get(ret, "id"),
        tenant=ignore_case_get(ret, "tenantId"),
        vcpu=get_integer(ignore_case_get(ret, "vcpu")),
        memory=get_integer(ignore_case_get(ret, "memory")),
        disk=get_integer(ignore_case_get(ret, "disk")),
        ephemeral=get_integer(ignore_case_get(ret, "ephemeral")),
        swap=get_integer(ignore_case_get(ret, "swap")),
        isPublic=get_boolean(ignore_case_get(ret, "isPublic")),
        extraspecs=ignore_case_get(ret, "extraSpecs"),
        is_predefined=ret.get("returnCode", int(0)),
        instid=nf_inst_id)


def vm_save(job_id, nf_inst_id, ret):
    JobUtil.add_job_status(job_id, 70, 'Create vms!')
    vm_id = str(uuid.uuid4())
    VmInstModel.objects.create(
        vmid=vm_id,
        vmname=ignore_case_get(ret, "name"),
        vimid=ignore_case_get(ret, "vimId"),
        resouceid=ignore_case_get(ret, "id"),
        tenant=ignore_case_get(ret, "tenantId"),
        nic_array=ignore_case_get(ret, "nicArray"),
        metadata=ignore_case_get(ret, "metadata"),
        volume_array=ignore_case_get(ret, "volumeArray"),
        server_group=ignore_case_get(ret, "serverGroup"),
        availability_zone=str(ignore_case_get(ret, "availabilityZone", "undefined")),
        flavor_id=ignore_case_get(ret, "flavorId"),
        security_groups=ignore_case_get(ret, "securityGroups"),
        operationalstate=ignore_case_get(ret, "status"),
        insttype=0,
        is_predefined=ignore_case_get(ret, "returnCode"),
        instid=nf_inst_id)
    VNFCInstModel.objects.create(
        vnfcinstanceid=str(uuid.uuid4()),
        vduid=ignore_case_get(ret, "id"),
        is_predefined=ignore_case_get(ret, "returnCode"),
        instid=nf_inst_id,
        vmid=vm_id)
