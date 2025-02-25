from django.db import models

class CropData(models.Model):
    region_name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    band_values = models.JSONField()  # Stores extracted band values as JSON
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.region_name} - {self.timestamp}"
