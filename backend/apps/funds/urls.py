"""Fund API routes (api/v1 prefix is supplied by config.urls)."""

from django.urls import path

from apps.invitations.views import FundInvitationsView, InvitationRevokeView
from apps.shares.views import FundShareDetailView, FundSharesView

from .views import (
    FundDetailView,
    FundListCreateView,
    FundMembershipListView,
    MyFundMembershipView,
)

urlpatterns = [
    path("<uuid:fund_id>/shares/", FundSharesView.as_view(), name="fund-share-list"),
    path(
        "<uuid:fund_id>/shares/<uuid:share_id>/",
        FundShareDetailView.as_view(),
        name="fund-share-detail",
    ),
    path(
        "<uuid:fund_id>/invitations/",
        FundInvitationsView.as_view(),
        name="fund-invitation-list",
    ),
    path(
        "<uuid:fund_id>/invitations/<uuid:invitation_id>/revoke/",
        InvitationRevokeView.as_view(),
        name="fund-invitation-revoke",
    ),
    path("", FundListCreateView.as_view(), name="fund-list"),
    path("<uuid:fund_id>/", FundDetailView.as_view(), name="fund-detail"),
    path(
        "<uuid:fund_id>/membership/",
        MyFundMembershipView.as_view(),
        name="fund-membership-me",
    ),
    path(
        "<uuid:fund_id>/memberships/",
        FundMembershipListView.as_view(),
        name="fund-membership-list",
    ),
]
