from django.urls import path

from exapp import views

app_name = 'excelset'

urlpatterns = [
    path('ex_down/', views.exdown, name='ex_down'),
    path('', views.ex_setting, name='exseton'),
    path('set_memo/', views.memo_set, name='set_memo'),
]