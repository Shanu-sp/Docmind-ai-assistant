from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField, HnswIndex

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
    
    # RAG Status Tracking
    indexing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('indexing', 'Indexing'),
            ('ready', 'Ready'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class DocumentChunk(models.Model):
    """
    Stores individual semantic text fragments with 768-dimensional embeddings
    and page-level provenance.
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_chunks')
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    
    # 768d Matryoshka embedding from gemini-embedding-001
    embedding = VectorField(dimensions=768)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['document', 'chunk_index']
        indexes = [
            models.Index(fields=['user', 'document']),
            HnswIndex(
                name='chunk_vector_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops']
            ),
        ]

    def __str__(self):
        return f"{self.document.title} [Chunk {self.chunk_index} | Page {self.page_number}]"
