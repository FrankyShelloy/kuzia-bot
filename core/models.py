# core/models.py
from tortoise import Model, fields

class Task(Model):
    id = fields.IntField(pk=True)
    chat_id = fields.CharField(max_length=50)
    user_id = fields.CharField(max_length=50)
    text = fields.TextField()
    status = fields.CharField(max_length=20, default="pending")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

class Schedule(Model):
    id = fields.IntField(pk=True)
    chat_id = fields.CharField(max_length=50)
    user_id = fields.CharField(max_length=50)
    text = fields.TextField()
    day_of_week = fields.IntField()
    time = fields.CharField(max_length=5)
    enabled = fields.BooleanField(default=True)