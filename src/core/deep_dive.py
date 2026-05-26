"""
Deep Dive Handler untuk ScholarScout.
Menghasilkan analisis mendalam untuk sebuah ide riset: outline, metodologi, dataset, referensi, timeline, tools.

v1.5: Adds grounding verification — compare each Deep Dive section against the
inspiration paper's abstract using semantic similarity. Returns confidence
scores (0.0-1.0) per section so the UI can show green/yellow/red badges.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import json

from src.core.llm import LLMClient
from src.core.config import Config


@dataclass
class DeepDiveResponse:
    """Respons analisis mendalam untuk sebuah ide riset."""
    outline: List[str]           # 5-7 item chapter/section titles
    methodology: str             # paragraf teks metodologi
    datasets: List[str]          # 3-5 item dengan deskripsi singkat
    references: List[Dict[str, str]]  # [{"title": str, "url": str}]
    timeline: str                # teks estimasi timeline
    tools: List[str]             # 5-8 item tools/frameworks

    # Field wajib yang harus ada dalam respons LLM
    REQUIRED_FIELDS = {"outline", "methodology", "datasets", "references", "timeline", "tools"}


class DeepDiveHandler:
    """
    Handler untuk menghasilkan analisis mendalam sebuah ide riset.
    Memanggil LLM untuk menghasilkan outline, metodologi, dataset, referensi, timeline, dan tools.
    """

    def __init__(self, llm_client: LLMClient):
        """
        Inisialisasi DeepDiveHandler.
        
        Args:
            llm_client: Instance LLMClient untuk komunikasi dengan LLM API
        """
        self.llm = llm_client

    def generate(self, idea: dict, language: str = 'en') -> dict:
        """
        Memanggil LLM untuk menghasilkan analisis mendalam sebuah ide.
        
        Args:
            idea: Dictionary berisi informasi ide riset (idea_title, field, difficulty, abstract, dll)
            language: Bahasa output ('en' atau 'id')
        
        Returns:
            Dictionary dengan keys: outline, methodology, datasets, references, timeline, tools
        
        Raises:
            ValueError: Jika respons LLM tidak dapat di-parse atau field wajib tidak ada
        """
        # Build prompt berdasarkan bahasa
        language_instruction = ""
        if language == 'id':
            language_instruction = "\nTulis semua konten dalam Bahasa Indonesia akademis yang baku."

        prompt = f"""You are a senior academic advisor helping an Indonesian student evaluate a research idea.

Research Idea: {idea.get('idea_title', 'Untitled')}
Field: {idea.get('field', 'Unknown')}
Difficulty Level: {idea.get('difficulty', 'Unknown')}
Summary: {idea.get('abstract', 'No abstract provided')}

Generate a detailed deep dive analysis as a JSON object with these exact keys:
- "outline": array of 5-7 chapter/section titles for a thesis/dissertation
- "methodology": string describing the recommended research methodology (2-3 paragraphs)
- "datasets": array of 3-5 publicly available datasets with brief descriptions
- "references": array of 5 objects, each with "title" and "url" (ArXiv links preferred)
- "timeline": string estimating the project timeline with milestones
- "tools": array of 5-8 recommended tools/frameworks/libraries
{language_instruction}

Respond ONLY with valid JSON. No markdown, no explanation."""

        # Panggil LLM
        response_text = self.llm.call(prompt, retries=3, task_type="deep_dive")
        
        if not response_text:
            raise ValueError("LLM returned empty response")

        # Parse JSON response
        try:
            # Bersihkan markdown code blocks jika ada
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                # Hapus ```json atau ``` di awal dan ``` di akhir
                lines = cleaned.split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = '\n'.join(lines)
            
            response_data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}")

        # Validasi field wajib
        missing_fields = DeepDiveResponse.REQUIRED_FIELDS - set(response_data.keys())
        if missing_fields:
            raise ValueError(f"Missing required fields in LLM response: {missing_fields}")

        # Validasi tipe data
        if not isinstance(response_data.get('outline'), list):
            raise ValueError("Field 'outline' must be a list")
        if not isinstance(response_data.get('methodology'), str):
            raise ValueError("Field 'methodology' must be a string")
        if not isinstance(response_data.get('datasets'), list):
            raise ValueError("Field 'datasets' must be a list")
        if not isinstance(response_data.get('references'), list):
            raise ValueError("Field 'references' must be a list")
        if not isinstance(response_data.get('timeline'), str):
            raise ValueError("Field 'timeline' must be a string")
        if not isinstance(response_data.get('tools'), list):
            raise ValueError("Field 'tools' must be a list")

        # Validasi struktur references
        for ref in response_data['references']:
            if not isinstance(ref, dict):
                raise ValueError("Each reference must be a dictionary")
            if 'title' not in ref or 'url' not in ref:
                raise ValueError("Each reference must have 'title' and 'url' fields")

        return response_data

    # ─── Grounding verification (v1.5) ────────────────────────────────────────

    def verify_grounding(self, deep_dive_result: dict, source_text: str) -> Dict[str, Dict]:
        """
        Compare each Deep Dive section against the source paper's abstract
        using semantic similarity (Gemini embeddings) or token overlap fallback.

        Args:
            deep_dive_result: Output from generate() — dict with outline, methodology, etc.
            source_text: Reference text to ground against (typically inspiration paper abstract).

        Returns:
            Dict mapping section name to {"score": float, "level": "high"|"medium"|"low"}
            Score is 0.0-1.0. Levels configured via config.yaml thresholds section.
            Empty dict if source_text is missing or all comparisons fail.
        """
        if not source_text or not source_text.strip():
            return {}

        # Lazy import to avoid circular dependency at module load time
        from src.core.novelty_checker import NoveltyChecker

        checker = NoveltyChecker()
        use_semantic = (
            Config.LLM_PROVIDER == "gemini"
            and Config.LLM_API_KEY
        )

        # Sections to verify — flatten structured fields into comparable strings
        sections = self._extract_section_texts(deep_dive_result)
        if not sections:
            return {}

        # Embed source once (only used by semantic path)
        source_vec: Optional[List[float]] = None
        if use_semantic:
            try:
                source_vec = checker._embed(source_text[:2000])
            except Exception:
                use_semantic = False  # Fall back to Jaccard for all sections

        results: Dict[str, Dict] = {}
        for name, text in sections.items():
            if not text or not text.strip():
                continue

            score = 0.0
            try:
                if use_semantic and source_vec:
                    sect_vec = checker._embed(text[:2000])
                    score = checker._cosine_similarity(source_vec, sect_vec)
                else:
                    score = checker._jaccard_similarity(source_text, text)
            except Exception:
                # Graceful: fall back to Jaccard for this section only
                try:
                    score = checker._jaccard_similarity(source_text, text)
                except Exception:
                    score = 0.0

            results[name] = {
                "score": round(max(0.0, min(1.0, score)), 4),
                "level": self._score_to_level(score),
            }

        return results

    def _extract_section_texts(self, dd: dict) -> Dict[str, str]:
        """Convert Deep Dive sections into flat strings suitable for similarity comparison."""
        outline = dd.get("outline", [])
        datasets = dd.get("datasets", [])
        references = dd.get("references", [])
        tools = dd.get("tools", [])

        return {
            "outline":     " ".join(str(x) for x in outline) if isinstance(outline, list) else str(outline),
            "methodology": str(dd.get("methodology", "")),
            "datasets":    " ".join(str(x) for x in datasets) if isinstance(datasets, list) else str(datasets),
            "references":  " ".join(r.get("title", "") for r in references if isinstance(r, dict)),
            "timeline":    str(dd.get("timeline", "")),
            "tools":       " ".join(str(x) for x in tools) if isinstance(tools, list) else str(tools),
        }

    @staticmethod
    def _score_to_level(score: float) -> str:
        """Map similarity score to badge level (thresholds from config.yaml)."""
        if score >= Config.THRESHOLD_GROUNDING_HIGH:
            return "high"
        if score >= Config.THRESHOLD_GROUNDING_MEDIUM:
            return "medium"
        return "low"
