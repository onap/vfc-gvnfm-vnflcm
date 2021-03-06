# Copyright (c) 2019, CMCC Technologies Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from rest_framework import serializers


class linkSerializer(serializers.Serializer):
    href = serializers.CharField(
        help_text="URI of the referenced resource.",
        required=True,
        allow_null=False,
        allow_blank=False)


class LinkSerializer(serializers.Serializer):
    self = linkSerializer(
        help_text="URI of this resource.",
        required=True,
        allow_null=False)
