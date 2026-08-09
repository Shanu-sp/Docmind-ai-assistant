from rest_framework import serializers
from .models import Document
import os

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'file',
            'file_type',
            'file_size',
            'extracted_text',
            'executive_summary',
            'suggested_questions',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'file_type', 'file_size', 'extracted_text', 'executive_summary', 'suggested_questions', 'created_at', 'updated_at']


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        ext = os.path.splitext(value.name)[1].lower()
        valid_extensions = ['.pdf', '.docx', '.txt']
        if ext not in valid_extensions:
            raise serializers.ValidationError(
                f"Unsupported file type '{ext}'. Allowed extensions are: {', '.join(valid_extensions)}"
            )
        # Limit file size to 25MB for V1
        max_size = 25 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("File size exceeds maximum allowed limit of 25MB.")
        return value
