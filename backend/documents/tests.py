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

    def test_recursive_semantic_chunker(self):
        from documents.services.chunker import RecursiveSemanticChunker

        # Test overlap validation
        with self.assertRaises(ValueError):
            RecursiveSemanticChunker(chunk_size=100, chunk_overlap=150)

        # Test chunking
        chunker = RecursiveSemanticChunker(chunk_size=200, chunk_overlap=50)
        pages = [
            {"page_number": 1, "text": "Sentence A. " * 15},
            {"page_number": 2, "text": "Sentence B. " * 15}
        ]
        chunks = chunker.chunk_pages(pages)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0]['page_number'], 1)
        self.assertEqual(chunks[0]['chunk_index'], 0)
        self.assertEqual(chunks[-1]['page_number'], 2)
        self.assertIn('char_count', chunks[0]['metadata'])

        # Test empty input
        self.assertEqual(chunker.chunk_pages([]), [])
        self.assertEqual(chunker.chunk_pages([{"page_number": 1, "text": ""}]), [])

    @patch("ai.services.embeddings.EmbeddingService.generate_batch_embeddings")
    def test_document_indexer_success_and_idempotency(self, mock_batch_embeddings):
        from documents.services.indexer import DocumentIndexer
        from documents.models import DocumentChunk

        # Mock embedding response with dummy 768-dim float vector
        dummy_vector = [0.01] * 768
        mock_batch_embeddings.side_effect = lambda texts: [dummy_vector for _ in texts]

        # Create a document
        doc = Document.objects.create(
            user=self.user,
            title="Indexer Test Document",
            file_type="txt",
            extracted_text="This is a test paragraph for indexing. " * 10
        )

        indexer = DocumentIndexer()
        success = indexer.index_document(doc)
        self.assertTrue(success)

        doc.refresh_from_db()
        self.assertEqual(doc.indexing_status, "ready")
        self.assertGreater(doc.chunks.count(), 0)

        first_chunk = doc.chunks.first()
        self.assertEqual(first_chunk.user, self.user)
        self.assertEqual(first_chunk.page_number, 1)
        self.assertEqual(len(first_chunk.embedding), 768)

        # Idempotency check: Re-index the document
        initial_chunk_count = doc.chunks.count()
        success_reindex = indexer.index_document(doc)
        self.assertTrue(success_reindex)
        doc.refresh_from_db()
        self.assertEqual(doc.chunks.count(), initial_chunk_count)

    @patch("ai.services.embeddings.EmbeddingService.generate_batch_embeddings")
    def test_document_indexer_edge_cases(self, mock_batch_embeddings):
        from documents.services.indexer import DocumentIndexer

        indexer = DocumentIndexer()

        # 1. Document with no user
        doc_no_user = Document.objects.create(
            user=None,
            title="Orphan Document",
            extracted_text="Some text without owner"
        )
        self.assertFalse(indexer.index_document(doc_no_user))
        doc_no_user.refresh_from_db()
        self.assertEqual(doc_no_user.indexing_status, "failed")

        # 2. Document with no file and no text
        doc_empty = Document.objects.create(
            user=self.user,
            title="Empty Document",
            extracted_text=""
        )
        self.assertFalse(indexer.index_document(doc_empty))
        doc_empty.refresh_from_db()
        self.assertEqual(doc_empty.indexing_status, "failed")

        # 3. Document indexing with API error
        mock_batch_embeddings.side_effect = RuntimeError("Gemini Quota Exceeded")
        doc_err = Document.objects.create(
            user=self.user,
            title="Error Document",
            extracted_text="Some valid content to embed"
        )
        self.assertFalse(indexer.index_document(doc_err))
        doc_err.refresh_from_db()
        self.assertEqual(doc_err.indexing_status, "failed")

    @patch("ai.services.embeddings.EmbeddingService.generate_batch_embeddings")
    def test_index_documents_management_command(self, mock_batch_embeddings):
        from django.core.management import call_command
        from io import StringIO

        dummy_vector = [0.05] * 768
        mock_batch_embeddings.side_effect = lambda texts: [dummy_vector for _ in texts]

        doc = Document.objects.create(
            user=self.user,
            title="Command Test Doc",
            extracted_text="Content for management command testing."
        )

        out = StringIO()
        call_command("index_documents", f"--doc-id={doc.id}", stdout=out)
        output = out.getvalue()

        self.assertIn("READY", output)
        doc.refresh_from_db()
        self.assertEqual(doc.indexing_status, "ready")
        self.assertGreater(doc.chunks.count(), 0)

    @patch("documents.views.LLMService.summarize_document")
    @patch("ai.services.embeddings.EmbeddingService.generate_batch_embeddings")
    def test_reindex_api_action(self, mock_batch_embeddings, mock_summarize):
        dummy_vector = [0.02] * 768
        mock_batch_embeddings.side_effect = lambda texts: [dummy_vector for _ in texts]

        doc = Document.objects.create(
            user=self.user,
            title="API Reindex Doc",
            extracted_text="Content to test reindex action."
        )

        response = self.client.post(f"/api/documents/{doc.id}/reindex/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["indexing_status"], "ready")




