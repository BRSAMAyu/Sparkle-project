from __future__ import annotations
import asyncio
import inspect
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from loguru import logger

from app.config import settings
from app.config.phase5_config import get_quality_threshold_for_doc_type, phase5_config
from app.core.cache import cache_service
from app.core.ingestion.ingestion_service import ingestion_service
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode


@dataclass
class VectorChunk:
    content: str
    page_numbers: list[int]  # Changed to list
    section_title: str | None
    metadata: dict = field(default_factory=dict)
    ocr_confidence: float | None = None  # 0.0-1.0, None if not from OCR

@dataclass
class QualityResult:
    passed: bool
    score: float
    issues: list[str]

class DocumentService:
    # ... existing methods ...

    def _detect_document_type(self, chunks: list[VectorChunk]) -> str:
        """
        检测文档类型
        Returns: "academic" | "invoice" | "general" | "code"
        """
        if not chunks:
            return "general"

        sample_text = " ".join([c.content[:200] for c in chunks[:3]])

        # 学术论文特征
        academic_keywords = ["abstract", "introduction", "conclusion", "references", "doi:", "arxiv"]
        academic_score = sum(1 for kw in academic_keywords if kw.lower() in sample_text.lower())

        # 代码特征
        code_patterns = [r'\bdef\s+\w+', r'\bclass\s+\w+', r'\bimport\s+\w+', r'function\s*\(']
        code_score = sum(1 for pattern in code_patterns if re.search(pattern, sample_text))

        # 发票特征
        invoice_keywords = ["invoice", "bill", "amount", "tax", "total", "发票", "金额"]
        invoice_score = sum(1 for kw in invoice_keywords if kw.lower() in sample_text.lower())

        if academic_score >= 2:
            return "academic"
        elif code_score >= 2:
            return "code"
        elif invoice_score >= 2:
            return "invoice"
        else:
            return "general"

    def _check_garbled_content(self, text: str, doc_type: str) -> tuple[float, list[str]]:
        """
        检查乱码内容
        Returns: (garbled_ratio, issues)
        """
        issues = []

        if not text:
            return 1.0, ["Empty content"]

        # 1. 统计非打印字符
        non_printable_count = sum(
            1 for char in text
            if not char.isprintable() and char not in ['\n', '\t', '\r']
        )

        # 2. 统计替换字符（常见乱码标志）
        replacement_chars = ['�', '\ufffd', '□', '▯']
        replacement_count = sum(text.count(char) for char in replacement_chars)

        # 3. 统计连续乱码字符
        max_consecutive_garbled = 0
        current_consecutive = 0

        for char in text:
            if char in replacement_chars or (not char.isprintable() and char not in ['\n', '\t', '\r']):
                current_consecutive += 1
                max_consecutive_garbled = max(max_consecutive_garbled, current_consecutive)
            else:
                current_consecutive = 0

        if max_consecutive_garbled > phase5_config.DOC_QUALITY_MAX_CONSECUTIVE_GARBLED:
            issues.append(
                f"Found {max_consecutive_garbled} consecutive garbled characters"
            )

        # 4. 计算乱码率
        total_suspicious = non_printable_count + replacement_count
        garbled_ratio = total_suspicious / len(text) if len(text) > 0 else 0

        # 5. 针对文档类型调整判断
        if doc_type == "academic" and phase5_config.DOC_QUALITY_MATH_SYMBOLS_ALLOWED:
            # 学术论文允许数学符号，降低乱码率权重
            garbled_ratio *= 0.7

        threshold = get_quality_threshold_for_doc_type(doc_type)

        if garbled_ratio > threshold:
            issues.append(
                f"High garbled ratio ({garbled_ratio:.2%}) exceeds threshold "
                f"({threshold:.2%}) for {doc_type} documents"
            )

        return garbled_ratio, issues

    def _check_language_consistency(self, text: str) -> tuple[float, list[str]]:
        """
        检查语言一致性（针对中文文档）
        Returns: (consistency_score, issues)
        """
        issues = []

        if not text:
            return 0.0, ["Empty content"]

        # 统计中文字符
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        # 统计字母
        latin_chars = sum(1 for char in text if char.isalpha() and ord(char) < 128)
        # 统计数字
        digit_chars = sum(1 for char in text if char.isdigit())

        total_meaningful = chinese_chars + latin_chars + digit_chars

        if total_meaningful == 0:
            return 0.0, ["No meaningful characters found"]

        chinese_ratio = chinese_chars / total_meaningful

        # 如果检测到是中文为主的文档，检查中文比例
        if chinese_ratio > phase5_config.DOC_QUALITY_CHINESE_MIN_RATIO:
            # 这是中文文档
            if chinese_ratio < 0.3:
                issues.append(
                    f"Chinese document has low Chinese character ratio: {chinese_ratio:.2%}"
                )
                return chinese_ratio, issues

        return 1.0, []

    def _check_content_structure(self, chunks: list[VectorChunk]) -> tuple[float, list[str]]:
        """
        检查内容结构完整性
        Returns: (structure_score, issues)
        """
        issues = []

        if not chunks:
            return 0.0, ["No chunks"]

        # 1. 检查切片长度分布
        chunk_lengths = [len(c.content) for c in chunks]
        sum(chunk_lengths) / len(chunk_lengths)

        # 过短的切片（可能是表格碎片或解析错误）
        very_short_chunks = sum(1 for length in chunk_lengths if length < 50)
        short_ratio = very_short_chunks / len(chunks)

        if short_ratio > 0.5:
            issues.append(
                f"Too many short chunks ({short_ratio:.1%}), "
                "may indicate poor OCR or table parsing"
            )

        # 2. 检查重复内容（页眉页脚）
        if len(chunks) > 2:
            # 简单检查：前两个和最后两个切片是否高度相似
            first_two = " ".join([c.content[:100] for c in chunks[:2]])
            last_two = " ".join([c.content[:100] for c in chunks[-2:]])

            # 简单相似度：共同词汇数
            words1 = set(first_two.lower().split())
            words2 = set(last_two.lower().split())

            if len(words1) > 0 and len(words2) > 0:
                similarity = len(words1 & words2) / len(words1 | words2)
                if similarity > 0.8:
                    issues.append("Detected repeated headers/footers across pages")

        # 3. 计算结构分数
        structure_score = 1.0 - short_ratio

        return max(structure_score, 0.0), issues

    def _check_ocr_confidence(self, chunks: list[VectorChunk]) -> tuple[float, list[str]]:
        """
        检查 OCR 置信度
        Returns: (avg_confidence, issues)
        """
        issues = []

        # 收集所有 OCR 置信度
        ocr_confidences = [
            c.ocr_confidence for c in chunks
            if c.ocr_confidence is not None
        ]

        if not ocr_confidences:
            # 没有 OCR 内容，返回满分
            return 1.0, []

        avg_confidence = sum(ocr_confidences) / len(ocr_confidences)

        # 检查是否低于阈值
        threshold = phase5_config.DOC_QUALITY_OCR_CONFIDENCE_THRESHOLD

        if avg_confidence < threshold:
            issues.append(
                f"Low OCR confidence ({avg_confidence:.2%}), "
                f"threshold is {threshold:.2%}. "
                f"Document may contain poor scan quality or handwriting."
            )

        # 检查个别页面置信度过低
        low_conf_pages = sum(1 for c in ocr_confidences if c < 0.5)
        if low_conf_pages > 0:
            issues.append(
                f"{low_conf_pages} page(s) have very low OCR confidence (<50%)"
            )

        return avg_confidence, issues

    def check_quality(
        self,
        chunks: list[VectorChunk],
        doc_type: str | None = None
    ) -> QualityResult:
        """
        改进的文档质量检测

        分层检测策略：
        1. 基础检查：内容长度
        2. 字符检查：乱码率
        3. 语言检查：中英文一致性
        4. 结构检查：切片分布、重复内容
        5. OCR 置信度检查

        Args:
            chunks: 文档切片列表
            doc_type: 文档类型（可选，自动检测）

        Returns:
            QualityResult: 质量检测结果
        """
        issues = []

        # 0. 基础检查
        if not chunks:
            self._report_metrics("unknown", False, 0.0, 0.0, None, ["no_content"])
            return QualityResult(
                passed=False,
                score=0.0,
                issues=["No text content extracted"]
            )

        total_text = " ".join([c.content for c in chunks])
        total_len = len(total_text)

        if total_len < phase5_config.DOC_QUALITY_MIN_LENGTH:
            has_ocr = any(c.ocr_confidence is not None for c in chunks)
            if not has_ocr:
                self._report_metrics("unknown", False, 0.1, 0.0, None, ["too_short"])
                return QualityResult(
                    passed=False,
                    score=0.1,
                    issues=[
                        f"Content too short: {total_len} chars "
                        f"(minimum: {phase5_config.DOC_QUALITY_MIN_LENGTH})"
                    ]
                )
            issues.append(
                f"Content too short: {total_len} chars "
                f"(minimum: {phase5_config.DOC_QUALITY_MIN_LENGTH})"
            )

        # 1. 文档类型检测
        if doc_type is None:
            doc_type = self._detect_document_type(chunks)

        logger.info(f"Detected document type: {doc_type}")

        # 2. 乱码检测
        garbled_ratio, garbled_issues = self._check_garbled_content(total_text, doc_type)
        issues.extend(garbled_issues)

        # 3. 语言一致性检测
        lang_score, lang_issues = self._check_language_consistency(total_text)
        issues.extend(lang_issues)

        # 4. 结构完整性检测
        structure_score, structure_issues = self._check_content_structure(chunks)
        issues.extend(structure_issues)

        # 5. OCR 置信度检测
        ocr_confidence, ocr_issues = self._check_ocr_confidence(chunks)
        issues.extend(ocr_issues)

        # 6. 综合评分
        # 权重：乱码率 35%，语言一致性 25%，结构 25%，OCR 置信度 15%
        garbled_score = 1.0 - garbled_ratio
        final_score = (
            0.35 * garbled_score +
            0.25 * lang_score +
            0.25 * structure_score +
            0.15 * ocr_confidence
        )

        # 7. 判定通过条件
        threshold = get_quality_threshold_for_doc_type(doc_type)
        pass_threshold = 0.7

        # OCR 置信度过低也应该失败
        ocr_threshold = phase5_config.DOC_QUALITY_OCR_CONFIDENCE_THRESHOLD
        ocr_passed = ocr_confidence >= ocr_threshold

        passed = (
            final_score >= pass_threshold and
            garbled_ratio <= threshold and
            ocr_passed
        )

        logger.info(
            f"Quality check: score={final_score:.3f}, "
            f"garbled={garbled_ratio:.3f}, "
            f"lang={lang_score:.3f}, "
            f"structure={structure_score:.3f}, "
            f"ocr_conf={ocr_confidence:.3f}, "
            f"passed={passed}"
        )

        # 8. 上报指标
        issue_types = self._categorize_issues(issues)
        self._report_metrics(
            doc_type=doc_type,
            passed=passed,
            score=final_score,
            garbled_ratio=garbled_ratio,
            ocr_confidence=ocr_confidence if ocr_confidence < 1.0 else None,
            issue_types=issue_types
        )

        return QualityResult(
            passed=passed,
            score=final_score,
            issues=issues if not passed else []
        )

    async def _generate_quick_summary(self, text: str) -> str:
        """Generate a lightweight summary without external model dependencies."""
        stripped = (text or "").strip()
        if not stripped:
            return "No content available."
        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        preview = " ".join(lines)[:400]
        return f"文档摘要:\n- 内容长度: {len(stripped)} 字符\n- 预览: {preview}"

    async def _run_map_reduce(self, sections: list[str], task_id: str = None) -> str:
        """Summarize large documents section by section."""
        if not sections:
            return "# 📂 Document Structure (Compressed)\n\n(No sections found)"

        summaries = []
        total = len(sections)
        for index, section in enumerate(sections, start=1):
            summary = await self._extract_section_summary(index - 1, section)
            summaries.append(summary)
            if task_id:
                progress = 50 + int((index / total) * 40)
                await self.update_progress(task_id, f"Analyzing section {index}/{total}...", progress)
        return "# 📂 Document Structure (Compressed)\n\n" + "\n\n".join(summaries)

    async def _extract_section_summary(self, index: int, text: str) -> str:
        cleaned = " ".join((text or "").split())
        preview = cleaned[:280] if cleaned else "(empty)"
        return f"### Part {index + 1}\n- **Summary**: {preview}"

    def _categorize_issues(self, issues: list[str]) -> list[str]:
        """将问题列表分类为指标标签"""
        categories = []
        issue_text = " ".join(issues).lower()

        if "garbled" in issue_text:
            categories.append("garbled")
        if "short" in issue_text:
            categories.append("too_short")
        if "chinese" in issue_text:
            categories.append("low_chinese_ratio")
        if "repeated" in issue_text or "headers" in issue_text:
            categories.append("repeated_headers")
        if "ocr" in issue_text or "confidence" in issue_text:
            categories.append("low_ocr_confidence")

        return categories

    def _report_metrics(
        self,
        doc_type: str,
        passed: bool,
        score: float,
        garbled_ratio: float,
        ocr_confidence: float | None,
        issue_types: list[str]
    ) -> None:
        """上报文档质量指标到 Prometheus"""
        try:
            from app.core.metrics import (
                DOC_GARBLED_RATIO,
                DOC_OCR_CONFIDENCE,
                DOC_QUALITY_CHECK_COUNT,
                DOC_QUALITY_ISSUES,
                DOC_QUALITY_SCORE,
            )

            # 1. 检测计数
            result = "passed" if passed else "failed"
            DOC_QUALITY_CHECK_COUNT.labels(doc_type=doc_type, result=result).inc()

            # 2. 质量分数分布
            DOC_QUALITY_SCORE.labels(doc_type=doc_type).observe(score)

            # 3. 乱码率分布
            DOC_GARBLED_RATIO.labels(doc_type=doc_type).observe(garbled_ratio)

            # 4. OCR 置信度分布（仅当有 OCR 内容时）
            if ocr_confidence is not None:
                DOC_OCR_CONFIDENCE.observe(ocr_confidence)

            # 5. 问题类型计数
            for issue_type in issue_types:
                DOC_QUALITY_ISSUES.labels(issue_type=issue_type).inc()

        except ImportError:
            # 指标模块未安装，静默跳过
            pass
        except Exception as e:
            logger.warning(f"Failed to report quality metrics: {e}")

    async def draft_knowledge_nodes(self, db_session, file_id: UUID, user_id: UUID, chunks: list[VectorChunk]):
        """
        Create draft knowledge nodes from document chunks.
        Strategy:
        - One root node for the Document.
        - Child nodes for identified sections (if any).
        """
        # 1. Get File Info
        file_record = await db_session.get(StoredFile, file_id)
        if not file_record:
            logger.error(f"File {file_id} not found for drafting")
            return

        document_text = "\n\n".join(chunk.content for chunk in chunks if chunk.content)
        if document_text.strip():
            try:
                from app.services.galaxy_service import GalaxyService

                galaxy_service = GalaxyService(db_session)
                await galaxy_service.create_nodes_from_document(
                    user_id=user_id,
                    file_id=file_id,
                    file_name=file_record.file_name,
                    document_text=document_text,
                )
                logger.info(f"Drafted ontology-driven knowledge nodes for file {file_id}")
                return
            except Exception as exc:
                logger.warning(f"Ontology drafting failed for file {file_id}, fallback to section heuristic: {exc}")

        # 2. Create Root Node
        root_node = KnowledgeNode(
            name=file_record.file_name,
            description=f"Imported from {file_record.file_name}",
            source_type="document_import",
            source_file_id=file_id,
            status="draft",
            importance_level=3,
            is_seed=False
        )
        db_session.add(root_node)
        await db_session.flush() # Get ID

        # 3. Create Section Nodes (Simple Heuristic)
        # Group chunks by section_title
        sections = {}
        for i, chunk in enumerate(chunks):
            title = chunk.section_title or "General"
            if title not in sections:
                sections[title] = []
            sections[title].append(i) # Store chunk index/ref

        for title, chunk_indices in sections.items():
            if title == "General" and len(sections) == 1:
                # If only General, link chunks to root
                root_node.chunk_refs = chunk_indices
                continue

            # Create child node
            child = KnowledgeNode(
                name=title[:50], # Truncate long titles
                parent_id=root_node.id,
                source_type="document_import",
                source_file_id=file_id,
                status="draft",
                chunk_refs=chunk_indices,
                is_seed=False
            )
            db_session.add(child)

        await db_session.commit()
        logger.info(f"Drafted knowledge nodes for file {file_id}")

    # ... existing clean_and_summarize ...

    """
    Service for intelligent document processing:
    - Text Extraction (via IngestionService)
    - Chunked Summarization (Map-Reduce via LLM)
    - Concept Extraction
    """

    async def update_progress(self, task_id: str, status: str, percent: int, result: Any = None):
        """Helper to update task status in Redis"""
        if not task_id:
            return

        normalized_status = self._normalize_task_status(status, percent)

        data = {
            "status": normalized_status,
            "percent": percent,
            "message": status, # redundancy for UI
            "result": result
        }
        # Save for 1 hour
        cache_result = cache_service.set(f"task:{task_id}", data, ttl=3600)
        if inspect.isawaitable(cache_result):
            await cache_result

    def _normalize_task_status(self, status: str, percent: int) -> str:
        normalized = (status or "").strip().lower()
        if normalized in {"queued", "processing", "completed", "failed", "error"}:
            return normalized
        if "complete" in normalized or percent >= 100:
            return "completed"
        if "fail" in normalized or "error" in normalized:
            return "failed"
        if "queue" in normalized or percent <= 0:
            return "queued"
        return "processing"

    async def clean_and_summarize(self, file_path: str, task_id: str = None, options: dict[str, Any] = None) -> dict[str, Any]:
        """
        Main entry point for "Document Cleaning".
        Returns a structured summary designed for both UI display and Agent context.

        Size limit: Cleaned content is limited to 10MB. For larger documents,
        only compressed summaries are returned.
        """
        options = options or {}

        # 定义10MB大小限制（字节）
        MAX_CLEANED_SIZE = 10 * 1024 * 1024

        try:
            resolved_path = _resolve_allowed_path(file_path)
            if not resolved_path:
                await self.update_progress(task_id, "Failed: Invalid file path", 100, {"error": "Invalid file path."})
                return {"status": "failed", "error": "Invalid file path."}

            await self.update_progress(task_id, "Reading and parsing document...", 10)

            # 1. Physical Ingestion (OCR, Parsing)
            # This is a synchronous CPU-bound operation, might block event loop if not careful.
            chunks = await asyncio.to_thread(ingestion_service.process_file, resolved_path, options)

            if not chunks:
                await self.update_progress(task_id, "Failed: No text found", 100, {"error": "No extractable text found."})
                return {"status": "failed", "error": "No extractable text found."}

            await self.update_progress(task_id, "Analyzing structure...", 30)

            # 2. Reconstruct Text & Check Size
            total_chars = 0
            current_section = []
            sections = []
            SECTION_LIMIT = 15000

            for chunk in chunks:
                meta = chunk.metadata
                prefix = "## " if meta.get("is_header") else ""
                if meta.get("is_bold"): prefix += "**"
                suffix = "**" if meta.get("is_bold") and not meta.get("is_header") else ""

                text = f"{prefix}{chunk.text}{suffix}"
                current_section.append(text)
                total_chars += len(text)

                if sum(len(s) for s in current_section) > SECTION_LIMIT:
                    sections.append("\n\n".join(current_section))
                    current_section = []

            if current_section:
                sections.append("\n\n".join(current_section))

            # 3. Process based on size (10MB = approximately 5 million characters in UTF-8)
            MAX_CHARS = MAX_CLEANED_SIZE  # Conservative estimate
            await self.update_progress(task_id, f"Processing document ({total_chars:,} chars)...", 40)

            if total_chars < 20000:
                await self.update_progress(task_id, "Generating summary...", 60)

                # Small file: Return full text and a quick overall summary
                full_text = "\n\n".join(sections)
                summary = await self._generate_quick_summary(full_text)

                # 检查是否超过大小限制
                full_text_size = len(full_text.encode('utf-8'))
                if full_text_size > MAX_CLEANED_SIZE:
                    logger.warning(f"Cleaned content ({full_text_size:,} bytes) exceeds 10MB limit, truncating")
                    # 截断到接近10MB
                    max_chars = int(MAX_CLEANED_SIZE * 0.9)  # 留一些余量
                    full_text = full_text[:max_chars] + "\n\n... [Content truncated due to size limit]"

                result = {
                    "status": "completed",
                    "mode": "full_text",
                    "summary": summary,
                    "full_text": full_text,
                    "char_count": total_chars,
                    "size_bytes": full_text_size,
                    "truncated": full_text_size > MAX_CLEANED_SIZE
                }
                await self.update_progress(task_id, "Completed", 100, result)
                return result

            elif total_chars <= MAX_CHARS:
                # Medium file: Return full text (within 10MB limit)
                await self.update_progress(task_id, f"Processing {len(sections)} sections...", 50)

                full_text = "\n\n".join(sections)
                summary = await self._generate_quick_summary(full_text[:50000])  # Summary from first 50K chars

                result = {
                    "status": "completed",
                    "mode": "full_text",
                    "summary": summary,
                    "full_text": full_text,
                    "char_count": total_chars,
                    "size_bytes": len(full_text.encode('utf-8')),
                    "truncated": False
                }
                await self.update_progress(task_id, "Completed", 100, result)
                return result

            else:
                # Large file (>10MB): Map-Reduce compression only
                await self.update_progress(task_id, f"Compressing large document ({total_chars:,} chars)...", 50)

                document_map = await self._run_map_reduce(sections, task_id)
                compressed_size = len(document_map.encode('utf-8'))

                logger.info(
                    f"Compressed document from {total_chars:,} chars to "
                    f"{compressed_size:,} bytes ({compressed_size/total_chars*100:.1f}% of original)"
                )

                result = {
                    "status": "completed",
                    "mode": "compressed",
                    "summary": document_map,  # This is the "compressed" version
                    "full_text_preview": sections[0][:2000] + "\n\n... [Content truncated due to size limit]",
                    "char_count": total_chars,
                    "compressed_size_bytes": compressed_size,
                    "section_count": len(sections),
                    "truncated": True,
                    "message": "Document exceeds 10MB limit. Only compressed summary is available."
                }
                await self.update_progress(task_id, "Completed", 100, result)
                return result

        except Exception as e:
            logger.error(f"Document cleaning failed: {e}", exc_info=True)
            await self.update_progress(task_id, f"Error: {str(e)}", 100, {"error": str(e)})
            return {"status": "error", "error": str(e)}


def _resolve_allowed_path(file_path: str) -> str | None:
    """
    安全地解析文件路径，防止路径穿越攻击。

    安全措施：
    1. 显式检查 .. 路径组件
    2. 拒绝绝对路径（除非在允许的根目录下）
    3. 使用 abspath 而不是 realpath（不跟随符号链接）
    4. 验证符号链接目标也在允许范围内
    """
    if not file_path:
        return None

    # 1. 显式检查路径遍历攻击
    if ".." in file_path:
        logger.warning(f"Path traversal attempt detected: {file_path}")
        return None

    # 2. 规范化路径（不跟随符号链接）
    resolved = os.path.abspath(file_path)

    # 3. 验证文件存在且是常规文件
    if not os.path.isfile(resolved):
        return None

    # 4. 检查是否是符号链接
    if os.path.islink(resolved):
        logger.warning(f"Symbolic links are not allowed: {file_path}")
        return None

    # 5. 验证在允许的目录下
    allowed_roots = [
        os.path.abspath(settings.UPLOAD_DIR),
        os.path.abspath(
            os.path.join(
                os.getenv("SPARKLE_UPLOAD_TEMP_DIR", tempfile.gettempdir()),
                "sparkle_uploads",
            )
        ),
    ]

    for root in allowed_roots:
        # 确保根目录存在
        if not os.path.isdir(root):
            continue

        # 不能直接是根目录
        if resolved == root:
            return None

        # 必须在根目录下
        if resolved.startswith(root + os.sep):
            return resolved

    logger.warning(f"File path outside allowed roots: {file_path}")
    return None

    async def _generate_quick_summary(self, text: str) -> str:
        """Single-shot summary for small files."""
        try:
            try:
                from langchain_core.prompts import ChatPromptTemplate

                from app.agents.graph.llm_factory import LLMFactory
            except ImportError as exc:
                raise HTTPException(
                    status_code=501,
                    detail="LLM summarization requires langchain dependencies (llm extras)."
                ) from exc

            llm = LLMFactory.get_llm("galaxy_guide", override_model="gpt-4o-mini")
            prompt = ChatPromptTemplate.from_messages([
                ("system", "Summarize this document in markdown. Include Key Concepts and Exam Hints."),
                ("human", f"{text[:20000]}")
            ])
            res = await (prompt | llm).ainvoke({})
            return res.content
        except Exception as e:
            return f"Summary generation failed: {e}"

    async def _run_map_reduce(self, sections: list[str], task_id: str = None) -> str:
        """Execute parallel chunk summarization."""
        sem = asyncio.Semaphore(5)
        total = len(sections)
        completed = 0

        async def throttled_extract(i, sec):
            nonlocal completed
            async with sem:
                res = await self._extract_section_summary(i, sec)
                completed += 1
                if task_id:
                    # Update progress proportionally from 50% to 90%
                    progress = 50 + int((completed / total) * 40)
                    await self.update_progress(task_id, f"Analyzing section {completed}/{total}...", progress)
                return res

        summaries = await asyncio.gather(*[
            throttled_extract(i, sec) for i, sec in enumerate(sections)
        ])

        return "# 📂 Document Structure (Compressed)\n\n" + "\n\n".join(summaries)

    async def _extract_section_summary(self, index: int, text: str) -> str:
        try:
            try:
                from langchain_core.prompts import ChatPromptTemplate

                from app.agents.graph.llm_factory import LLMFactory
            except ImportError as exc:
                raise HTTPException(
                    status_code=501,
                    detail="LLM summarization requires langchain dependencies (llm extras)."
                ) from exc

            llm = LLMFactory.get_llm("galaxy_guide", override_model="gpt-4o-mini")
            prompt = ChatPromptTemplate.from_messages([
                ("system", "Analyze this section. Output compact Markdown."),
                ("human", f"""Analyze Part {index+1}.
                Format:
                ### Part {index+1}: [Title]
                - **Concepts**: [Tags]
                - **Summary**: [Content]
                - **Exam Hints**: [Hints]

                Text:
                {text[:15000]}
                """)
            ])
            response = await (prompt | llm).ainvoke({})
            return response.content
        except Exception as e:
            return f"### Part {index+1}: Error - {str(e)}"

    async def extract_vector_chunks(
        self,
        file_path: str,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
    ) -> list[VectorChunk]:
        """
        Extract document chunks suitable for vectorization.
        """
        chunks = await asyncio.to_thread(ingestion_service.process_file, file_path)
        if not chunks:
            return []

        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError as exc:
            raise HTTPException(
                status_code=501,
                detail="Vector chunking requires langchain-text-splitters (llm extras)."
            ) from exc

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        results: list[VectorChunk] = []
        for chunk in chunks:
            text = (chunk.text or "").strip()
            if not text:
                continue
            for piece in splitter.split_text(text):
                content = piece.strip()
                if len(content) < 20:
                    continue
                results.append(VectorChunk(
                    content=content,
                    page_numbers=[chunk.page_num] if chunk.page_num else [],
                    section_title=chunk.metadata.get("title") if chunk.metadata else None,
                    ocr_confidence=chunk.ocr_confidence,
                ))

        return results

document_service = DocumentService()
