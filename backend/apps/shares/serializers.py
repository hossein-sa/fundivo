"""Explicit input and output contracts for draft share allocation."""

from rest_framework import serializers

from .models import Share
from .participation_serializers import ParticipationReadSerializer


class ShareAllocationSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    count = serializers.IntegerField(min_value=1, max_value=20)
    allocation_id = serializers.UUIDField()

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {field: ["This field cannot be written."] for field in sorted(unknown)}
            )
        return super().to_internal_value(data)


class ShareReadSerializer(serializers.ModelSerializer):
    # Legacy membership_id denotes initial allottee; the rows below are authoritative.
    membership_id = serializers.UUIDField(read_only=True)
    participations = ParticipationReadSerializer(many=True, read_only=True)

    class Meta:
        model = Share
        fields = ("id", "number", "membership_id", "participations", "created_at")
        read_only_fields = fields


class ShareBatchSerializer(serializers.Serializer):
    shares = ShareReadSerializer(many=True, read_only=True)
