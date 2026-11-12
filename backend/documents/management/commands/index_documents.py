import time
from django.core.management.base import BaseCommand
from django.db.models import Count
from documents.models import Document
from documents.services.indexer import DocumentIndexer


class Command(BaseCommand):
    help = "Indexes documents into semantic vector chunks for RAG retrieval."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Force re-indexing of ALL documents, even those already marked ready.",
        )
        parser.add_argument(
            "--doc-id",
            type=int,
            help="Index a single document specified by its primary key ID.",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="Index all documents belonging to a specific user ID.",
        )
        parser.add_argument(
            "--failed-only",
            action="store_true",
            help="Retry indexing only for documents marked as 'failed'.",
        )

    def handle(self, *args, **options):
        start_time = time.time()
        self.stdout.write(self.style.MIGRATE_HEADING("=== DocMind RAG Document Indexer ==="))

        doc_id = options.get("doc-id")
        user_id = options.get("user-id")
        reindex_all = options.get("all")
        failed_only = options.get("failed-only")

        # 1. Build Queryset based on options
        qs = Document.objects.select_related("user").annotate(chunks_count=Count("chunks"))

        if doc_id:
            qs = qs.filter(id=doc_id)
            if not qs.exists():
                self.stderr.write(self.style.ERROR(f"No document found with ID {doc_id}."))
                return
        elif user_id:
            qs = qs.filter(user_id=user_id)
        elif failed_only:
            qs = qs.filter(indexing_status="failed")
        elif not reindex_all:
            # Default: index any document not ready or with zero chunks
            qs = qs.filter(indexing_status__in=["pending", "failed"]) | qs.filter(chunks_count=0)
            qs = qs.distinct()

        documents = list(qs.order_by("id"))
        total = len(documents)

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No documents require indexing at this time."))
            return

        self.stdout.write(f"Found {total} document(s) to index.\n")

        # 2. Run Indexing
        indexer = DocumentIndexer()
        success_count = 0
        failure_count = 0
        total_chunks = 0

        for idx, doc in enumerate(documents, start=1):
            user_display = doc.user.username if doc.user else "NO USER"
            self.stdout.write(
                f"[{idx}/{total}] Doc ID {doc.id}: '{doc.title}' (User: {user_display})...",
                ending=" "
            )

            try:
                success = indexer.index_document(doc)
                doc.refresh_from_db()

                if success:
                    chunk_count = doc.chunks.count()
                    total_chunks += chunk_count
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"READY ({chunk_count} chunk{'s' if chunk_count != 1 else ''})")
                    )
                else:
                    failure_count += 1
                    self.stdout.write(self.style.ERROR(f"FAILED (status: {doc.indexing_status})"))
            except Exception as e:
                failure_count += 1
                self.stdout.write(self.style.ERROR(f"ERROR: {str(e)}"))

        # 3. Final Summary Report
        elapsed = time.time() - start_time
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.MIGRATE_HEADING("Indexing Summary:"))
        self.stdout.write(f"  • Total Processed: {total}")
        self.stdout.write(self.style.SUCCESS(f"  • Succeeded:       {success_count}"))
        if failure_count > 0:
            self.stdout.write(self.style.ERROR(f"  • Failed:          {failure_count}"))
        else:
            self.stdout.write(f"  • Failed:          0")
        self.stdout.write(f"  • Chunks Created:  {total_chunks}")
        self.stdout.write(f"  • Time Elapsed:    {elapsed:.2f}s")
        self.stdout.write("=" * 50 + "\n")
