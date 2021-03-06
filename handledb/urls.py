"""handledb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from dbmanageapp import views

urlpatterns = [
    path('', views.dbmainpage, name='home'),
    path('adminchangi/', admin.site.urls),
    path('accounts/', include('accountapp.urls')),
    path('dbmanager/', include('dbmanageapp.urls')),
    path('super_adm/', include('allmanageapp.urls')),
    path('aboutex/', include('exapp.urls')),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)