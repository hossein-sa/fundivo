"""Recipient actions live under /api/v1/invitations/."""

from django.urls import path

from .views import InvitationAcceptView, InvitationRejectView

urlpatterns = [
    path("accept/", InvitationAcceptView.as_view(), name="invitation-accept"),
    path("reject/", InvitationRejectView.as_view(), name="invitation-reject"),
]
