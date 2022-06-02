from django.urls import path

from exapp import views

app_name = 'excelset'

urlpatterns = [
    path('ex_down/', views.exdown, name='ex_down'),
    path('', views.ex_setting, name='exseton'),
]