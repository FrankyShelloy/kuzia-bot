from tortoise import fields
from tortoise.models import Model


class Task(Model):
    id = fields.IntField(pk=True)
    chat_id = fields.CharField(max_length=64, index=True)
    user_id = fields.CharField(max_length=64, index=True)
    text = fields.TextField()
    status = fields.CharField(max_length=16, default="new", index=True)
    parent_id = fields.IntField(null=True, default=None)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "tasks"


class Schedule(Model):
    id = fields.IntField(pk=True)
    chat_id = fields.CharField(max_length=64, index=True)
    user_id = fields.CharField(max_length=64, index=True)
    text = fields.TextField()
    day_of_week = fields.IntField()
    time = fields.CharField(max_length=5)
    timezone = fields.CharField(max_length=64, default="UTC")
    reminder_minutes = fields.IntField(default=0)  # Напомнить за N минут до события (0 = выключено)
    enabled = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "schedules"


class UserSettings(Model):
    id = fields.IntField(pk=True)
    user_id = fields.CharField(max_length=64, index=True, unique=True)
    chat_id = fields.CharField(max_length=64, index=True)
    timezone = fields.CharField(max_length=64, default="UTC")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_settings"

