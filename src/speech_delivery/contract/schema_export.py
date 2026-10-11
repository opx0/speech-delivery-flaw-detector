"""Export the contract as one JSON Schema bundle. `make contract` compiles it to TypeScript."""

import json
from pathlib import Path
from typing import Any, cast

from pydantic import TypeAdapter
from pydantic.json_schema import GenerateJsonSchema

from .dataset import DatasetManifest
from .jobs import AnalyzeOptions, JobEvent, LibraryEntry
from .report import Report
from .rubric import RubricWeights

ROOTS: dict[str, TypeAdapter[Any]] = {
    "AnalyzeOptions": TypeAdapter(AnalyzeOptions),
    "DatasetManifest": TypeAdapter(DatasetManifest),
    "JobEvent": TypeAdapter(JobEvent),
    "LibraryEntry": TypeAdapter(LibraryEntry),
    "Report": TypeAdapter(Report),
    "RubricWeights": TypeAdapter(RubricWeights),
}


def _drop_property_titles(node: object) -> None:
    """Pydantic titles every property ("First", "End"), which json2ts turns into alias types
    that collide across models. Model titles stay, so interfaces keep their class names."""
    if isinstance(node, dict):
        mapping = cast("dict[str, Any]", node)
        properties = mapping.get("properties")
        if isinstance(properties, dict):
            for schema in cast("dict[str, Any]", properties).values():
                if isinstance(schema, dict):
                    cast("dict[str, Any]", schema).pop("title", None)
        for child in mapping.values():
            _drop_property_titles(child)
    elif isinstance(node, list):
        for child in cast("list[Any]", node):
            _drop_property_titles(child)


def build_bundle() -> dict[str, Any]:
    generator = GenerateJsonSchema(ref_template="#/$defs/{model}")
    inputs = [(name, "serialization", adapter.core_schema) for name, adapter in ROOTS.items()]
    by_key, definitions = generator.generate_definitions(inputs)  # type: ignore[arg-type]
    bundle: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Contract",
        "type": "object",
        "additionalProperties": False,
        "required": list(ROOTS),
        "properties": {name: by_key[(name, "serialization")] for name in ROOTS},
        "$defs": definitions,
    }
    _drop_property_titles(bundle)
    return bundle


def render_bundle() -> str:
    return json.dumps(build_bundle(), indent=2, sort_keys=True) + "\n"


def write_bundle(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_bundle(), encoding="utf-8")
