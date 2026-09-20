from django.urls import path

from .views import (
    DeliveryListCreateView,
    FarmerListCreateView,
    PlotListCreateView,
    PlotRiskAttemptsView,
    PriceScheduleView,
    StationDeliveryFeedView,
    WashingStationListCreateView,
)

urlpatterns = [
    path("farmers/", FarmerListCreateView.as_view(), name="farmer-list-create"),
    path("stations/", WashingStationListCreateView.as_view(), name="station-list-create"),
    path("plots/", PlotListCreateView.as_view(), name="plot-list-create"),
    path("plots/<int:plot_id>/risk-checks/", PlotRiskAttemptsView.as_view(), name="plot-risk-checks"),
    path("deliveries/", DeliveryListCreateView.as_view(), name="delivery-list-create"),
    path("stations/<str:station_code>/deliveries/", StationDeliveryFeedView.as_view(), name="station-delivery-feed"),
    path("price-schedule/", PriceScheduleView.as_view(), name="price-schedule"),
]
