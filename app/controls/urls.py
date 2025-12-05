"""
URL mappings for the controls app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from controls import views

app_name = "controls"

router = DefaultRouter()
router.register("controls", views.ControlViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
