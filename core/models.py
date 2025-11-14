from tortoise import fields
from tortoise.models import Model


class Task(Model):
    id = fields.IntField(pk=True)
    chat_id = fields.CharField(max_length=64, index=True)
    user_id = fields.CharField(max_length=64, index=True)
    text = fields.TextField()
    status = fields.CharField(max_length=16, default="pending", index=True)  # pending, done, expired
    parent_id = fields.IntField(null=True, default=None)
    ai_generated = fields.BooleanField(default=False)  # Добавлено для совместимости
    expired_at = fields.DatetimeField(null=True, default=None)  # Когда задача стала просроченной
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
    total_completed_tasks = fields.IntField(default=0)  # Общий счетчик выполненных задач (не сбрасывается)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_settings"


class Achievement(Model):
    id = fields.IntField(pk=True)
    chat_id = fields.CharField(max_length=64, index=True)
    milestone = fields.IntField(index=True)
    title = fields.CharField(max_length=200)
    emoji = fields.CharField(max_length=10, default="🏆")
    unlocked_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "achievements"
        unique_together = [("chat_id", "milestone")]


class MotivationSettings(Model):
    id = fields.IntField(pk=True)
    chat_id = fields.CharField(max_length=64, unique=True, index=True)
    style = fields.CharField(max_length=20, default="friendly")
    enabled = fields.BooleanField(default=True)
    last_reminder = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "motivation_settings"
