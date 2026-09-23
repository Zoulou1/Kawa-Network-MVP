from datetime import date, timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase

from .models import Delivery, Farmer, Plot, RiskCheckAttempt, WashingStation


class KawaApiTests(APITestCase):
    def setUp(self):
        self.station = WashingStation.objects.create(
            code="NYA-01", name="Emmanuel's Station", administrative_sector="Mbuye"
        )
        self.farmer_payload = {
            "national_id": "RW1234567",
            "full_name": "Aline Mukamana",
            "phone_number": "+250788123456",
        }

    def test_farmer_registration_returns_created_farmer(self):
        response = self.client.post("/api/farmers/", self.farmer_payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["national_id"], "RW1234567")

    def test_farmer_validation_has_structured_error(self):
        response = self.client.post("/api/farmers/", {"full_name": "Aline", "phone_number": "x"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertIn("national_id", response.data["error"]["fields"])

    def make_plot(self):
        farmer = Farmer.objects.create(**self.farmer_payload)
        response = self.client.post("/api/plots/", {
            "plot_code": "PLOT-001",
            "farmer": farmer.id,
            "administrative_sector": "Mbuye",
            "washing_station": self.station.id,
            "area_hectares": "1.25",
            "latitude": -2.45,
            "longitude": 29.65,
        }, format="json")
        return farmer, response

    def test_plot_creation_queues_recorded_risk_attempt_without_calling_registry(self):
        with patch("api.views.logger.info") as log:
            _, response = self.make_plot()
        self.assertEqual(response.status_code, 201)
        plot = Plot.objects.get(plot_code="PLOT-001")
        attempt = RiskCheckAttempt.objects.get(plot=plot)
        self.assertEqual(plot.risk_status, Plot.RiskStatus.QUEUED)
        self.assertEqual(attempt.status, RiskCheckAttempt.Status.QUEUED)
        log.assert_called()

    def test_plot_rejects_only_one_coordinate(self):
        farmer = Farmer.objects.create(**self.farmer_payload)
        response = self.client.post("/api/plots/", {
            "plot_code": "PLOT-002", "farmer": farmer.id,
            "administrative_sector": "Mbuye", "washing_station": self.station.id,
            "area_hectares": "1.25", "latitude": -2.45,
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("latitude and longitude", str(response.data))

    def test_delivery_requires_plot_station_match(self):
        _, response = self.make_plot()
        plot = Plot.objects.get(plot_code="PLOT-001")
        other = WashingStation.objects.create(code="NYA-02", name="Other Station", administrative_sector="Gasaka")
        delivery_response = self.client.post("/api/deliveries/", {
            "plot": plot.id, "washing_station": other.id, "delivery_date": str(date.today()),
            "weight_kg": "12.5", "cherry_grade": "A",
        }, format="json")
        self.assertEqual(delivery_response.status_code, 400)
        self.assertIn("washing_station", delivery_response.data["error"]["fields"])

    def test_delivery_and_paginated_station_feed(self):
        _, response = self.make_plot()
        plot = Plot.objects.get(plot_code="PLOT-001")
        delivery_response = self.client.post("/api/deliveries/", {
            "plot": plot.id, "washing_station": self.station.id, "delivery_date": str(date.today()),
            "weight_kg": "12.5", "cherry_grade": "A", "recorded_by": "Emmanuel",
        }, format="json")
        self.assertEqual(delivery_response.status_code, 201)
        feed = self.client.get("/api/stations/NYA-01/deliveries/?page=1&page_size=1")
        self.assertEqual(feed.status_code, 200)
        self.assertEqual(feed.data["count"], 1)
        self.assertEqual(feed.data["results"][0]["plot_code"], "PLOT-001")

    def test_future_delivery_is_rejected(self):
        _, response = self.make_plot()
        plot = Plot.objects.get(plot_code="PLOT-001")
        future = date.today() + timedelta(days=1)
        result = self.client.post("/api/deliveries/", {
            "plot": plot.id, "washing_station": self.station.id, "delivery_date": str(future),
            "weight_kg": "12.5", "cherry_grade": "A",
        }, format="json")
        self.assertEqual(result.status_code, 400)
        self.assertIn("delivery_date", result.data["error"]["fields"])

    def test_price_schedule_exists(self):
        response = self.client.get("/api/price-schedule/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["prices"]), 3)


class RiskWorkerTests(TestCase):
    def test_worker_records_successful_attempt(self):
        station = WashingStation.objects.create(code="NYA-01", name="Station", administrative_sector="Mbuye")
        farmer = Farmer.objects.create(national_id="RW7654321", full_name="Jean Bosco", phone_number="+250788000000")
        plot = Plot.objects.create(
            farmer=farmer, plot_code="WORKER-001", administrative_sector="Mbuye",
            washing_station=station, area_hectares="2.00",
        )
        attempt = RiskCheckAttempt.objects.create(plot=plot, attempt_number=1)
        call_command("process_risk_checks", once=True)
        attempt.refresh_from_db()
        plot.refresh_from_db()
        self.assertEqual(attempt.status, RiskCheckAttempt.Status.SUCCEEDED)
        self.assertEqual(plot.risk_status, Plot.RiskStatus.CLEAR)
        self.assertTrue(attempt.external_reference)
