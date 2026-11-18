"""Fund API routes (api/v1 prefix is supplied by config.urls)."""

from django.urls import path

from .views import (
    FundDetailView,
    FundListCreateView,
    FundMembershipListView,
    MyFundMembershipView,
)

urlpatterns = [
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
