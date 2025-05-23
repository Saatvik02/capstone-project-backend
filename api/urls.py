from django.urls import path
from . import views

urlpatterns = [
  path("", views.home_view, name="home"),
  path("test/", views.test_view, name="test"),
  path("fetch-indices/", views.fetch_s2_and_s1_indices, name="fetch-indices"),
  path("mock-results/", views.generate_mock_results, name="mock-results")
]
