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
import uuid

from lcm.pub.config.config import REPORT_TO_AAI
from lcm.pub.database.models import NfInstModel
from lcm.pub.exceptions import NFLCMException
from lcm.pub.msapi.aai import create_vnf_aai
from lcm.pub.msapi.catalog import query_rawdata_from_catalog
from lcm.pub.msapi.gvnfmdriver import get_packageinfo_by_vnfdid
from lcm.pub.utils import toscautil
from lcm.pub.utils.timeutil import now_time
from lcm.pub.utils.values import ignore_case_get

logger = logging.getLogger(__name__)


class CreateVnf:
    def __init__(self, data):
        self.data = data
        self.vnfd_id = ignore_case_get(self.data, "vnfdId")
        self.vnf_instance_mame = ignore_case_get(self.data, "vnfInstanceName")
        self.description = ignore_case_get(self.data, "vnfInstanceDescription")
        self.vnfd = None
        self.package_info = ''
        self.package_id = ''
        self.csar_id = ''

    def do_biz(self):
        self.nf_inst_id = str(uuid.uuid4())
        try:
            self.check_vnf_name_valid()
            self.get_vnfd_info()
            self.save_info_to_db()
            if REPORT_TO_AAI:
                self.create_vnf_in_aai()
        except NFLCMException as e:
            logger.debug('Create VNF instance[%s] to AAI failed' % self.nf_inst_id)
        except:
            NfInstModel.objects.create(nfinstid=self.nf_inst_id,
                                       nf_name=self.vnf_instance_mame,
                                       package_id='',
                                       version='',
                                       vendor='',
                                       netype='',
                                       vnfd_model='',
                                       status='NOT_INSTANTIATED',
                                       nf_desc=self.description,
                                       vnfdid=self.vnfd_id,
                                       vnfSoftwareVersion='',
                                       create_time=now_time())

        vnf_inst = NfInstModel.objects.get(nfinstid=self.nf_inst_id)
        logger.debug('id is [%s],name is [%s],vnfd_id is [%s],vnfd_model is [%s],'
                     'description is [%s],create_time is [%s]' %
                     (vnf_inst.nfinstid, vnf_inst.nf_name, vnf_inst.vnfdid,
                      vnf_inst.vnfd_model, vnf_inst.nf_desc, vnf_inst.create_time))
        return self.nf_inst_id

    def check_vnf_name_valid(self):
        logger.debug("CreateVnfIdentifier--CreateVnf::> %s" % self.data)
        is_exist = NfInstModel.objects.filter(nf_name=self.vnf_instance_mame).exists()
        logger.debug("check_inst_name_exist::is_exist=%s" % is_exist)
        if is_exist:
            raise NFLCMException('VNF is already exist.')

    def get_vnfd_info(self):
        self.nf_inst_id = str(uuid.uuid4())
        self.package_info = get_packageinfo_by_vnfdid(self.vnfd_id)
        for val in ignore_case_get(self.package_info, "csars"):
            if self.vnfd_id == ignore_case_get(val, "vnfdId"):
                self.package_id = ignore_case_get(val, "csarId")
                break

        raw_data = query_rawdata_from_catalog(self.package_id)
        self.vnfd = toscautil.convert_vnfd_model(raw_data["rawData"])  # convert to inner json
        self.vnfd = json.JSONDecoder().decode(self.vnfd)

    def save_info_to_db(self):
        metadata = ignore_case_get(self.vnfd, "metadata")
        version = ignore_case_get(metadata, "vnfd_version")
        vendor = ignore_case_get(metadata, "vendor")
        netype = ignore_case_get(metadata, "vnf_type")
        vnfsoftwareversion = ignore_case_get(metadata, "version")
        vnfd_model = self.vnfd
        NfInstModel.objects.create(nfinstid=self.nf_inst_id,
                                   nf_name=self.vnf_instance_mame,
                                   package_id=self.package_id,
                                   version=version,
                                   vendor=vendor,
                                   netype=netype,
                                   vnfd_model=vnfd_model,
                                   status='NOT_INSTANTIATED',
                                   nf_desc=self.description,
                                   vnfdid=self.vnfd_id,
                                   vnfSoftwareVersion=vnfsoftwareversion,
                                   create_time=now_time())

    def create_vnf_in_aai(self):
        logger.debug("CreateVnf::create_vnf_in_aai::report vnf instance[%s] to aai." % self.nf_inst_id)
        data = {
            "vnf-id": self.nf_inst_id,
            "vnf-name": self.vnf_instance_mame,
            "vnf-type": "INFRA",
            "in-maint": True,
            "is-closed-loop-disabled": False
        }
        resp_data, resp_status = create_vnf_aai(self.nf_inst_id, data)
        if resp_data:
            logger.debug("Fail to create vnf instance[%s] to aai, resp_status: [%s]." % (self.nf_inst_id, resp_status))
        else:
            logger.debug("Success to create vnf instance[%s] to aai, resp_status: [%s]." % (self.nf_inst_id, resp_status))
