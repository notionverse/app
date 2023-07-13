from django.urls import path
from .views import *

urlpatterns = [
    path('send-email', SendTodaysListingsView.as_view()),
]