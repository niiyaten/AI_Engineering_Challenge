from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..models import Evidence, ExecutionResult, QueryPlan, Question
from ..store import DocumentStore
from ..vision_client import OpenAICompatibleVisionClient
from .base import Executor


@dataclass
class VisionFallbackExecutor(Executor):
    client: OpenAICompatibleVisionClient
    name: str = "vision"
    max_files: int = 4
    max_pages: int = 8

    def execute(self, question: Question, plan: QueryPlan, store: DocumentStore) -> ExecutionResult:
        project = plan.project_hints[0] if plan.project_hints else ""
        filename = plan.filename_hints[0] if plan.filename_hints else ""
        records = store.find(
            project_hint=project,
            filename_hint=filename,
            extensions={".pdf", ".docx", ".pptx", ".xlsx", ".xlsm", ".png", ".jpg", ".jpeg"},
            selected_sources=question.selected_sources,
            limit=self.max_files,
        )
        if not records:
            return ExecutionResult.abstain("Vision対象資料を特定できない")
        with tempfile.TemporaryDirectory(prefix="rag-vision-") as td:
            render_root = Path(td)
            images: list[tuple[Path, str, str]] = []
            context_lines = []
            for rec in records:
                context_lines.append(f"- {rec.relative_path}")
                for unit in store.extract_text_units(rec)[:12]:
                    if unit.text.strip():
                        context_lines.append(f"  {unit.locator}: {unit.text[:500].replace(chr(10), ' ')}")
                images.extend(self._render(rec, render_root, store))
                if len(images) >= self.max_pages:
                    break
            images = images[: self.max_pages]
            if not images:
                return ExecutionResult.abstain("資料を画像化できない")
            answer = self.client.answer(question.text, images, "\n".join(context_lines))
        if answer.answer in {"", "わからない", "わかりません"} or answer.confidence < 0.75:
            return ExecutionResult.abstain("Visionモデルが一意回答を返さない", diagnostics={"vision_confidence": answer.confidence})
        source = answer.source if any(answer.source == r.relative_path for r in records) else images[0][1]
        locator = answer.locator or images[0][2]
        return ExecutionResult(True, answer.answer, min(.92, answer.confidence), "openai_compatible_vision_fallback", [Evidence(source, locator, answer.evidence)], diagnostics={"vision_confidence": answer.confidence})

    def _render(self, rec, render_root: Path, store: DocumentStore):
        if rec.extension in {".png", ".jpg", ".jpeg"}:
            target = render_root / rec.path.name
            shutil.copy2(rec.path, target)
            return [(target, rec.relative_path, "image")]
        pdf = rec.path
        if rec.extension != ".pdf":
            outdir = render_root / f"office_{abs(hash(rec.relative_path)) & 0xffffffff:x}"
            outdir.mkdir(parents=True, exist_ok=True)
            try:
                subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(rec.path)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                return []
            pdf = outdir / f"{rec.path.stem}.pdf"
            if not pdf.exists():
                return []
        prefix = render_root / f"page_{abs(hash(rec.relative_path)) & 0xffffffff:x}"
        try:
            subprocess.run(["pdftoppm", "-png", "-r", "120", "-f", "1", "-l", str(self.max_pages), str(pdf), str(prefix)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return []
        outputs = sorted(render_root.glob(f"{prefix.name}-*.png"))
        return [(path, rec.relative_path, f"page:{i+1}") for i, path in enumerate(outputs)]
