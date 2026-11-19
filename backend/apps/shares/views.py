"""Fund-scoped shares: managers see all; members see only their own."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.funds.models import FundMembership, GuestSponsorship
from apps.funds.views import FundPagination, visible_fund_or_404

from .models import Share
from .serializers import (
    ShareAllocationSerializer,
    ShareBatchSerializer,
    ShareReadSerializer,
)
from .services import allocate_shares


def visible_shares(*, user, fund_id):
    fund = visible_fund_or_404(user, fund_id)
    membership = get_object_or_404(
        FundMembership.objects.filter(fund=fund, user=user, is_active=True)
    )
    queryset = Share.objects.filter(fund=fund)
    if membership.role != FundMembership.Role.MANAGER:
        queryset = queryset.filter(
            Q(participations__membership=membership)
            | Q(
                participations__membership__guest_sponsorship__sponsor_membership=membership,
                participations__membership__guest_sponsorship__status=GuestSponsorship.Status.ACTIVE,
            )
        ).distinct()
    return queryset


class FundSharesView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ShareReadSerializer
    pagination_class = FundPagination

    def get_queryset(self):
        return visible_shares(user=self.request.user, fund_id=self.kwargs["fund_id"])

    @extend_schema(tags=["Shares"], responses=ShareReadSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Shares"],
        request=ShareAllocationSerializer,
        responses={201: ShareBatchSerializer, 200: ShareBatchSerializer},
    )
    def post(self, request, fund_id):
        # Hide existence of funds from non-members before checking allocation rights.
        visible_fund_or_404(request.user, fund_id)
        serializer = ShareAllocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shares, created = allocate_shares(
            fund_id=fund_id,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(
            {"shares": ShareReadSerializer(shares, many=True).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class FundShareDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "head", "options")

    @extend_schema(tags=["Shares"], responses=ShareReadSerializer)
    def get(self, request, fund_id, share_id):
        share = get_object_or_404(
            visible_shares(user=request.user, fund_id=fund_id), pk=share_id
        )
        return Response(ShareReadSerializer(share).data)
