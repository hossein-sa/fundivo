"""Input contract for creating a guest membership (not a user account)."""

from rest_framework import serializers


class GuestMembershipCreateSerializer(serializers.Serializer):
    guest_name = serializers.CharField(max_length=120, allow_blank=False, trim_whitespace=True)

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {key: ["This field cannot be written."] for key in sorted(unknown)}
            )
        return super().to_internal_value(data)
