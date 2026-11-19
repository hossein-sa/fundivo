"""Fund-scoped manager-only draft share split proposals."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.funds.views import visible_fund_or_404

from .participation_serializers import (
    ParticipationBatchSerializer,
    ParticipationProposalSerializer,
    ParticipationReadSerializer,
)
from .participation_services import propose_shared_participation
from .views import visible_shares


class ShareParticipationsView(APIView):
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "post", "head", "options")

    @extend_schema(tags=["Shares"], responses=ParticipationReadSerializer(many=True))
    def get(self, request, fund_id, share_id):
        share = get_object_or_404(
            visible_shares(user=request.user, fund_id=fund_id), pk=share_id
        )
        queryset = share.participations.order_by("membership_id")
        return Response(ParticipationReadSerializer(queryset, many=True).data)

    @extend_schema(
        tags=["Shares"],
        request=ParticipationProposalSerializer,
        responses={201: ParticipationBatchSerializer, 200: ParticipationBatchSerializer},
        description="Manager-only one-time draft split. Does not create installments or payment liabilities.",
    )
    def post(self, request, fund_id, share_id):
        # Do not reveal a private fund's existence to non-members.
        visible_fund_or_404(request.user, fund_id)
        serializer = ParticipationProposalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rows, created = propose_shared_participation(
            fund_id=fund_id,
            share_id=share_id,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(
            {"participants": ParticipationReadSerializer(rows, many=True).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
