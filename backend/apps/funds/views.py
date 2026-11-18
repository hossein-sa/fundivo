"""Fund HTTP endpoints. Access always starts from member-scoped querysets."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Fund, FundMembership
from .serializers import (
    FundCreateSerializer,
    FundEditSerializer,
    FundReadSerializer,
    MembershipReadSerializer,
)
from .services import create_fund, edit_fund_draft


class FundPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def visible_funds(user):
    return Fund.objects.filter(
        memberships__user=user, memberships__is_active=True
    ).distinct()


def visible_fund_or_404(user, fund_id):
    return get_object_or_404(visible_funds(user), pk=fund_id)


class FundListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    pagination_class = FundPagination

    def get_queryset(self):
        return visible_funds(self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return FundCreateSerializer
        return FundReadSerializer

    @extend_schema(tags=["Funds"], responses=FundReadSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["Funds"], request=FundCreateSerializer, responses={201: FundReadSerializer})
    def post(self, request, *args, **kwargs):
        serializer = FundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fund = create_fund(creator=request.user, **serializer.validated_data)
        return Response(
            FundReadSerializer(fund, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class FundDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "patch", "head", "options")

    @extend_schema(tags=["Funds"], responses=FundReadSerializer)
    def get(self, request, fund_id):
        fund = visible_fund_or_404(request.user, fund_id)
        return Response(FundReadSerializer(fund, context={"request": request}).data)

    @extend_schema(tags=["Funds"], request=FundEditSerializer, responses=FundReadSerializer)
    def patch(self, request, fund_id):
        fund = visible_fund_or_404(request.user, fund_id)
        serializer = FundEditSerializer(fund, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = edit_fund_draft(
            fund_id=fund.pk, actor=request.user, changes=serializer.validated_data
        )
        return Response(FundReadSerializer(updated, context={"request": request}).data)


class MyFundMembershipView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(tags=["Memberships"], responses=MembershipReadSerializer)
    def get(self, request, fund_id):
        visible_fund_or_404(request.user, fund_id)
        membership = get_object_or_404(
            FundMembership, fund_id=fund_id, user=request.user, is_active=True
        )
        return Response(MembershipReadSerializer(membership).data)


class FundMembershipListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = MembershipReadSerializer
    pagination_class = FundPagination

    def get_queryset(self):
        fund = visible_fund_or_404(self.request.user, self.kwargs["fund_id"])
        if not FundMembership.objects.filter(
            fund=fund,
            user=self.request.user,
            role=FundMembership.Role.MANAGER,
            is_active=True,
        ).exists():
            raise PermissionDenied("Only the fund manager can list memberships.")
        return FundMembership.objects.filter(fund=fund).order_by("joined_at", "id")

    @extend_schema(tags=["Memberships"], responses=MembershipReadSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
