# Changelog

All notable changes to Fundivo will be documented here.

This project follows the Keep a Changelog format
and plans to use Semantic Versioning for releases.

## [Unreleased]

### Added
- OTP login-ticket exchange, JWT access/refresh rotation, refresh-token blacklist logout, and read-only profile API.
- Redis-backed OTP verification endpoints, rate limiting, and one-time login tickets (JWT exchange pending).
- Initial monorepo structure.
- Django 5.2 LTS backend with Python 3.12.
- PostgreSQL 17 development database using Docker Compose.
- Environment-based configuration and secret management.
- Separate development and production settings.
- Django REST Framework integration.
- OpenAPI schema, Swagger UI, and ReDoc.
- Initial infrastructure tests using pytest.
- Ruff code quality checks.
- GitHub Actions backend CI workflow.
- Initial architecture documentation.
- Preliminary database design and ERD.
- Initial business rules documentation.

### Fixed
- Django management script executable permissions
  for Linux-based CI environments.

## Releases

No official versions have been released yet.
