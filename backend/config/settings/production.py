"""
Production settings for Fundivo.
"""

from .base import *

DEBUG = False

API_DOCS_ENABLED = False

# HTTPS security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

OTP_DELIVERY_BACKEND = "disabled"
