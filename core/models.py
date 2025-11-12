from tortoise import fields
from tortoise.models import Model


class Task(Model):
    id = fields.IntField(pk=True)
    chat_id = fields.CharField(max_length=64, index=True)
    user_id = fields.CharField(max_length=64, index=True)
    text = fields.TextField()
    status = fields.CharField(max_length=16, default="new", index=True)
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
    enabled = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "schedules"


