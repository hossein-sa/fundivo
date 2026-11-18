"""Invitation APIs: signed-in creators and verified code-bearing recipients."""

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.funds.serializers import MembershipReadSerializer
from apps.funds.views import FundPagination

from .models import Invitation
from .serializers import (
    InvitationAcceptedSerializer,
    InvitationCodeSerializer,
    InvitationCreateSerializer,
    InvitationIssuedSerializer,
    InvitationReadSerializer,
)
from .services import (
    create_invitation,
    manager_fund_or_error,
    respond_to_invitation,
    revoke_invitation,
)


class FundInvitationsView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    pagination_class = FundPagination

    def get_queryset(self):
        fund = manager_fund_or_error(
            fund_id=self.kwargs["fund_id"], actor=self.request.user
        )
        return Invitation.objects.filter(fund=fund).order_by("-created_at", "-id")

    def get_serializer_class(self):
        return InvitationCreateSerializer if self.request.method == "POST" else InvitationReadSerializer

    @extend_schema(tags=["Invitations"], responses=InvitationReadSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Invitations"], request=InvitationCreateSerializer,
        responses={201: InvitationIssuedSerializer},
    )
    def post(self, request, fund_id):
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation, code = create_invitation(
            fund_id=fund_id, actor=request.user,
            phone_number=serializer.validated_data["phone_number"],
        )
        data = InvitationReadSerializer(invitation).data
        data["invitation_code"] = code
        return Response(data, status=status.HTTP_201_CREATED)


class InvitationAcceptView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=["Invitations"], request=InvitationCodeSerializer,
        responses={200: InvitationAcceptedSerializer},
    )
    def post(self, request):
        serializer = InvitationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _, membership = respond_to_invitation(
            actor=request.user, code=serializer.validated_data["code"], accept=True
        )
        return Response({
            "detail": "Invitation accepted.",
            "membership": MembershipReadSerializer(membership).data,
        })


class InvitationRejectView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=["Invitations"], request=InvitationCodeSerializer,
        responses={200: InvitationReadSerializer},
    )
    def post(self, request):
        serializer = InvitationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation, _ = respond_to_invitation(
            actor=request.user, code=serializer.validated_data["code"], accept=False
        )
        return Response(InvitationReadSerializer(invitation).data)


class InvitationRevokeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(tags=["Invitations"], request=None, responses={200: InvitationReadSerializer})
    def post(self, request, fund_id, invitation_id):
        invitation = revoke_invitation(
            actor=request.user, fund_id=fund_id, invitation_id=invitation_id
        )
        return Response(InvitationReadSerializer(invitation).data)
