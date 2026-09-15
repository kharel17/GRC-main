"""
Vector Store Service — Qdrant wrapper for split collections (grc_doc_chunks and grc_iso_controls).
"""
import logging
import uuid
from typing import List, Optional, Dict, Any, Union
import numpy as np

from qdrant_client import AsyncQdrantClient, models as qmodels
from qdrant_client.models import PointStruct
from app.config import settings
from app.ingestion.chunker import Chunk

logger = logging.getLogger("grc.vector_store")

VECTOR_SIZE = 384  # all-MiniLM-L6-v2 dimension

class VectorStoreService:
    """
    Manages Qdrant vector storage for split collections:
    1. grc_doc_chunks — Document chunks scoped by org_id and document_id.
    2. grc_iso_controls — Static ISO 27001 control embeddings.
    """

    def __init__(self):
        self._client: Optional[AsyncQdrantClient] = None
        self._is_ready = False

    @property
    def client(self) -> Optional[AsyncQdrantClient]:
        return self._client

    @property
    def collection_name(self) -> str:
        return settings.QDRANT_COLLECTION_DOC_CHUNKS

    def initialize(self) -> None:
        """Initialize Qdrant client connection."""
        try:
            url = settings.QDRANT_URL
            api_key = settings.QDRANT_API_KEY
            self._client = AsyncQdrantClient(url=url, api_key=api_key, timeout=10)
            logger.info(f"Vector Store: Client configured for {url}")
        except Exception as e:
            logger.warning(f"Vector Store: Init failed ({e}). Vector storage disabled.")
            self._client = None
            self._is_ready = False

    @property
    def is_ready(self) -> bool:
        return self._is_ready and self._client is not None

    async def initialize_collections(self) -> bool:
        """
        Ensure split collections exist in Qdrant and payload indexes are created.
        Called on server startup.
        """
        if not self._client:
            self.initialize()
        if not self._client:
            return False

        try:
            # 1. Check & Create grc_doc_chunks collection
            collections = await self._client.get_collections()
            collection_names = [c.name for c in collections.collections]

            doc_coll = settings.QDRANT_COLLECTION_DOC_CHUNKS
            if doc_coll not in collection_names:
                await self._client.create_collection(
                    collection_name=doc_coll,
                    vectors_config=qmodels.VectorParams(
                        size=VECTOR_SIZE,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
                logger.info(f"Vector Store: Created collection '{doc_coll}'")

                # Payload index for org_id scoping
                await self._client.create_payload_index(
                    collection_name=doc_coll,
                    field_name="org_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
                # Payload index for document_id filtering
                await self._client.create_payload_index(
                    collection_name=doc_coll,
                    field_name="document_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )

            # 2. Check & Create grc_iso_controls collection
            ctrl_coll = settings.QDRANT_COLLECTION_ISO_CONTROLS
            if ctrl_coll not in collection_names:
                await self._client.create_collection(
                    collection_name=ctrl_coll,
                    vectors_config=qmodels.VectorParams(
                        size=VECTOR_SIZE,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
                logger.info(f"Vector Store: Created collection '{ctrl_coll}'")

            self._is_ready = True
            logger.info("Vector Store: All split collections initialized [OK]")
            return True

        except Exception as e:
            logger.warning(f"Vector Store: Failed to initialize collections ({e}). Qdrant unreachable.")
            self._is_ready = False
            return False

    async def upsert_chunks(
        self,
        chunks: List[Any],
        embeddings: Any,
        batch_size: int = 100,
    ) -> bool:
        """
        Upsert document chunks into grc_doc_chunks collection in batches.
        Prevents payload limits and memory spikes for large documents (1,000+ pages).
        """
        if not self.is_ready or not self._client:
            logger.debug("Vector Store: Skipped upsert_chunks because vector store is not ready")
            return False

        if not chunks:
            logger.warning("Vector Store: upsert_chunks called with empty chunks list")
            return True

        if len(chunks) != len(embeddings):
            logger.error(
                f"Vector Store: Length mismatch between chunks ({len(chunks)}) and embeddings ({len(embeddings)})"
            )
            return False

        doc_coll = self.collection_name
        total_chunks = len(chunks)
        total_batches = (total_chunks + batch_size - 1) // batch_size

        for i in range(0, total_chunks, batch_size):
            batch_slice_end = min(i + batch_size, total_chunks)
            batch_chunks = chunks[i : batch_slice_end]
            batch_embeddings = embeddings[i : batch_slice_end]

            points = []
            for chunk, emb in zip(batch_chunks, batch_embeddings):
                # Resolve point id (prefer UUID, fallback to str(uuid4()))
                point_id = getattr(chunk, "chunk_id", None) or getattr(chunk, "id", None)
                if not point_id:
                    point_id = str(uuid.uuid4())
                else:
                    try:
                        point_id = str(uuid.UUID(str(point_id)))
                    except ValueError:
                        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(point_id)))

                payload = {
                    "document_id": str(getattr(chunk, "document_id", "")),
                    "org_id": str(getattr(chunk, "org_id", "")),
                    "page_number": getattr(chunk, "page_number", 1),
                    "section_heading": getattr(chunk, "section_heading", ""),
                    "chunk_index": getattr(chunk, "chunk_index", 0),
                    "text": getattr(chunk, "text", ""),
                    "token_count": getattr(chunk, "token_count", 0),
                }

                emb_array = np.asarray(emb).flatten()
                emb_vector = emb_array.tolist()
                points.append(
                    PointStruct(
                        id=str(point_id),
                        vector=emb_vector,
                        payload=payload,
                    )
                )

            try:
                await self._client.upsert(
                    collection_name=doc_coll,
                    points=points,
                    wait=True,
                )
                logger.info(
                    f"Upserted chunk batch {i // batch_size + 1}/{total_batches} ({len(points)} points)"
                )
            except Exception as e:
                logger.error(
                    f"Vector Store: Failed upserting batch slice [{i}:{batch_slice_end}] ({len(points)} points): {e}",
                    exc_info=True,
                )
                raise

        return True

    async def upsert_iso_controls(self, controls: List[dict], embeddings: np.ndarray) -> None:
        """Upsert ISO 27001 control embeddings into grc_iso_controls collection."""
        if not self.is_ready or not self._client:
            logger.debug("Vector Store: Skipped upsert_iso_controls because vector store is not ready")
            return

        ctrl_coll = settings.QDRANT_COLLECTION_ISO_CONTROLS
        points = []

        for idx, ctrl in enumerate(controls):
            emb_vector = embeddings[idx].tolist() if isinstance(embeddings[idx], np.ndarray) else list(embeddings[idx])
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"iso-control-{ctrl['id']}"))

            # Note: The chunk text here is derived from the NIST SP 800-53 Rev 5 to ISO 27001:2022 public-domain
            # cross-reference mapping. The fields below map to the standard schema, but the text is enriched
            # with operational controls mapping rather than verbatim copyrighted ISO text.
            payload = {
                "control_id": ctrl["id"],
                "annex": ctrl["annex"],
                "title": ctrl["title"],
                "description": ctrl["description"],
                "clause_id": ctrl.get("clauseId", ""),
                "section_heading": ctrl.get("section_heading", ""),
                "text": ctrl.get("text", ""),
            }

            points.append(qmodels.PointStruct(
                id=point_id,
                vector=emb_vector,
                payload=payload,
            ))

        if points:
            await self._client.upsert(collection_name=ctrl_coll, points=points)
            logger.info(f"Vector Store: Upserted {len(points)} ISO controls into '{ctrl_coll}'")

    async def dense_search(
        self,
        query_vector: np.ndarray,
        collection_name: str,
        top_k: int = 30,
        org_id: Optional[str] = None,
        document_id: Optional[str] = None,
        exclude_document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform dense vector search against specified collection.
        Optionally filters by org_id and/or document_id, and optionally excludes exclude_document_id.
        """
        if not self.is_ready or not self._client:
            return []

        vector_list = query_vector.flatten().tolist()

        # Build filter conditions
        must_filters = []
        if org_id:
            must_filters.append(qmodels.FieldCondition(
                key="org_id",
                match=qmodels.MatchValue(value=str(org_id))
            ))
        if document_id:
            must_filters.append(qmodels.FieldCondition(
                key="document_id",
                match=qmodels.MatchValue(value=str(document_id))
            ))

        must_not_filters = []
        if exclude_document_id:
            must_not_filters.append(qmodels.FieldCondition(
                key="document_id",
                match=qmodels.MatchValue(value=str(exclude_document_id))
            ))

        query_filter = qmodels.Filter(
            must=must_filters if must_filters else None,
            must_not=must_not_filters if must_not_filters else None,
        ) if (must_filters or must_not_filters) else None

        res = await self._client.query_points(
            collection_name=collection_name,
            query=vector_list,
            query_filter=query_filter,
            limit=top_k,
        )
        results = res.points

        hits = []
        for res in results:
            hits.append({
                "id": str(res.id),
                "score": float(res.score),
                "payload": res.payload or {},
            })

        return hits

# Global singleton
vector_store = VectorStoreService()
