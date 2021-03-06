# Copyright 2018 ZTE Corporation.
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

from rest_framework import serializers

from .resource_handle import ResourceHandleSerializer
from .ext_link_port_info import ExtlinkPortInfoSerializer


class ExtVirtualLinkInfoSerializer(serializers.Serializer):
    id = serializers.CharField(
        help_text="Identifier of the external VL and the related external VL information instance. \
        The identifier is assigned by the NFV-MANO entity that manages this VL instance.",
        required=True,
        max_length=255,
        allow_null=False,
        allow_blank=False)
    resourceHandle = ResourceHandleSerializer(
        help_text="Reference to the resource realizing this VL.",
        required=True,
        allow_null=False)
    extlinkPorts = ExtlinkPortInfoSerializer(
        help_text="Link ports of this VL.",
        many=True,
        required=False,
        allow_null=True)
