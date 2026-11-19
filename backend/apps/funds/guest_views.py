"""Fund manager can record a guest without assigning any login credentials."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .guest_serializers import GuestMembershipCreateSerializer
from .guest_services import create_guest_membership
from .serializers import MembershipReadSerializer
from .views import visible_fund_or_404


class FundGuestMembershipCreateView(APIView):
    permission_classes = (IsAuthenticated,)
    http_method_names = ("post", "options")

    @extend_schema(
        tags=["Memberships"],
        request=GuestMembershipCreateSerializer,
        responses={201: MembershipReadSerializer},
        description=(
            "Manager-only. Create a guest placeholder in a draft fund. "
            "Does not create a User or confer login access."
        ),
    )
    def post(self, request, fund_id):
        # A non-member gets 404; a member without manager permissions gets 403.
        visible_fund_or_404(request.user, fund_id)
        serializer = GuestMembershipCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = create_guest_membership(
            fund_id=fund_id, actor=request.user, **serializer.validated_data
        )
        return Response(
            MembershipReadSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )
