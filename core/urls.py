from django.urls import path
from . import views

urlpatterns = [
    path("", views.HomePage, name = 'home-page'),
    path("upload/", views.UploadFile, name = 'upload'),
    path("enter-password/", views.EnterPassword, name = 'password'),
    path("single-file/", views.SingleFile, name = 'single-file'),
    path("tree/", views.Tree, name = 'tree'),
    path("download-single/", views.Download, name = 'download-single'),
    path("download/", views.DownloadZip, name = 'download')
]