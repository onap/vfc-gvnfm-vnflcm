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

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


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