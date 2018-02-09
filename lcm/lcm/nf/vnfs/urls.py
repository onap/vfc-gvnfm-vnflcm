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

from django.conf.urls import url

from lcm.nf.vnfs.views import InstantiateVnf, TerminateVnf, DeleteVnfAndQueryVnf, CreateVnfAndQueryVnfs

urlpatterns = [
    url(r'^api/vnflcm/v1/vnf_instances$', CreateVnfAndQueryVnfs.as_view()),
    url(r'^api/vnflcm/v1/vnf_instances/(?P<instanceid>[0-9a-zA-Z_-]+)/instantiate$', InstantiateVnf.as_view()),
    url(r'^api/vnflcm/v1/vnf_instances/(?P<instanceid>[0-9a-zA-Z_-]+)$', DeleteVnfAndQueryVnf.as_view()),
    url(r'^api/vnflcm/v1/vnf_instances/(?P<instanceid>[0-9a-zA-Z_-]+)/terminate$', TerminateVnf.as_view()),
]
