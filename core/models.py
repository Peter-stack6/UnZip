from django.db import models

class TempUpload(models.Model):
    file = models.FileField(upload_to = 'files/')
