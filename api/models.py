from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Farmer(models.Model):
    national_id = models.CharField(max_length=32, unique=True)
    full_name = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name", "id"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.national_id})"


class WashingStation(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    administrative_sector = models.CharField(max_length=120)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Plot(models.Model):
    class RiskStatus(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        CLEAR = "clear", "Clear"
        FLAGGED = "flagged", "Flagged"
        FAILED = "failed", "Failed"

    farmer = models.ForeignKey(Farmer, on_delete=models.PROTECT, related_name="plots")
    plot_code = models.CharField(max_length=40, unique=True)
    administrative_sector = models.CharField(max_length=120)
    washing_station = models.ForeignKey(WashingStation, on_delete=models.PROTECT, related_name="plots")
    area_hectares = models.DecimalField(max_digits=7, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    risk_status = models.CharField(max_length=16, choices=RiskStatus.choices, default=RiskStatus.QUEUED)
    risk_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]


class Delivery(models.Model):
    class Grade(models.TextChoices):
        A = "A", "Grade A"
        B = "B", "Grade B"
        C = "C", "Grade C"

    plot = models.ForeignKey(Plot, on_delete=models.PROTECT, related_name="deliveries")
    washing_station = models.ForeignKey(WashingStation, on_delete=models.PROTECT, related_name="deliveries")
    delivery_date = models.DateField()
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    cherry_grade = models.CharField(max_length=1, choices=Grade.choices)
    recorded_by = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-delivery_date", "-created_at", "id"]


class RiskCheckAttempt(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    plot = models.ForeignKey(Plot, on_delete=models.CASCADE, related_name="risk_check_attempts")
    attempt_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    external_reference = models.CharField(max_length=120, blank=True)
    error_message = models.TextField(blank=True)
    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-queued_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["plot", "attempt_number"], name="unique_plot_risk_attempt")
        ]
