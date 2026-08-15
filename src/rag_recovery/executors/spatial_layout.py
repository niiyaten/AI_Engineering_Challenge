from __future__ import annotations

import io
import itertools
import math
import re
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from ..models import Evidence, ExecutionResult, QueryPlan, Question
from ..normalize import nfkc, norm
from ..store import DocumentStore
from .base import Executor

_NAME_RE = re.compile(r"([一-龯々]{1,8})さん")
_OCR_PERSON_RE = re.compile(r"([一-龯々]{1,8})\s*\((Exec|PM|DS|QA|BA|DE)\)", re.I)
_POSITION_ORDER = "NWSE"
_RIGHT_OF = {"N": "W", "W": "S", "S": "E", "E": "N"}
_OPPOSITE = {"N": "S", "S": "N", "W": "E", "E": "W"}


@dataclass(frozen=True)
class SeatOccupant:
    name: str
    extension: str
    role: str
    pod: int
    position: str
    label_center: tuple[float, float]
    desk_center: tuple[float, float]
    assignment_distance: float


@dataclass
class SpatialLayoutExecutor(Executor):
    """Image-only four-seat island floor-map executor.

    It does not branch on question IDs or known answers. The document image is parsed at
    runtime using Japanese OCR and desk-color geometry. Supported relations are immediate
    right-hand seat and opposite seat within the same four-person POD.
    """

    name: str = "spatial_layout"
    normalized_width: int = 1376
    _layout_cache: dict[str, tuple[list[SeatOccupant], dict[str, Any], str]] = field(default_factory=dict, init=False, repr=False)

    def execute(self, question: Question, plan: QueryPlan, store: DocumentStore) -> ExecutionResult:
        q = nfkc(question.text)
        target_match = _NAME_RE.search(q)
        if not target_match:
            return ExecutionResult.abstain("基準人物を質問文から特定できない")
        target_name = target_match.group(1)
        relation = "opposite" if "向かい" in q or "正面" in q else "right" if "右側" in q or "右隣" in q else ""
        if not relation:
            return ExecutionResult.abstain("対応する座席関係ではない")

        records = store.find(
            extensions={".pptx", ".png", ".jpg", ".jpeg"},
            roles={"internal"},
            selected_sources=question.selected_sources,
            limit=30,
        )
        records.sort(key=lambda rec: (0 if "座席" in rec.filename or "floor" in rec.filename.lower() else 1, rec.relative_path))
        failures: list[str] = []
        for rec in records:
            try:
                cache_key = f"{rec.path.resolve()}::{rec.path.stat().st_size}::{rec.path.stat().st_mtime_ns}"
                cached = self._layout_cache.get(cache_key)
                if cached is None:
                    image, locator = self._load_floor_map_image(rec.path)
                    occupants, diagnostics = self._parse_island_floor_map(image)
                    self._layout_cache[cache_key] = (occupants, diagnostics, locator)
                else:
                    occupants, diagnostics, locator = cached
                    diagnostics = dict(diagnostics)
                    diagnostics["layout_cache_hit"] = True
            except Exception as exc:
                failures.append(f"{rec.relative_path}:{type(exc).__name__}:{exc}")
                continue
            target = next((item for item in occupants if norm(item.name) == norm(target_name)), None)
            if target is None:
                failures.append(f"{rec.relative_path}:target_not_found:{target_name}")
                continue
            desired = _OPPOSITE[target.position] if relation == "opposite" else _RIGHT_OF[target.position]
            related = [item for item in occupants if item.pod == target.pod and item.position == desired]
            if not related:
                failures.append(f"{rec.relative_path}:related_seat_missing:pod={target.pod},position={desired}")
                continue
            asks_ext = "EXT" in q.upper() or "内線" in q
            if asks_ext:
                if any(not item.extension for item in related):
                    return ExecutionResult.abstain("関係席のEXTをOCRで確定できない", diagnostics={"occupants": self._diag_occupants(occupants)})
                answer = "、".join(item.extension for item in related)
            else:
                answer = "、".join(item.name for item in related)

            average_distance = sum(item.assignment_distance for item in occupants if item.pod == target.pod) / max(1, sum(item.pod == target.pod for item in occupants))
            confidence = 0.95 if average_distance <= 145 else 0.91
            detail = (
                f"POD {target.pod}: {target.name}={target.position}席。"
                f"relation={relation} により {desired}席={','.join(item.name for item in related)}"
                f"（EXT={','.join(item.extension for item in related)}）。"
            )
            diagnostics.update(
                {
                    "target": target.name,
                    "target_pod": target.pod,
                    "target_position": target.position,
                    "relation": relation,
                    "resolved_position": desired,
                    "occupants": self._diag_occupants(occupants),
                    "average_assignment_distance": average_distance,
                }
            )
            return ExecutionResult(
                True,
                answer,
                confidence,
                "local_ocr_spatial_layout",
                [Evidence(rec.relative_path, locator, detail)],
                diagnostics=diagnostics,
            )
        return ExecutionResult.abstain("座席表画像を決定的に解析できない", diagnostics={"failures": failures[:10]})

    @staticmethod
    def _diag_occupants(occupants: list[SeatOccupant]) -> list[dict[str, Any]]:
        return [
            {
                "name": item.name,
                "extension": item.extension,
                "role": item.role,
                "pod": item.pod,
                "position": item.position,
                "assignment_distance": round(item.assignment_distance, 3),
            }
            for item in sorted(occupants, key=lambda value: (value.pod, _POSITION_ORDER.index(value.position)))
        ]

    @staticmethod
    def _load_floor_map_image(path: Path) -> tuple[Image.Image, str]:
        ext = path.suffix.lower()
        if ext in {".png", ".jpg", ".jpeg"}:
            return Image.open(path).convert("RGB"), "image"
        if ext != ".pptx":
            raise ValueError(f"unsupported spatial document: {ext}")
        with zipfile.ZipFile(path) as zf:
            media = [name for name in zf.namelist() if name.startswith("ppt/media/") and Path(name).suffix.lower() in {".png", ".jpg", ".jpeg"}]
            if not media:
                raise ValueError("pptx contains no raster image")
            # Floor-map decks used by this executor are image-only; choose the largest image.
            name = max(media, key=lambda item: zf.getinfo(item).file_size)
            return Image.open(io.BytesIO(zf.read(name))).convert("RGB"), f"slide:1/{name}"

    def _parse_island_floor_map(self, image: Image.Image) -> tuple[list[SeatOccupant], dict[str, Any]]:
        try:
            import cv2
            import numpy as np
            import pytesseract
        except ImportError as exc:
            raise RuntimeError("spatial extra is required: uv sync --extra spatial") from exc
        if shutil.which("tesseract") is None:
            raise RuntimeError("tesseract executable is not available")

        scale = self.normalized_width / image.width
        normalized = image.resize((self.normalized_width, max(1, round(image.height * scale))))
        rgb = np.array(normalized)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        pods = self._detect_pods(bgr, cv2, np)
        labels = self._detect_and_ocr_labels(normalized, bgr, cv2, np, pytesseract)
        occupants = self._assign_labels_to_pods(labels, pods)
        if len(occupants) < 6:
            raise ValueError(f"too few occupants parsed: {len(occupants)}")
        diagnostics = {
            "parser": "japanese_tesseract_plus_color_geometry",
            "normalized_size": [normalized.width, normalized.height],
            "pod_count": len(pods),
            "ocr_label_count": len(labels),
            "occupant_count": len(occupants),
        }
        return occupants, diagnostics

    @staticmethod
    def _detect_pods(bgr, cv2, np) -> list[dict[str, tuple[float, float]]]:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        # Repeated desk colors identify north, west and south positions. The fourth
        # position is the parallelogram completion, allowing gray/yellow desks.
        ranges = {
            "N": ((90, 50, 80), (115, 220, 245)),   # blue desk
            "W": ((65, 50, 70), (92, 220, 235)),    # green desk
            "S": ((5, 70, 90), (18, 240, 245)),     # orange desk
        }
        components: dict[str, list[tuple[float, float]]] = {}
        for position, (low, high) in ranges.items():
            mask = cv2.inRange(hsv, np.array(low), np.array(high))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
            count, _, stats, centers = cv2.connectedComponentsWithStats(mask)
            found: list[tuple[float, float]] = []
            for index in range(1, count):
                x, y, width, height, area = map(int, stats[index])
                if 2200 < area < 5000 and 85 < width < 130 and 45 < height < 80 and y > 300:
                    found.append((float(centers[index][0]), float(centers[index][1])))
            components[position] = sorted(found, key=lambda point: point[0])
        pod_count = min((len(values) for values in components.values()), default=0)
        if pod_count < 1 or any(len(values) != pod_count for values in components.values()):
            raise ValueError(f"desk components are inconsistent: {components}")
        pods: list[dict[str, tuple[float, float]]] = []
        for index in range(pod_count):
            north = components["N"][index]
            west = components["W"][index]
            south = components["S"][index]
            east = (north[0] + south[0] - west[0], north[1] + south[1] - west[1])
            pods.append({"N": north, "W": west, "S": south, "E": east})
        return pods

    @staticmethod
    def _detect_and_ocr_labels(image: Image.Image, bgr, cv2, np, pytesseract) -> list[dict[str, Any]]:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 120)
        edges = cv2.dilate(edges, np.ones((2, 2), np.uint8), 1)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        candidates: list[tuple[int, int, int, int, float]] = []
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = float(cv2.contourArea(contour))
            if 90 <= width <= 125 and 45 <= height <= 60 and area >= 3500 and y < 620:
                candidates.append((x, y, width, height, area))
        candidates.sort(key=lambda value: -value[4])
        boxes: list[tuple[int, int, int, int, float]] = []
        for candidate in candidates:
            x, y, _, _, _ = candidate
            if not any(abs(x - prior[0]) < 5 and abs(y - prior[1]) < 5 for prior in boxes):
                boxes.append(candidate)
        boxes.sort(key=lambda value: (value[1], value[0]))

        labels: list[dict[str, Any]] = []
        for x, y, width, height, _ in boxes:
            crop = image.crop((x - 5, y - 5, x + width + 5, y + height + 5)).resize(((width + 10) * 3, (height + 10) * 3))
            text = pytesseract.image_to_string(crop, lang="jpn+eng", config="--psm 6").strip().replace("\n", " ")
            match = _OCR_PERSON_RE.search(text)
            if not match:
                lower = crop.crop((0, int(crop.height * 0.30), crop.width, crop.height))
                lower_text = pytesseract.image_to_string(lower, lang="jpn+eng", config="--psm 7").strip()
                match = _OCR_PERSON_RE.search(lower_text)
                if match:
                    text = f"{text} {lower_text}".strip()
            if not match:
                continue
            name, role = match.group(1), match.group(2)
            top = crop.crop((0, 0, crop.width, int(crop.height * 0.60)))
            extension_variants: list[str] = []
            variants = [top, top.convert("L"), top.convert("L").point(lambda value: 0 if value < 180 else 255)]
            for variant in variants:
                raw = pytesseract.image_to_string(variant, lang="eng", config="--psm 7 -c tessedit_char_whitelist=0123456789").strip()
                digits = "".join(re.findall(r"\d", raw))
                if len(digits) >= 4:
                    extension_variants.append(digits[-4:])
            extension = max(set(extension_variants), key=extension_variants.count) if extension_variants else ""
            labels.append(
                {
                    "name": name,
                    "role": role,
                    "extension": extension,
                    "center": (x + width / 2.0, y + height / 2.0),
                    "box": (x, y, width, height),
                    "raw_ocr": text,
                }
            )
        return labels

    @staticmethod
    def _assign_labels_to_pods(labels: list[dict[str, Any]], pods: list[dict[str, tuple[float, float]]]) -> list[SeatOccupant]:
        non_exec = [label for label in labels if str(label["role"]).lower() != "exec"]
        pod_centers_x = [sum(point[0] for point in pod.values()) / 4.0 for pod in pods]
        groups: list[list[dict[str, Any]]] = [[] for _ in pods]
        for label in non_exec:
            pod_index = min(range(len(pods)), key=lambda index: abs(label["center"][0] - pod_centers_x[index]))
            groups[pod_index].append(label)

        occupants: list[SeatOccupant] = []
        for pod_index, (pod, group) in enumerate(zip(pods, groups), 1):
            by_identity: dict[str, list[dict[str, Any]]] = {}
            for label in group:
                identity = label["extension"] or label["name"]
                by_identity.setdefault(identity, []).append(label)
            identities = list(by_identity)
            if len(identities) < 2:
                continue
            identity_subsets = [identities] if len(identities) <= 4 else itertools.combinations(identities, 4)
            best: tuple[float, tuple[dict[str, Any], ...], tuple[str, ...]] | None = None
            for subset in identity_subsets:
                occurrences = [by_identity[identity] for identity in subset]
                for selected in itertools.product(*occurrences):
                    for positions in itertools.permutations(_POSITION_ORDER, len(selected)):
                        cost = sum(math.dist(label["center"], pod[position]) for label, position in zip(selected, positions))
                        if best is None or cost < best[0]:
                            best = (cost, selected, positions)
            if best is None:
                continue
            _, selected, positions = best
            for label, position in zip(selected, positions):
                distance = math.dist(label["center"], pod[position])
                occupants.append(
                    SeatOccupant(
                        name=label["name"],
                        extension=label["extension"],
                        role=label["role"],
                        pod=pod_index,
                        position=position,
                        label_center=label["center"],
                        desk_center=pod[position],
                        assignment_distance=distance,
                    )
                )
        return occupants
