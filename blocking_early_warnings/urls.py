from django.urls import path
from blocking_early_warnings.views import HistogramBackendView, HistogramPageView

urlpatterns = [
    path("", HistogramPageView.as_view()), # Main page displaying histograms
    path("histogram", HistogramBackendView.as_view()) # Backend to fill histograms view
]
