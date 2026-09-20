import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Delivery, Farmer, Plot, RiskCheckAttempt, WashingStation
from .serializers import (
    DeliverySerializer,
    FarmerSerializer,
    PlotSerializer,
    RiskCheckAttemptSerializer,
    WashingStationSerializer,
)

logger = logging.getLogger(__name__)


class FarmerListCreateView(generics.ListCreateAPIView):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer


class WashingStationListCreateView(generics.ListCreateAPIView):
    queryset = WashingStation.objects.all()
    serializer_class = WashingStationSerializer


class PlotListCreateView(generics.ListCreateAPIView):
    queryset = Plot.objects.select_related("farmer", "washing_station").prefetch_related("risk_check_attempts")
    serializer_class = PlotSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plot = serializer.save(risk_status=Plot.RiskStatus.QUEUED)
        attempt = RiskCheckAttempt.objects.create(plot=plot, attempt_number=1)
        logger.info("risk_check_queued plot=%s attempt=%s", plot.plot_code, attempt.id)
        headers = self.get_success_headers(serializer.data)
        response_data = self.get_serializer(plot).data
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)


class DeliveryListCreateView(generics.ListCreateAPIView):
    queryset = Delivery.objects.select_related("plot__farmer", "washing_station")
    serializer_class = DeliverySerializer


class StationDeliveryFeedView(generics.ListAPIView):
    serializer_class = DeliverySerializer

    def get_queryset(self):
        station = get_object_or_404(WashingStation, code=self.kwargs["station_code"])
        return Delivery.objects.filter(washing_station=station).select_related("plot__farmer", "washing_station")


class PlotRiskAttemptsView(generics.ListAPIView):
    serializer_class = RiskCheckAttemptSerializer

    def get_queryset(self):
        return RiskCheckAttempt.objects.filter(plot_id=self.kwargs["plot_id"])


class PriceScheduleView(APIView):
    def get(self, request):
        return Response({
            "season": "2026",
            "currency": "USD",
            "prices": settings.PRICE_SCHEDULE,
            "note": "Prices are configuration for this MVP and are not yet editable through the API.",
        })
