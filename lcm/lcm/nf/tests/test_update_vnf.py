# Copyright 2019 ZTE Corporation.
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

import mock
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from lcm.pub.utils import restcall
from lcm.pub.database.models import NfInstModel
from lcm.pub.utils.jobutil import JobUtil
from lcm.nf.biz.update_vnf import UpdateVnf


class TestNFUpdate(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.upd_data = {
            "vnfInstanceName": "vnf new name",
            "vnfInstanceDescription": "new description"
        }

    def tearDown(self):
        pass

    def test_update_vnf_not_exist(self):
        response = self.client.patch("/api/vnflcm/v1/vnf_instances/1111",
                                     data=self.upd_data,
                                     format='json')
        self.failUnlessEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    @mock.patch.object(restcall, 'call_req')
    def test_update_vnf_success(self, mock_call_req):
        instanceid = "12"
        NfInstModel(nfinstid=instanceid,
                    nf_name='VNF1',
                    nf_desc="VNF DESC",
                    vnfdid="1",
                    netype="XGW",
                    vendor="ZTE",
                    vnfSoftwareVersion="V1",
                    version="V1",
                    package_id="2",
                    status='INSTANTIATED').save()
        mock_call_req.return_value = [0, {}, status.HTTP_202_ACCEPTED]
        job_id = JobUtil.create_job('NF', 'UPDATETEST', instanceid)
        UpdateVnf(self.upd_data, instanceid, job_id).run()
        name = NfInstModel.objects.filter(nfinstid=instanceid).get().nf_name
        self.failUnlessEqual("vnf new name", name)