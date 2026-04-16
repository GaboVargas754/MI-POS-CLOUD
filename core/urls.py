from django.urls import path
from . import views

urlpatterns = [
    path('', views.portal_principal, name='portal_principal'),
]
