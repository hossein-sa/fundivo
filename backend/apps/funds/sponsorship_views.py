"""Scoped request/consent/approval endpoints for draft guest sponsorship."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FundMembership, GuestSponsorship
from .sponsorship_serializers import (
    GuestSponsorshipReadSerializer,
    SponsorshipAttachSerializer,
    SponsorshipCreateSerializer,
)
from .sponsorship_services import (
    attach_existing_guest,
    create_sponsorship_request,
    decide_sponsorship,
)
from .views import FundPagination, visible_fund_or_404


class GuestSponsorshipListCreateView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = GuestSponsorshipReadSerializer
    pagination_class = FundPagination

    def get_queryset(self):
        fund = visible_fund_or_404(self.request.user, self.kwargs["fund_id"])
        membership = get_object_or_404(
            FundMembership, fund=fund, user=self.request.user, is_active=True
        )
        queryset = GuestSponsorship.objects.filter(fund=fund).select_related("guest_membership")
        if membership.role != FundMembership.Role.MANAGER:
            queryset = queryset.filter(sponsor_membership=membership)
        return queryset.order_by("-created_at", "-pk")

    @extend_schema(tags=["Guest Sponsorships"], responses=GuestSponsorshipReadSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Guest Sponsorships"], request=SponsorshipCreateSerializer,
        responses={201: GuestSponsorshipReadSerializer, 200: GuestSponsorshipReadSerializer},
        description="Draft guest request. Members explicitly accept their own responsibility; nominated sponsors must accept separately.",
    )
    def post(self, request, fund_id):
        visible_fund_or_404(request.user, fund_id)
        serializer = SponsorshipCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj, created = create_sponsorship_request(
            fund_id=fund_id, actor=request.user, **serializer.validated_data
        )
        return Response(
            GuestSponsorshipReadSerializer(obj).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class GuestSponsorshipAttachView(APIView):
    permission_classes = (IsAuthenticated,)
    http_method_names = ("post", "options")

    @extend_schema(
        tags=["Guest Sponsorships"], request=SponsorshipAttachSerializer,
        responses={201: GuestSponsorshipReadSerializer, 200: GuestSponsorshipReadSerializer},
        description="Manager-only: propose a sponsor for a pre-existing guest; preserve old shares.",
    )
    def post(self, request, fund_id, guest_id):
        visible_fund_or_404(request.user, fund_id)
        serializer = SponsorshipAttachSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj, created = attach_existing_guest(
            fund_id=fund_id, guest_id=guest_id, actor=request.user,
            **serializer.validated_data,
        )
        return Response(
            GuestSponsorshipReadSerializer(obj).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class _SponsorshipDecisionView(APIView):
    permission_classes = (IsAuthenticated,)
    http_method_names = ("post", "options")
    decision = None

    def post(self, request, fund_id, sponsorship_id):
        visible_fund_or_404(request.user, fund_id)
        obj = decide_sponsorship(
            fund_id=fund_id, sponsorship_id=sponsorship_id,
            actor=request.user, decision=self.decision,
        )
        return Response(GuestSponsorshipReadSerializer(obj).data)


class SponsorshipAcceptView(_SponsorshipDecisionView):
    decision = "accept"

    @extend_schema(tags=["Guest Sponsorships"], request=None, responses=GuestSponsorshipReadSerializer)
    def post(self, request, fund_id, sponsorship_id):
        return super().post(request, fund_id, sponsorship_id)


class SponsorshipApproveView(_SponsorshipDecisionView):
    decision = "approve"

    @extend_schema(tags=["Guest Sponsorships"], request=None, responses=GuestSponsorshipReadSerializer)
    def post(self, request, fund_id, sponsorship_id):
        return super().post(request, fund_id, sponsorship_id)


class SponsorshipRejectView(_SponsorshipDecisionView):
    decision = "reject"

    @extend_schema(tags=["Guest Sponsorships"], request=None, responses=GuestSponsorshipReadSerializer)
    def post(self, request, fund_id, sponsorship_id):
        return super().post(request, fund_id, sponsorship_id)
