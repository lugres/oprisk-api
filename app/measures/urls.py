"""
URL mappings for the measures app.
"""

from django.urls import path, include

from rest_framework.routers import DefaultRouter

from measures import views

router = DefaultRouter()
router.register("measures", views.MeasureViewSet)

app_name = "measures"

urlpatterns = [
    path("", include(router.urls)),
]
