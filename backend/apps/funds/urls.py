"""Fund API routes (api/v1 prefix is supplied by config.urls)."""

from django.urls import path

from apps.invitations.views import FundInvitationsView, InvitationRevokeView
from apps.shares.participation_views import ShareParticipationsView
from apps.shares.views import FundShareDetailView, FundSharesView

from .guest_views import FundGuestMembershipCreateView
from .sponsorship_views import (
    GuestSponsorshipAttachView,
    GuestSponsorshipListCreateView,
    SponsorshipAcceptView,
    SponsorshipApproveView,
    SponsorshipRejectView,
)
from .views import (
    FundDetailView,
    FundListCreateView,
    FundMembershipListView,
    MyFundMembershipView,
)

urlpatterns = [
    path(
        "<uuid:fund_id>/guest-sponsorships/",
        GuestSponsorshipListCreateView.as_view(),
        name="fund-guest-sponsorship-list",
    ),
    path(
        "<uuid:fund_id>/guest-memberships/<uuid:guest_id>/sponsorship/",
        GuestSponsorshipAttachView.as_view(),
        name="fund-guest-sponsorship-attach",
    ),
    path(
        "<uuid:fund_id>/guest-sponsorships/<uuid:sponsorship_id>/accept/",
        SponsorshipAcceptView.as_view(),
        name="fund-guest-sponsorship-accept",
    ),
    path(
        "<uuid:fund_id>/guest-sponsorships/<uuid:sponsorship_id>/approve/",
        SponsorshipApproveView.as_view(),
        name="fund-guest-sponsorship-approve",
    ),
    path(
        "<uuid:fund_id>/guest-sponsorships/<uuid:sponsorship_id>/reject/",
        SponsorshipRejectView.as_view(),
        name="fund-guest-sponsorship-reject",
    ),
    path(
        "<uuid:fund_id>/shares/<uuid:share_id>/participations/",
        ShareParticipationsView.as_view(),
        name="fund-share-participations",
    ),
    path(
        "<uuid:fund_id>/guest-memberships/",
        FundGuestMembershipCreateView.as_view(),
        name="fund-guest-membership-create",
    ),
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
