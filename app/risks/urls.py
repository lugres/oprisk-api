"""
URL mappings for the risks app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from risks import views

app_name = "risks"

router = DefaultRouter()
router.register("risks", views.RiskViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
