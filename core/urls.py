from django.urls import path
from . import views
from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView

from .sitemaps import StaticViewSitemap

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    path("", views.HomePage, name = 'home-page'),
    path("upload/", views.UploadFile, name = 'upload'),
    path("enter-password/", views.EnterPassword, name = 'password'),
    path("single-file/", views.SingleFile, name = 'single-file'),
    path("tree/", views.Tree, name = 'tree'),
    path("download-single/", views.Download, name = 'download-single'),
    path("download/", views.DownloadZip, name = 'download'),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
]
