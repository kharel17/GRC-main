"""
CLI Runner for GRC Retrieval Golden Set Benchmark & Gate Threshold Calibration.
"""
import asyncio
import logging
import sys

from app.config import settings
from app.services.ai_service import ai_service
from app.services.retrieval_service import RankedChunk, retrieval_service
from app.services.vector_store import vector_store
from eval.evaluator import Evaluator, QueryEvalMetrics

logger = logging.getLogger("grc.eval.runner")

# Expanded realistic corpus including positive policy text, ambiguous overlapping text, and distractor noise
BENCHMARK_CORPUS = [
    # --- Access Control domain (nist_pos_001, 002, 003, amb_023) ---
    RankedChunk("c101", "AC-2 Account Management. Organizations manage information system accounts including identifying account types, establishing conditions for group membership, and reviewing accounts. Account management requirements for information system accounts include creation, enabling, modifying, disabling, and removing.", "doc1", "org1", 1, "AC-2 Account Management", 1),
    RankedChunk("c102", "AC-6 Least Privilege. The organization employs the principle of least privilege, allowing only authorized accesses for users which are necessary to accomplish assigned tasks. Privileged accounts and privileged account restrictions are enforced system-wide.", "doc1", "org1", 2, "AC-6 Least Privilege", 2),
    RankedChunk("c103", "AC-5 Separation of Duties. The organization separates duties of individuals as necessary to prevent malevolent activity. Separation of duties control requirements prevent any single person from completing a critical task alone.", "doc1", "org1", 3, "AC-5 Separation of Duties", 3),
    RankedChunk("c104", "AC-3 Access Enforcement. The information system enforces approved authorizations for logical access to the system in accordance with applicable access control policies. Access authorization for privileged users and authentication credentials is managed centrally.", "doc1", "org1", 4, "AC-3 Access Enforcement", 4),

    # --- Awareness and Training (nist_pos_004) ---
    RankedChunk("c105", "AT-2 Security Awareness Training. The organization provides basic security awareness training to information system users as part of initial training and when required by system changes. Security awareness training for personnel includes role-based awareness programs.", "doc1", "org1", 5, "AT-2 Security Awareness Training", 5),

    # --- Audit and Accountability (nist_pos_005, 006, amb_024) ---
    RankedChunk("c106", "AU-2 Audit Events. The organization determines that the information system is capable of auditing defined events. Audit events and audit log content requirements include logon and logoff, object access, privilege use, and system events.", "doc1", "org1", 6, "AU-2 Audit Events", 6),
    RankedChunk("c107", "AU-11 Audit Record Retention. The organization retains audit records for a defined retention period to provide support for after-the-fact investigations of security incidents. Audit record retention requirements must comply with regulatory obligations.", "doc1", "org1", 7, "AU-11 Audit Record Retention", 7),
    RankedChunk("c108", "AU-6 Audit Review, Analysis, and Reporting. The organization reviews and analyzes information system audit monitoring of incident events and reporting violations. Audit monitoring of incident events and reporting supports threat detection.", "doc1", "org1", 8, "AU-6 Audit Review", 8),

    # --- Configuration Management (nist_pos_007, 008, amb_025) ---
    RankedChunk("c109", "CM-3 Configuration Change Control. The organization determines the types of changes to the information system that are configuration-controlled. Configuration change control for systems ensures all changes are tested, reviewed, approved before deployment.", "doc1", "org1", 9, "CM-3 Configuration Change Control", 9),
    RankedChunk("c110", "CM-2 Baseline Configuration. The organization develops, documents, and maintains under configuration control a current baseline configuration of the information system. Baseline configuration and configuration settings must be reviewed regularly.", "doc1", "org1", 10, "CM-2 Baseline Configuration", 10),

    # --- Contingency Planning / Backup (nist_pos_009, amb_026) ---
    RankedChunk("c111", "CP-4 Contingency Plan Testing. The organization tests the contingency plan for the information system using defined tests to determine the effectiveness of the plan. Contingency plan testing and backup recovery exercises are conducted quarterly.", "doc1", "org1", 11, "CP-4 Contingency Plan Testing", 11),
    RankedChunk("c112", "CP-9 System Backup. The organization conducts backups of user-level information, system-level information, and system documentation. Backup recovery and contingency planning after disruption ensure continuity of operations.", "doc1", "org1", 12, "CP-9 System Backup", 12),

    # --- Incident Response (nist_pos_010) ---
    RankedChunk("c113", "IR-4 Incident Handling. The organization implements an incident handling capability that includes preparation, detection, analysis, containment, eradication, and recovery. Incident handling and incident response training are mandatory for all security personnel.", "doc1", "org1", 13, "IR-4 Incident Handling", 13),

    # --- Identification and Authentication (nist_pos_011, 012) ---
    RankedChunk("c114", "IA-2 Identification and Authentication. The information system uniquely identifies and authenticates organizational users. Identification and authentication for organizational users includes username and password combined with a second factor.", "doc1", "org1", 14, "IA-2 Identification and Authentication", 14),
    RankedChunk("c115", "IA-2(1) Multi-Factor Authentication. The information system implements multi-factor authentication for network access to privileged accounts. Multi-factor authentication requirements mandate use of two or more of: something you know, have, or are.", "doc1", "org1", 15, "IA-2(1) Multi-Factor Authentication", 15),

    # --- Maintenance (nist_pos_013, amb_030) ---
    RankedChunk("c116", "MA-3 Maintenance Tools. The organization approves, controls, and monitors information system maintenance tools. Maintenance tools and controlled maintenance activities must be logged and authorized before use.", "doc1", "org1", 16, "MA-3 Maintenance Tools", 16),
    RankedChunk("c117", "MA-2 Controlled Maintenance. The organization schedules, performs, documents, and reviews records of maintenance and repairs on information system components. Physical access controls for maintenance personnel are enforced at all times.", "doc1", "org1", 17, "MA-2 Controlled Maintenance", 17),

    # --- Media Protection (nist_pos_014, amb_028) ---
    RankedChunk("c118", "MP-6 Media Sanitization. The organization sanitizes information system media prior to disposal, release out of organizational control, or release for reuse. Media sanitization and media storage controls prevent unauthorized disclosure.", "doc1", "org1", 18, "MP-6 Media Sanitization", 18),
    RankedChunk("c119", "MP-2 Media Access. The organization restricts access to information system media to authorized individuals. Media protection for removable storage with confidentiality requirements enforces encryption and access logging.", "doc1", "org1", 19, "MP-2 Media Access", 19),

    # --- Physical Protection (nist_pos_015) ---
    RankedChunk("c120", "PE-3 Physical Access Control. The organization enforces physical access authorizations at defined entry/exit points by verifying individual access authorizations before granting access. Physical access authorizations and visitor access records are maintained for all facilities.", "doc1", "org1", 20, "PE-3 Physical Access Control", 20),

    # --- Risk Assessment (nist_pos_016, amb_029) ---
    RankedChunk("c121", "RA-5 Vulnerability Monitoring and Scanning. The organization scans for vulnerabilities in the information system and hosted applications on a defined frequency. Risk assessment vulnerability monitoring scanning identifies and prioritizes remediation.", "doc1", "org1", 21, "RA-5 Vulnerability Scanning", 21),

    # --- System and Services Acquisition (nist_pos_017, amb_027) ---
    RankedChunk("c122", "SA-3 System Development Life Cycle. The organization manages the information system using a system development life cycle methodology. System development life cycle acquisition process ensures security requirements are addressed from inception.", "doc1", "org1", 22, "SA-3 SDLC", 22),
    RankedChunk("c123", "SA-4 Acquisition Process. The organization includes security functional requirements, security strength requirements, and security assurance requirements in information system acquisition contracts. Supplier risk and system component acquisition requirements are documented.", "doc1", "org1", 23, "SA-4 Acquisition Process", 23),

    # --- System and Communications Protection (nist_pos_018) ---
    RankedChunk("c124", "SC-7 Boundary Protection. The information system monitors and controls communications at the external boundary and key internal boundaries. Boundary protection and transmission confidentiality requirements enforce encrypted data transit.", "doc1", "org1", 24, "SC-7 Boundary Protection", 24),

    # --- System and Information Integrity (nist_pos_019) ---
    RankedChunk("c125", "SI-2 Flaw Remediation. The organization identifies, reports, and corrects information system flaws. Flaw remediation and malicious code protection are implemented through patch management and endpoint security controls.", "doc1", "org1", 25, "SI-2 Flaw Remediation", 25),

    # --- Supply Chain Risk Management (nist_pos_020) ---
    RankedChunk("c126", "SR-2 Supply Chain Risk Management Plan. The organization develops a plan for managing supply chain risks associated with information systems and their components. Supply chain risk management plan addresses identification and mitigation of threats.", "doc1", "org1", 26, "SR-2 Supply Chain Risk", 26),

    # --- Personnel Security (nist_pos_021) ---
    RankedChunk("c127", "PS-3 Personnel Screening. The organization screens individuals prior to authorizing access to the information system. Personnel screening and personnel termination controls ensure background investigations are performed and access is revoked promptly.", "doc1", "org1", 27, "PS-3 Personnel Screening", 27),

    # --- Privacy (nist_pos_022) ---
    RankedChunk("c128", "PT-2 Privacy Impact Assessment. The organization conducts privacy impact assessments for information systems involving personally identifiable information. Privacy impact assessment and personally identifiable information processing controls are documented.", "doc1", "org1", 28, "PT-2 Privacy Impact Assessment", 28),

    # --- Legacy chunks retained for backward compat with original golden_set.json ---
    RankedChunk("c129", "5.17 Authentication information. Passwords and secret authentication credentials rules and complexity requirements.", "doc1", "org1", 29, "5.17 Authentication Credentials", 29),
    RankedChunk("c130", "5.12 Classification of information. Information labeling, classification schema, and storage media handling.", "doc1", "org1", 30, "5.12 Information Classification", 30),
    RankedChunk("c131", "8.24 Cryptography policy. AES-256 encryption required for data at rest. TLS 1.3 enforced for data in transit.", "doc1", "org1", 31, "8.24 Cryptography", 31),
    RankedChunk("c132", "8.8 Vulnerability management. Weekly automated vulnerability scans. Critical patch management window is 72 hours.", "doc1", "org1", 32, "8.8 Vulnerability Management", 32),
    RankedChunk("c133", "7.1 Physical security perimeter. Biometric access control, CCTV monitoring of server room.", "doc1", "org1", 33, "7.1 Physical Security", 33),
    RankedChunk("c134", "8.15 Logging and monitoring. Audit log collection via SIEM. Privileged access events logged with tamper-evident integrity.", "doc1", "org1", 34, "8.15 Logging", 34),
    RankedChunk("c135", "5.29 Business continuity. Disaster recovery quarterly drills. Recovery time objective (RTO) maximum 4 hours.", "doc1", "org1", 35, "5.29 Business Continuity", 35),
    RankedChunk("c136", "6.1 Human resource security. Pre-employment background screening required. Non-disclosure agreements (NDA) signed before access.", "doc1", "org1", 36, "6.1 HR Security", 36),
    RankedChunk("c137", "5.24 Incident management. Security incident response procedure. Incident reporting required within 4 hours.", "doc1", "org1", 37, "5.24 Incident Management", 37),
    RankedChunk("c138", "5.15 Access control policy. Role-based access control (RBAC) restricts access to systems. Multi-factor authentication (MFA) is required for all administrative accounts.", "doc1", "org1", 38, "5.15 Access Control", 38),
]


async def run_evaluation():
    print("=" * 75)
    print(" GRC Retrieval Pipeline & Confidence Gate Calibration Benchmark")
    print("=" * 75)

    # 1. Initialize services
    if not ai_service.is_ready:
        ai_service.initialize()
    retrieval_service.initialize()
    await vector_store.initialize_collections()

    from pathlib import Path
    golden_set_name = sys.argv[1] if len(sys.argv) > 1 else "golden_set.json"
    evaluator = Evaluator(golden_set_path=Path(__file__).parent / golden_set_name)
    results: list[QueryEvalMetrics] = []

    use_qdrant = vector_store.is_ready
    if use_qdrant:
        print(" Evaluation Mode : QDRANT LIVE STORE")
        from app.ingestion.chunker import Chunk
        benchmark_chunks = [
            Chunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                org_id=c.org_id,
                page_number=c.page_number,
                section_heading=c.section_heading,
                chunk_index=c.chunk_index,
                text=c.text,
                token_count=len(c.text.split()),
            )
            for c in BENCHMARK_CORPUS
        ]
        # ── Deterministic clean-state: purge ALL existing points in
        # grc_doc_chunks before re-inserting the canonical BENCHMARK_CORPUS.
        # Without this, leftover real-document chunks from previous ingestion
        # tests change the BM25→RRF candidate pool and produce different
        # CrossEncoder margins across runs, making the baseline non-reproducible.
        from qdrant_client import models as qmodels
        await vector_store._client.delete(
            collection_name=settings.QDRANT_COLLECTION_DOC_CHUNKS,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(must=[])
            ),
        )
        logger.info("Eval: purged grc_doc_chunks before benchmark upsert (clean-state run)")

        embeddings = ai_service._embed_texts([c.text for c in benchmark_chunks])
        await vector_store.upsert_chunks(benchmark_chunks, embeddings)
    else:
        print(" Evaluation Mode : BENCHMARK CORPUS (BM25 + CrossEncoder, Qdrant offline)")

    print(f" Loaded {len(evaluator.test_cases)} test queries (Positive, Ambiguous, Hard-Negative).\n")
    print(f" Current Config Thresholds: TOP1 = {settings.CONFIDENCE_GATE_TOP1_THRESHOLD}, MARGIN = {settings.CONFIDENCE_GATE_MARGIN_THRESHOLD}\n")

    # 2. Iterate through test cases
    for tc in evaluator.test_cases:
        qid = tc["id"]
        query = tc["query"]
        domain = tc["domain"]
        expected_annexes = tc.get("expected_annexes", [])
        expected_keywords = tc.get("expected_keywords", [])
        expected_verdict = tc.get("expected_verdict", "accept")

        if use_qdrant:
            coll = "grc_iso_controls" if "iso" in golden_set_name.lower() else "grc_doc_chunks"
            retrieved = await retrieval_service.hybrid_retrieve(
                query=query,
                collection=coll,
                top_k_dense=20,
                top_k_sparse=20,
                rerank_top_n=10,
            )
        else:
            sparse = await retrieval_service.sparse_retrieve(query, list(BENCHMARK_CORPUS), top_k=8)
            fused = retrieval_service.rrf_fuse(list(BENCHMARK_CORPUS), sparse)
            retrieved = retrieval_service.rerank(query, fused, top_n=8)

        metrics = evaluator.evaluate_query(
            query_id=qid,
            query_text=query,
            domain=domain,
            expected_annexes=expected_annexes,
            expected_keywords=expected_keywords,
            expected_verdict=expected_verdict,
            retrieved_chunks=retrieved,
        )
        results.append(metrics)

        correct_flag = "OK" if metrics.verdict_correct else "MISMATCH"
        print(
            f"[{qid:<10}] {domain:<26} | Exp: {expected_verdict:<22} | Act: {metrics.actual_verdict:<22} "
            f"| Top1: {metrics.top1_score:.4f} | Margin: {metrics.score_margin:.4f} | [{correct_flag}]"
        )

    # 3. Aggregate results
    summary = evaluator.summarize(results)

    print("\n" + "=" * 75)
    print(" BENCHMARK SUMMARY & GATE CALIBRATION RESULTS")
    print("=" * 75)
    print(f" Total Queries Evaluated   : {summary.total_queries}")
    print(f" Mean Reciprocal Rank (MRR): {summary.mrr:.4f}")
    print(f" Gate Verdict Accuracy     : {summary.gate_accuracy * 100:.1f}% ({sum(1 for m in results if m.verdict_correct)}/{summary.total_queries})")
    print("-" * 75)

    pos_scores = [m.top1_score for m in results if m.expected_verdict == "accept"]
    neg_scores = [m.top1_score for m in results if m.expected_verdict == "insufficient_evidence"]
    amb_margins = [m.score_margin for m in results if m.expected_verdict == "needs_review"]

    print(" Score Distributions:")
    if pos_scores:
        print(f"   Positive Matches Top1 Score Range  : min={min(pos_scores):.4f}, max={max(pos_scores):.4f}, mean={sum(pos_scores)/len(pos_scores):.4f}")
    if neg_scores:
        print(f"   Hard-Negative Top1 Score Range     : min={min(neg_scores):.4f}, max={max(neg_scores):.4f}, mean={sum(neg_scores)/len(neg_scores):.4f}")
    if amb_margins:
        print(f"   Ambiguous Match Margin Range       : min={min(amb_margins):.4f}, max={max(amb_margins):.4f}, mean={sum(amb_margins)/len(amb_margins):.4f}")

    print("-" * 75)
    print(" Recall @ K (Positive Queries):")
    for k, r in summary.avg_recall_at_k.items():
        print(f"   Recall@{k:<2}  : {r:.4f} ({r*100:.1f}%)")
    print("=" * 75)

    return summary


if __name__ == "__main__":
    asyncio.run(run_evaluation())
