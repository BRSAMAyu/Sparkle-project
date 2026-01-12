import asyncio
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from app.core.ingestion.ingestion_service import ingestion_service
from app.agents.graph.llm_factory import LLMFactory
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from app.core.cache import cache_service


@dataclass
class VectorChunk:
    content: str
    page_number: Optional[int]
    section_title: Optional[str]


class DocumentService:
    """
    Service for intelligent document processing:
    - Text Extraction (via IngestionService)
    - Chunked Summarization (Map-Reduce via LLM)
    - Concept Extraction
    """

    async def update_progress(self, task_id: str, status: str, percent: int, result: Any = None):
        """Helper to update task status in Redis"""
        if not task_id: return
        
        data = {
            "status": status,
            "percent": percent,
            "message": status, # redundancy for UI
            "result": result
        }
        # Save for 1 hour
        await cache_service.set(f"task:{task_id}", data, ttl=3600)

    async def clean_and_summarize(self, file_path: str, task_id: str = None, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main entry point for "Document Cleaning".
        Returns a structured summary designed for both UI display and Agent context.
        """
        options = options or {}
        enable_ocr = options.get("enable_ocr", True)
        # Note: IngestionService currently auto-detects OCR need. We could pass this flag down if we refactor IngestionService further.
        
        try:
            await self.update_progress(task_id, "Reading and parsing document...", 10)

            # 1. Physical Ingestion (OCR, Parsing)
            # This is a synchronous CPU-bound operation, might block event loop if not careful.
            chunks = await asyncio.to_thread(ingestion_service.process_file, file_path)
            
            if not chunks:
                await self.update_progress(task_id, "Failed: No text found", 100, {"error": "No extractable text found."})
                return {"status": "failed", "error": "No extractable text found."}

            await self.update_progress(task_id, "Analyzing structure...", 30)

            # 2. Reconstruct Text & Check Size
            formatted_chunks = []
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

            # 3. Process based on size
            if total_chars < 20000:
                await self.update_progress(task_id, "Generating summary...", 60)
                
                # Small file: Return full text and a quick overall summary
                full_text = "\n\n".join(sections)
                summary = await self._generate_quick_summary(full_text)
                
                result = {
                    "status": "completed",
                    "mode": "full_text",
                    "summary": summary,
                    "full_text": full_text,
                    "char_count": total_chars
                }
                await self.update_progress(task_id, "Completed", 100, result)
                return result
            else:
                # Large file: Map-Reduce
                await self.update_progress(task_id, f"Processing {len(sections)} sections (Map-Reduce)...", 50)
                
                document_map = await self._run_map_reduce(sections, task_id)
                
                result = {
                    "status": "completed",
                    "mode": "map_reduce",
                    "summary": document_map, # This is the "compressed" version
                    "full_text_preview": sections[0][:1000] + "...", # Only preview
                    "char_count": total_chars,
                    "section_count": len(sections)
                }
                await self.update_progress(task_id, "Completed", 100, result)
                return result

        except Exception as e:
            logger.error(f"Document cleaning failed: {e}")
            await self.update_progress(task_id, f"Error: {str(e)}", 100, {"error": str(e)})
            return {"status": "error", "error": str(e)}

    async def _generate_quick_summary(self, text: str) -> str:
        """Single-shot summary for small files."""
        try:
            llm = LLMFactory.get_llm("galaxy_guide", override_model="gpt-4o-mini")
            prompt = ChatPromptTemplate.from_messages([
                ("system", "Summarize this document in markdown. Include Key Concepts and Exam Hints."),
                ("human", f"{text[:20000]}")
            ])
            res = await (prompt | llm).ainvoke({})
            return res.content
        except Exception as e:
            return f"Summary generation failed: {e}"

    async def _run_map_reduce(self, sections: List[str], task_id: str = None) -> str:
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
    ) -> List[VectorChunk]:
        """
        Extract document chunks suitable for vectorization.
        """
        chunks = await asyncio.to_thread(ingestion_service.process_file, file_path)
        if not chunks:
            return []

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        results: List[VectorChunk] = []
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
                    page_number=chunk.page_num,
                    section_title=chunk.metadata.get("title") if chunk.metadata else None,
                ))

        return results

document_service = DocumentService()
