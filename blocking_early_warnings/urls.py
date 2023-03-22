from typing import Type
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.views import View

from blocking_early_warnings.views import HistogramBackendView, HistogramPageView

# Sanity check
if hasattr(settings, "EARLY_WARNINGS_LOGIN_REQUIRED") and not isinstance(settings.EARLY_WARNINGS_LOGIN_REQUIRED, bool):
    raise ValueError("EARLY_WARNINGS_LOGIN_REQUIRED Configuration parameter should be boolean")

# Login require: require login if requested from settings
should_require_login = settings.EARLY_WARNINGS_LOGIN_REQUIRED if hasattr(settings, "EARLY_WARNINGS_LOGIN_REQUIRED") else False

def login_required_check(view : Type[View]):
    if settings.EARLY_WARNINGS_LOGIN_REQUIRED:
        return login_required(view.as_view())

    return view.as_view()

urlpatterns = [
    path("", login_required_check(HistogramPageView)), # Main page displaying histograms
    path("histogram", login_required_check(HistogramBackendView), name="histogram_backend") # Backend to fill histograms view
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
