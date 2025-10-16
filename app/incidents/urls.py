"""
URL mappings for the incidents app.
"""

from django.urls import path, include

from rest_framework.routers import DefaultRouter

from incidents import views

router = DefaultRouter()
router.register("incidents", views.IncidentsViewSet)

app_name = "incidents"

urlpatterns = [
    path("", include(router.urls)),
]
