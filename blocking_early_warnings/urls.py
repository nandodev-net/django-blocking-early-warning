from django.urls import path
from blocking_early_warnings.views import HistogramBackendView, HistogramPageView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", HistogramPageView.as_view()), # Main page displaying histograms
    path("histogram", HistogramBackendView.as_view(), name="histogram_backend") # Backend to fill histograms view
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
