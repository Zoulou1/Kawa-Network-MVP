from datetime import date
from decimal import Decimal

from rest_framework import serializers

from .models import Delivery, Farmer, Plot, RiskCheckAttempt, WashingStation


class FarmerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farmer
        fields = ["id", "national_id", "full_name", "phone_number", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_national_id(self, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError("national_id must contain at least 5 characters.")
        return value

    def validate_full_name(self, value: str) -> str:
        value = value.strip()
        if len(value.split()) < 2:
            raise serializers.ValidationError("full_name must include a first name and a family name.")
        return value

    def validate_phone_number(self, value: str) -> str:
        value = value.strip()
        if len(value) < 9 or not any(character.isdigit() for character in value):
            raise serializers.ValidationError("phone_number must contain a valid contact number.")
        return value


class WashingStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WashingStation
        fields = ["id", "code", "name", "administrative_sector"]
        read_only_fields = ["id"]


class RiskCheckAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskCheckAttempt
        fields = ["id", "attempt_number", "status", "external_reference", "error_message", "queued_at", "started_at", "finished_at"]
        read_only_fields = fields


class PlotSerializer(serializers.ModelSerializer):
    farmer_name = serializers.CharField(source="farmer.full_name", read_only=True)
    washing_station_code = serializers.CharField(source="washing_station.code", read_only=True)
    latest_risk_attempt = serializers.SerializerMethodField()

    class Meta:
        model = Plot
        fields = [
            "id", "plot_code", "farmer", "farmer_name", "administrative_sector",
            "washing_station", "washing_station_code", "area_hectares", "latitude",
            "longitude", "risk_status", "risk_checked_at", "latest_risk_attempt", "created_at",
        ]
        read_only_fields = ["id", "risk_status", "risk_checked_at", "latest_risk_attempt", "created_at"]

    def get_latest_risk_attempt(self, obj: Plot):
        attempt = obj.risk_check_attempts.first()
        return RiskCheckAttemptSerializer(attempt).data if attempt else None

    def validate_administrative_sector(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("administrative_sector is required.")
        return value

    def validate(self, attrs):
        latitude = attrs.get("latitude")
        longitude = attrs.get("longitude")
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError("latitude and longitude must be provided together.")
        if latitude is not None and not (-90 <= latitude <= 90):
            raise serializers.ValidationError({"latitude": "latitude must be between -90 and 90."})
        if longitude is not None and not (-180 <= longitude <= 180):
            raise serializers.ValidationError({"longitude": "longitude must be between -180 and 180."})
        return attrs


class DeliverySerializer(serializers.ModelSerializer):
    farmer_name = serializers.CharField(source="plot.farmer.full_name", read_only=True)
    plot_code = serializers.CharField(source="plot.plot_code", read_only=True)
    station_code = serializers.CharField(source="washing_station.code", read_only=True)

    class Meta:
        model = Delivery
        fields = [
            "id", "plot", "plot_code", "farmer_name", "washing_station", "station_code",
            "delivery_date", "weight_kg", "cherry_grade", "recorded_by", "created_at",
        ]
        read_only_fields = ["id", "plot_code", "farmer_name", "station_code", "created_at"]

    def validate_delivery_date(self, value: date) -> date:
        if value > date.today():
            raise serializers.ValidationError("delivery_date cannot be in the future.")
        return value

    def validate_weight_kg(self, value: Decimal) -> Decimal:
        if value <= 0:
            raise serializers.ValidationError("weight_kg must be greater than zero.")
        return value

    def validate(self, attrs):
        plot = attrs.get("plot")
        station = attrs.get("washing_station")
        if plot and station and plot.washing_station_id != station.id:
            raise serializers.ValidationError({
                "washing_station": "The delivery station must match the plot's registered washing station."
            })
        if plot and plot.risk_status in {Plot.RiskStatus.FLAGGED}:
            self.context.setdefault("warnings", []).append("This plot is flagged by the risk workflow; delivery is accepted for review.")
        return attrs
