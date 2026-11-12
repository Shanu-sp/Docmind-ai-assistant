import os
from io import BytesIO
from unittest.mock import patch
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from documents.models import Document
import docx

class DocumentUploadAndExtractionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser@example.com", email="testuser@example.com", password="password123")
        self.client.force_authenticate(user=self.user)

    @patch("documents.views.LLMService.summarize_document")
    def test_upload_txt_file_and_extract_text(self, mock_summarize):
        mock_summarize.return_value = {
            "executive_summary": ["Test point 1", "Test point 2"],
            "suggested_questions": ["Test question 1?"]
        }
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

    @patch("documents.views.LLMService.summarize_document")
    def test_upload_docx_file_and_extract_text(self, mock_summarize):
        mock_summarize.return_value = {
            "executive_summary": ["Docx summary"],
            "suggested_questions": ["Docx question?"]
        }
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

    def test_document_extractor_page_awareness(self):
        from documents.services.extractor import DocumentExtractor
        import tempfile

        # 1. Test TXT file with virtual pagination
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w', encoding='utf-8') as f:
            # Write 2500 chars across multiple paragraphs to trigger 2 virtual pages (limit 2000)
            f.write("Paragraph 1: " + "A" * 1200 + "\n\nParagraph 2: " + "B" * 1200)
            temp_path = f.name

        try:
            pages = DocumentExtractor.extract_pages(temp_path, 'txt')
            self.assertEqual(len(pages), 2)
            self.assertEqual(pages[0]['page_number'], 1)
            self.assertEqual(pages[1]['page_number'], 2)
            self.assertTrue(pages[0]['text'].startswith("Paragraph 1:"))
            self.assertTrue(pages[1]['text'].startswith("Paragraph 2:"))

            # Test extract_text backward compatibility
            full_text = DocumentExtractor.extract_text(temp_path, 'txt')
            self.assertIn("Paragraph 1:", full_text)
            self.assertIn("Paragraph 2:", full_text)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_document_extractor_error_handling(self):
        from documents.services.extractor import DocumentExtractor
        # Non-existent file
        with self.assertRaises(FileNotFoundError):
            DocumentExtractor.extract_pages("non_existent_file.pdf", "pdf")

        # Unsupported format
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name
        try:
            with self.assertRaises(ValueError):
                DocumentExtractor.extract_pages(temp_path, "xyz")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


