"""可保存的创作参数。仅处理数据，不创建窗口，不执行配方中的代码。"""
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import tempfile


@dataclass(frozen=True)
class Parameter:
    key: str
    label: str
    kind: str
    default: object
    low: float = 0
    high: float = 0
    step: float = 1
    choices: tuple = ()


SPECIFICATIONS = {
    25: (
        Parameter("theme", "花色", "choice", 0, choices=("赤色彼岸", "蓝紫星梦", "鎏金月夜")),
        Parameter("speed", "绽放速度", "float", 1.0, .25, 2.5, .05),
        Parameter("star_count", "星空密度", "int", 115, 40, 180, 5),
        Parameter("curvature", "花瓣卷曲", "float", 1.0, .65, 1.35, .05),
        Parameter("wind", "微风强度", "float", 1.0, 0, 2, .1),
        Parameter("seed", "构图种子", "int", 2506, 0, 2147483647),
    ),
    26: (
        Parameter("theme", "星尘色彩", "choice", 0, choices=("玫瑰星尘", "冰蓝心跳", "香槟暮光")),
        Parameter("rate", "心跳速度", "float", 1.0, .45, 1.8, .05),
        Parameter("particle_count", "粒子数量", "int", 680, 240, 1000, 20),
        Parameter("size", "爱心大小", "float", 1.0, .75, 1.1, .05),
        Parameter("seed", "构图种子", "int", 260, 0, 2147483647),
    ),
}
TITLES = {25: "星空彼岸花", 26: "怦然心动"}
PRESETS = {
    25: (
        ("赤色星河", {}),
        ("蓝紫微风", {"theme": 1, "speed": .75, "star_count": 145, "curvature": 1.15, "wind": .6}),
        ("鎏金静夜", {"theme": 2, "speed": .55, "star_count": 80, "curvature": .85, "wind": .25}),
    ),
    26: (
        ("玫瑰心跳", {}),
        ("冰蓝呼吸", {"theme": 1, "rate": .65, "particle_count": 500, "size": .95}),
        ("香槟星尘", {"theme": 2, "rate": 1.2, "particle_count": 820, "size": 1.05}),
    ),
}
FORMAT = "turtle-gallery/recipe"
FORMAT_VERSION = 1
SCENE_VERSION = 1
MAX_RECIPE_BYTES = 65536


def parameter_specs(work_id):
    if type(work_id) is not int or work_id not in SPECIFICATIONS:
        raise ValueError("这款作品暂不支持创作配方。")
    return SPECIFICATIONS[work_id]


def default_parameters(work_id):
    return {spec.key: spec.default for spec in parameter_specs(work_id)}


def validate_parameters(work_id, values):
    specs = parameter_specs(work_id)
    if not isinstance(values, dict) or set(values) != {spec.key for spec in specs}:
        raise ValueError("配方参数不完整或含有未知参数，请使用对应版本的作品配方。")
    result = {}
    for spec in specs:
        value = values[spec.key]
        if spec.kind in ("int", "choice"):
            if type(value) is not int:
                raise ValueError(f"{spec.label}需要整数。")
            maximum = len(spec.choices) - 1 if spec.kind == "choice" else spec.high
            minimum = 0 if spec.kind == "choice" else spec.low
        else:
            if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
                raise ValueError(f"{spec.label}需要有效的数字。")
            minimum, maximum = spec.low, spec.high
        if not minimum <= value <= maximum:
            raise ValueError(f"{spec.label}应在 {minimum:g} 到 {maximum:g} 之间。")
        result[spec.key] = float(value) if spec.kind == "float" else value
    return result


def preset_parameters(work_id, index):
    values = default_parameters(work_id)
    if type(index) is not int or not 0 <= index < len(PRESETS[work_id]):
        raise ValueError("请选择已有的灵感预设。")
    values.update(PRESETS[work_id][index][1])
    return validate_parameters(work_id, values)


def make_recipe(work_id, parameters):
    return {"format": FORMAT, "version": FORMAT_VERSION, "work_id": work_id,
            "scene_version": SCENE_VERSION, "parameters": validate_parameters(work_id, parameters)}


def save_recipe(path, work_id, parameters):
    """Replace a recipe only after the complete new JSON has been written."""
    recipe = make_recipe(work_id, parameters)
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(recipe, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return recipe


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("配方包含重复字段，请检查文件。")
        result[key] = value
    return result


def load_recipe(path, expected_work_id=None):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_RECIPE_BYTES + 1)
    if len(raw) > MAX_RECIPE_BYTES:
        raise ValueError("配方文件过大，请选择海龟画廊导出的 JSON 配方。")
    try:
        data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("无法读取配方，请选择有效的 JSON 配方文件。") from exc
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError("这不是海龟画廊的创作配方。")
    if type(data.get("version")) is not int or data["version"] != FORMAT_VERSION:
        raise ValueError("暂不支持这个配方格式版本。")
    if type(data.get("scene_version")) is not int or data["scene_version"] != SCENE_VERSION:
        raise ValueError("配方对应的作品版本不同，请使用兼容版本。")
    work_id = data.get("work_id")
    parameter_specs(work_id)
    if expected_work_id is not None and work_id != expected_work_id:
        raise ValueError(f"这是「{TITLES[work_id]}」的配方，请在对应作品中载入。")
    return make_recipe(work_id, data.get("parameters"))
