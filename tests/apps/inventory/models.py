import uuid

from django.db import models


class Item(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True)
    attributes = models.JSONField(default=dict)
    thumbnail = models.BinaryField(null=True)
    weight = models.FloatField(null=True)


class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    items = models.ManyToManyField(Item, through="Stock", blank=True)


class Stock(models.Model):
    item = models.OneToOneField(Item, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)


class BaseAsset(models.Model):
    serial = models.CharField(max_length=64)
    purchased_on = models.DateField(null=True)

    class Meta:
        abstract = True


class Vehicle(BaseAsset):
    plate = models.CharField(max_length=16)


class Device(Vehicle):
    ip_address = models.GenericIPAddressField(null=True)
    firmware = models.FileField(upload_to="firmware/", blank=True)


class LegacyTable(models.Model):
    code = models.CharField(max_length=10, primary_key=True, db_column="CODE")
    payload = models.TextField()

    class Meta:
        managed = False
        db_table = "legacy_table"
