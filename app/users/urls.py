"""
URL mappings for the user API.
"""

from django.urls import path

from users import views

app_name = "users"

urlpatterns = [
    path("create/", views.CreateUserView.as_view(), name="create"),
]
