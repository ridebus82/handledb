from django.urls import path

from accountapp import views

urlpatterns = [
    path('', views.chk_ttt),
]
