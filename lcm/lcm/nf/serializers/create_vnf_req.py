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


class CreateVnfReqSerializer(serializers.Serializer):
    vnfdId = serializers.CharField(
        help_text="Identifier that identifies the VNFD which defines the VNF instance to be created.",
        max_length=255,
        required=True,
        allow_null=True)
    vnfInstanceName = serializers.CharField(
        help_text="Human-readable name of the VNF instance to be created.",
        max_length=255,
        required=False,
        allow_null=False)
    vnfInstanceDescription = serializers.CharField(
        help_text="Human-readable description of the VNF instance to be created.",
        max_length=255,
        required=False,
        allow_null=True,
        allow_blank=True)
    vnfmInstId = serializers.CharField(
        help_text="VNFM instance ID passed from nfvo.",
        max_length=255,
        required=False,
        allow_null=True,
        allow_blank=True)
