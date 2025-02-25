from django.urls import path
from . import views

urlpatterns = [
  path("", views.home_view, name="home"),
  path("test/", views.test_view, name="test"),
  path("fetch-bands/", views.fetch_band_values, name="fetch-band-values"),
]
