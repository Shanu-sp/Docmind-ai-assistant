from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    """
    Represents an uploaded document (PDF, DOCX, TXT) and its extracted metadata & insights.
    Belongs to a specific User for multi-tenant data isolation.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents', null=True, blank=True)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    file_type = models.CharField(max_length=50, blank=True)  # pdf, docx, txt
    file_size = models.IntegerField(default=0)  # in bytes
    extracted_text = models.TextField(blank=True, default="")
    executive_summary = models.JSONField(default=list, blank=True)  # List of 3 summary bullet points
    suggested_questions = models.JSONField(default=list, blank=True)  # List of dynamic follow-up questions
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
