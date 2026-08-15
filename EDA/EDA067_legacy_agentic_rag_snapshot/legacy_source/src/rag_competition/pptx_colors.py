from __future__ import annotations

import colorsys
import math
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"a": A_NS, "p": P_NS}


def _tag(name: str) -> str:
    return f"{{{A_NS}}}{name}"


def _rgb(value: str) -> tuple[int, int, int] | None:
    value = re.sub(r"[^0-9a-fA-F]", "", value or "")
    if len(value) == 8:
        value = value[-6:]
    if len(value) != 6:
        return None
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _apply_transforms(rgb: tuple[int, int, int], element: ElementTree.Element | None) -> tuple[int, int, int]:
    if element is None:
        return rgb
    values = {child.tag.rsplit("}", 1)[-1]: int(child.attrib.get("val", "0")) for child in list(element) if child.tag.startswith("{" + A_NS + "}")}
    channels = [value / 255.0 for value in rgb]
    if "tint" in values:
        factor = values["tint"] / 100000.0
        channels = [channel + (1.0 - channel) * factor for channel in channels]
    if "shade" in values:
        channels = [channel * values["shade"] / 100000.0 for channel in channels]
    if "lumMod" in values:
        channels = [channel * values["lumMod"] / 100000.0 for channel in channels]
    if "lumOff" in values:
        channels = [channel + values["lumOff"] / 100000.0 for channel in channels]
    return tuple(max(0, min(255, round(channel * 255))) for channel in channels)


def normalized_color_name(rgb: tuple[int, int, int] | None) -> tuple[str, str, float]:
    if rgb is None:
        return "unknown", "unknown", float("inf")
    red, green, blue = [value / 255.0 for value in rgb]
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    if value < 0.12:
        name = "black"
    elif saturation < 0.12 and value > 0.9:
        name = "white"
    elif saturation < 0.18:
        name = "gray"
    else:
        degrees = hue * 360
        if degrees < 15 or degrees >= 345: name = "red"
        elif degrees < 45: name = "orange"
        elif degrees < 75: name = "yellow"
        elif degrees < 165: name = "green"
        elif degrees < 255: name = "blue"
        elif degrees < 300: name = "purple"
        elif degrees < 345: name = "pink"
        else: name = "brown"
    references = {"red": (220, 40, 40), "orange": (240, 140, 30), "yellow": (240, 220, 30), "green": (50, 170, 70), "blue": (50, 100, 210), "purple": (130, 70, 170), "pink": (230, 100, 160), "brown": (130, 80, 40), "gray": (128, 128, 128), "black": (0, 0, 0), "white": (255, 255, 255)}
    nearest, nearest_rgb = min(references.items(), key=lambda item: math.sqrt(sum((rgb[i] - item[1][i]) ** 2 for i in range(3))))
    distance = math.sqrt(sum((rgb[i] - nearest_rgb[i]) ** 2 for i in range(3)))
    return name, nearest, distance


def _theme_colors(archive: zipfile.ZipFile) -> dict[str, tuple[int, int, int]]:
    result: dict[str, tuple[int, int, int]] = {}
    for name in archive.namelist():
        if not name.startswith("ppt/theme/") or not name.endswith(".xml"):
            continue
        root = ElementTree.fromstring(archive.read(name))
        scheme = root.find(".//a:clrScheme", NS)
        if scheme is None:
            continue
        for child in list(scheme):
            color = next(iter(child), None)
            if color is None:
                continue
            value = color.attrib.get("lastClr") or color.attrib.get("val", "")
            parsed = _rgb(value)
            if parsed:
                result[child.tag.rsplit("}", 1)[-1]] = parsed
    return result


def resolve_color(element: ElementTree.Element | None, themes: dict[str, tuple[int, int, int]], source: str) -> dict[str, Any]:
    result: dict[str, Any] = {"raw_color_type": "", "raw_color_value": "", "scheme_color_name": "", "theme_color_value": "", "color_transforms": [], "resolved_rgb": "", "resolved_argb": "", "normalized_color_name": "unknown", "nearest_reference_color": "unknown", "color_distance": None, "color_match_threshold": 110.0, "color_source": source, "resolution_status": "not_specified"}
    if element is None:
        return result
    fill = element.find("a:solidFill", NS)
    if fill is None:
        return result
    color = next(iter(fill), None)
    if color is None:
        result["resolution_status"] = "not_resolved"
        return result
    kind = color.tag.rsplit("}", 1)[-1]
    raw_value = color.attrib.get("val", "") or color.attrib.get("lastClr", "")
    result["raw_color_type"] = kind
    result["raw_color_value"] = raw_value
    result["scheme_color_name"] = raw_value if kind == "schemeClr" else ""
    base = _rgb(raw_value) if kind in {"srgbClr", "sysClr", "prstClr", "scrgbClr"} else themes.get(raw_value)
    if kind == "sysClr":
        base = _rgb(color.attrib.get("lastClr", "")) or base
    if kind == "schemeClr":
        result["theme_color_value"] = "".join(f"{value:02X}" for value in base) if base else ""
    transforms = [{child.tag.rsplit("}", 1)[-1]: child.attrib.get("val", "")} for child in list(color)]
    result["color_transforms"] = transforms
    final = _apply_transforms(base, color) if base else None
    if final is None:
        result["resolution_status"] = "not_resolved"
        return result
    name, nearest, distance = normalized_color_name(final)
    result.update({"resolved_rgb": "#%02X%02X%02X" % final, "resolved_argb": "FF%02X%02X%02X" % final, "normalized_color_name": name, "nearest_reference_color": nearest, "color_distance": round(distance, 4), "resolution_status": "resolved", "base_rgb": "#%02X%02X%02X" % base, "applied_transforms": transforms})
    return result


def slide_color_map(path: Path) -> dict[int, list[list[dict[str, Any]]]]:
    """PPTXの各スライドで、shape・paragraph・runに対応するraw色を抽出する。"""
    result: dict[int, list[list[dict[str, Any]]]] = {}
    with zipfile.ZipFile(path) as archive:
        themes = _theme_colors(archive)
        for name in archive.namelist():
            match = re.match(r"ppt/slides/slide(\d+)\.xml$", name)
            if not match:
                continue
            root = ElementTree.fromstring(archive.read(name)); shapes: list[list[dict[str, Any]]] = []
            for shape in root.findall(".//p:sp", NS):
                tx_body = shape.find("p:txBody", NS)
                if tx_body is None:
                    continue
                shape_fill = resolve_color(shape.find("p:spPr", NS), themes, "shape_default")
                shape_default = tx_body.find("a:lstStyle/a:defPPr/a:defRPr", NS)
                paragraphs: list[dict[str, Any]] = []
                for paragraph in tx_body.findall("a:p", NS):
                    paragraph_default = paragraph.find("a:pPr/a:defRPr", NS) or shape_default
                    runs: list[dict[str, Any]] = []
                    for run in paragraph.findall("a:r", NS):
                        props = run.find("a:rPr", NS)
                        color = resolve_color(props, themes, "run_explicit")
                        if color["resolution_status"] == "not_specified":
                            color = resolve_color(paragraph_default, themes, "paragraph_default" if paragraph.find("a:pPr/a:defRPr", NS) is not None else "shape_default")
                        color["shape_fill_rgb"] = shape_fill.get("resolved_rgb", "")
                        color["shape_fill_normalized_name"] = shape_fill.get("normalized_color_name", "unknown")
                        color["shape_fill_source"] = shape_fill.get("color_source", "unknown")
                        runs.append(color)
                    paragraphs.append(runs)
                shapes.append(paragraphs)
            result[int(match.group(1))] = shapes
    return result
