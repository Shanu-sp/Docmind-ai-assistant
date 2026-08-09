import os
from io import BytesIO
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from documents.models import Document
import docx

class DocumentUploadAndExtractionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_upload_txt_file_and_extract_text(self):
        content = b"Hello, this is a test TXT document for DocMind."
        uploaded_file = SimpleUploadedFile("sample.txt", content, content_type="text/plain")

        response = self.client.post("/api/documents/", {"file": uploaded_file}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["title"], "sample.txt")
        self.assertEqual(data["file_type"], "txt")
        self.assertEqual(data["extracted_text"], "Hello, this is a test TXT document for DocMind.")

        # Verify DB entry
        doc = Document.objects.get(id=data["id"])
        self.assertEqual(doc.extracted_text, "Hello, this is a test TXT document for DocMind.")

    def test_upload_docx_file_and_extract_text(self):
        doc = docx.Document()
        doc.add_paragraph("DocMind DOCX Extraction Test Paragraph.")
        docx_io = BytesIO()
        doc.save(docx_io)
        docx_io.seek(0)

        uploaded_file = SimpleUploadedFile(
            "sample.docx",
            docx_io.read(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        response = self.client.post("/api/documents/", {"file": uploaded_file}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["file_type"], "docx")
        self.assertIn("DocMind DOCX Extraction Test Paragraph.", data["extracted_text"])

    def test_invalid_file_extension(self):
        content = b"Binary data"
        uploaded_file = SimpleUploadedFile("sample.exe", content, content_type="application/octet-stream")

        response = self.client.post("/api/documents/", {"file": uploaded_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

