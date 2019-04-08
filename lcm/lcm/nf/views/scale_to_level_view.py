# Copyright (C) 2019 ZTE. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
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

import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from lcm.nf.serializers.scale_vnf_to_level_request_serializer import ScaleVnfToLevelRequestSerializer
from lcm.nf.serializers.response import ProblemDetailsSerializer
from lcm.pub.exceptions import NFLCMException
from lcm.pub.exceptions import NFLCMExceptionNotFound
from lcm.pub.exceptions import NFLCMExceptionConflict
from lcm.pub.utils.jobutil import JobUtil
from lcm.pub.database.models import NfInstModel
from lcm.nf.const import VNF_STATUS
from lcm.nf.biz.scale_vnf_to_level import ScaleVnfToLevel
from .common import view_safe_call_with_log

logger = logging.getLogger(__name__)


class ScaleVnfToLevelView(APIView):
    @swagger_auto_schema(
        request_body=ScaleVnfToLevelRequestSerializer(),
        responses={
            status.HTTP_202_ACCEPTED: "Success",
            status.HTTP_404_NOT_FOUND: ProblemDetailsSerializer(),
            status.HTTP_409_CONFLICT: ProblemDetailsSerializer(),
            status.HTTP_500_INTERNAL_SERVER_ERROR: "Internal error"
        }
    )
    @view_safe_call_with_log(logger=logger)
    def post(self, request, instanceid):
        logger.debug("ScaleVnfToLevel--post::> %s" % request.data)

        scale_to_level_serializer = ScaleVnfToLevelRequestSerializer(data=request.data)
        if not scale_to_level_serializer.is_valid():
            raise NFLCMException(scale_to_level_serializer.errors)

        job_id = JobUtil.create_job('NF', 'SCALE_TO_LEVEL', instanceid)
        JobUtil.add_job_status(job_id, 0, "SCALE_VNF_TO_LEVEL_READY")
        self.scale_pre_check(instanceid, job_id)

        ScaleVnfToLevel(scale_to_level_serializer.data, instanceid, job_id).start()

        response = Response(data={"jobId": job_id},
                            status=status.HTTP_202_ACCEPTED)
        return response

    def scale_pre_check(self, nf_inst_id, job_id):
        vnf_insts = NfInstModel.objects.filter(nfinstid=nf_inst_id)
        if not vnf_insts.exists():
            raise NFLCMExceptionNotFound("VNF nf_inst_id does not exist.")

        if vnf_insts[0].status != 'INSTANTIATED':
            raise NFLCMExceptionConflict("VNF instantiationState is not INSTANTIATED.")

        vnf_insts.update(status=VNF_STATUS.SCALING)
        JobUtil.add_job_status(job_id, 15, 'Nf scaling to level pre-check finish')
        logger.info("Nf scaling to level pre-check finish")