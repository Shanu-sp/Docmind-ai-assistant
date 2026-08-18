from django.db import models
from django.contrib.auth.models import User
from documents.models import Document

class ChatSession(models.Model):
    """
    Represents a conversation session linked to an uploaded Document and owned by a User.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        null=True,
        blank=True
    )
    document = models.ForeignKey(
        Document, 
        on_delete=models.CASCADE, 
        related_name='chat_sessions',
        null=True,
        blank=True
    )
    title = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} (Session {self.id})"


class ChatMessage(models.Model):
    """
    Represents an individual user message or AI assistant response within a ChatSession.
    """
    SENDER_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
    )

    session = models.ForeignKey(
        ChatSession, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.sender.upper()}] {self.content[:30]}..."
