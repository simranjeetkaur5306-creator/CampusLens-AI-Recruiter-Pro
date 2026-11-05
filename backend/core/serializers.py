from rest_framework import serializers


class StrictWritableFieldsMixin:
    """Rejects any submitted key that is read-only or does not exist (400)."""

    def to_internal_value(self, data):
        writable = {name for name, field in self.fields.items() if not field.read_only}
        invalid = [key for key in data if key not in writable]
        if invalid:
            raise serializers.ValidationError(
                {key: ["This field is read-only or does not exist."] for key in invalid}
            )
        return super().to_internal_value(data)