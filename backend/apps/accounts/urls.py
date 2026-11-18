"""Authentication endpoint URLs (version prefix supplied in config.urls)."""

from django.urls import path

from .auth_views import (
    LoginTicketExchangeView,
    SessionLogoutView,
    SessionRefreshView,
    UserMeView,
)
from .views import OTPRequestView, OTPVerifyView

urlpatterns = [
    path("otp/request/", OTPRequestView.as_view(), name="otp-request"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),
    path("token/exchange/", LoginTicketExchangeView.as_view(), name="auth-token-exchange"),
    path("token/refresh/", SessionRefreshView.as_view(), name="auth-token-refresh"),
    path("logout/", SessionLogoutView.as_view(), name="auth-token-logout"),
    path("me/", UserMeView.as_view(), name="users-me"),
]
