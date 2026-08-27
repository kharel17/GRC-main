"""
Document Ingestion Worker Pipeline — Orchestrates extract -> chunk -> embed -> status update.
"""
import asyncio
import logging
from uuid import UUID
from app.database import SessionLocal
from app.ingestion.extractor import extract_pages_from_bytes
from app.ingestion.chunker import chunk_document
from app.ingestion.job_queue import update_job_progress, IngestionStep
from app.services.ai_service import ai_service, _run_document_analysis_async

logger = logging.getLogger("grc.ingestion.pipeline")

async def process_document_job(
    analysis_id: UUID,
    file_bytes: bytes,
    filename: str,
    organization_id: UUID,
    source_type: str = "evidence",
) -> None:
    """
    Background job function: extracts text, builds chunks, embeds content, and updates DB status.
    Called via background worker or FastAPI BackgroundTasks.
    """
    logger.info(f"Starting ingestion pipeline for document {filename} (analysis_id={analysis_id}, source_type={source_type})")

    async with SessionLocal() as db:
        try:
            # 1. Extraction phase
            await update_job_progress(db, analysis_id, IngestionStep.extracting, progress=20)
            pages = await asyncio.to_thread(extract_pages_from_bytes, file_bytes, filename)

            if not pages:
                raise ValueError("Could not extract any readable text or content from the document.")

            full_text = "\n\n".join(p.raw_text for p in pages)

            # 2. Chunking phase
            await update_job_progress(db, analysis_id, IngestionStep.chunking, progress=50)
            chunks = await asyncio.to_thread(
                chunk_document,
                pages=pages,
                document_id=str(analysis_id),
                org_id=str(organization_id),
                target_token_size=400,
                overlap_ratio=0.15,
                source_type=source_type,
            )

            # 3. Embedding phase — embed chunks and upsert into Qdrant grc_doc_chunks collection
            await update_job_progress(db, analysis_id, IngestionStep.embedding, progress=70, chunk_count=len(chunks))

            from app.services.vector_store import vector_store
            if chunks and not vector_store.is_ready:
                raise RuntimeError(
                    "Vector indexing failed: Qdrant vector store is not ready. "
                    "Document cannot be marked ready until chunks are indexed."
                )

            chunks_indexed = 0
            if chunks:
                try:
                    chunk_texts = [c.text for c in chunks]
                    embeddings = await asyncio.to_thread(ai_service._embed_texts, chunk_texts)
                    await vector_store.upsert_chunks(chunks, embeddings)
                    chunks_indexed = len(chunks)
                    logger.info(f"Vector Store: Indexed {chunks_indexed} chunks for document {analysis_id} (source_type={source_type})")
                except Exception as vs_err:
                    # Vector store failure is non-fatal — pipeline continues, control mapping still works
                    logger.warning(f"Vector Store: Chunk upsert failed ({vs_err}); failing ingestion job")
                    raise RuntimeError(f"Vector indexing failed: {vs_err}") from vs_err
            elif not vector_store.is_ready:
                logger.info("Vector Store: Not ready — skipping vector indexing (Qdrant not configured)")


            # 4. Final analysis & completion phase — async Qdrant path
            analysis_data = await _run_document_analysis_async(full_text)
            
            # Enrich analysis_data with chunk metadata
            analysis_data["chunk_summary"] = {
                "total_pages": len(pages),
                "total_chunks": len(chunks),
                "chunks_indexed": chunks_indexed,
                "avg_tokens_per_chunk": round(sum(c.token_count for c in chunks) / max(len(chunks), 1)),
                "source_type": source_type,
            }

            # Update DocumentAnalysis record in DB
            from sqlalchemy import select
            from app import models
            result = await db.execute(
                select(models.DocumentAnalysis).where(models.DocumentAnalysis.id == analysis_id)
            )
            doc_analysis = result.scalars().first()
            if doc_analysis:
                doc_analysis.extracted_text = full_text
                doc_analysis.source_type = source_type
                doc_analysis.document_category = analysis_data.get("document_category", "general")
                doc_analysis.implemented_controls = analysis_data.get("implemented_controls", [])
                doc_analysis.missing_controls = analysis_data.get("missing_controls", [])
                doc_analysis.security_practices = analysis_data.get("security_practices", [])
                if source_type == "internal_policy":
                    policy_mappings = ai_service.map_policy_chunks_to_controls(
                        chunks=chunks,
                        embeddings=embeddings if chunks else None,
                        threshold=settings.POLICY_MATCH_THRESHOLD,
                    )
                    doc_analysis.policy_control_mappings = policy_mappings

                    # Dispatch self-serve review notification to Org Admins/Managers
                    try:
                        from app.utils.notifications import notify
                        mgr_res = await db.execute(
                            select(models.User).where(
                                models.User.organization_id == organization_id,
                                models.User.role.in_([models.UserRole.admin, models.UserRole.manager]),
                                models.User.is_active == True,
                            )
                        )
                        managers = mgr_res.scalars().all()
                        for mgr in managers:
                            await notify(
                                db=db,
                                user_id=mgr.id,
                                title="Policy Crosswalk Review Required",
                                message=f"AI suggested {len(policy_mappings)} control mappings for '{filename}'. Please review and confirm.",
                                entity_type="document_analysis",
                                entity_id=str(analysis_id),
                                link_url=f"/policies/review/{analysis_id}",
                                notification_type="policy_crosswalk_review",
                            )
                    except Exception as notif_err:
                        logger.warning(f"Failed to dispatch policy review notifications ({notif_err})")

            await update_job_progress(db, analysis_id, IngestionStep.ready, progress=100, chunk_count=len(chunks))
            logger.info(f"Ingestion pipeline completed successfully for {filename} ({len(chunks)} chunks created, source_type={source_type})")

        except Exception as e:
            logger.error(f"Ingestion pipeline failed for document {filename}: {e}", exc_info=True)
            await update_job_progress(
                db,
                analysis_id,
                IngestionStep.failed,
                progress=0,
                error=str(e),
            )
