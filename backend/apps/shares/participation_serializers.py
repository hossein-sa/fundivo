"""Draft, non-financial share participation proposals and read-only contracts."""

from rest_framework import serializers

from .models import ShareParticipation


class ParticipationInputSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    units = serializers.IntegerField(min_value=1, max_value=12)

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {key: ["Unknown field."] for key in sorted(unknown)}
            )
        return super().to_internal_value(data)


class ParticipationProposalSerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    participants = ParticipationInputSerializer(many=True, allow_empty=False)

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {key: ["Unknown field."] for key in sorted(unknown)}
            )
        return super().to_internal_value(data)

    def validate_participants(self, participants):
        if not 2 <= len(participants) <= 12:
            raise serializers.ValidationError("A shared share needs 2 to 12 participants.")
        ids = [row["membership_id"] for row in participants]
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("Each membership may appear only once.")
        if sum(row["units"] for row in participants) != 12:
            raise serializers.ValidationError("Participation units must total exactly 12.")
        return participants


class ParticipationReadSerializer(serializers.ModelSerializer):
    membership_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ShareParticipation
        fields = ("id", "membership_id", "units", "created_at")
        read_only_fields = fields


class ParticipationBatchSerializer(serializers.Serializer):
    participants = ParticipationReadSerializer(many=True, read_only=True)
