"""Provider-facing response schemas and strict offline validation."""
from __future__ import annotations

from math import isfinite
from .data import CONTEXTS, SOURCES

PROBABILITY_SCHEMA = {"type": "object", "properties": {"probability": {"type": "number", "minimum": 0, "maximum": 1}},
                      "required": ["probability"], "additionalProperties": False}
CELL_SCHEMA = {"type": "object", "properties": {
    "context": {"type": "string", "enum": list(CONTEXTS)},
    "source": {"type": "string", "enum": list(SOURCES)},
    "estimate": {"type": "number", "minimum": 0, "maximum": 1},
    "lower": {"type": "number", "minimum": 0, "maximum": 1},
    "upper": {"type": "number", "minimum": 0, "maximum": 1}},
    "required": ["context", "source", "estimate", "lower", "upper"], "additionalProperties": False}
MAP_SCHEMA = {"type": "object", "properties": {"cells": {"type": "array", "items": CELL_SCHEMA, "minItems": 9, "maxItems": 9}},
              "required": ["cells"], "additionalProperties": False}


def message_schema(max_chars):
    return {"type": "object", "properties": {"message": {"type": "string", "maxLength": max_chars}},
            "required": ["message"], "additionalProperties": False}


def batch_probe_schema(profile_ids):
    return {"type": "object", "properties": {"predictions": {
        "type": "array", "minItems": len(profile_ids), "maxItems": len(profile_ids),
        "items": {"type": "object", "properties": {
            "profile_id": {"type": "string", "enum": list(profile_ids)},
            "probability": {"type": "number", "minimum": 0, "maximum": 1}},
            "required": ["profile_id", "probability"], "additionalProperties": False}}},
        "required": ["predictions"], "additionalProperties": False}


def validate_response(value, schema):
    """No coercion, clipping, repair or retry. Invalid responses stop the run."""
    import jsonschema
    jsonschema.Draft202012Validator(schema).validate(value)
    if "cells" in value:
        cells = value["cells"]
        actual = {(c["context"], c["source"]) for c in cells}
        if actual != {(c, s) for c in CONTEXTS for s in SOURCES}:
            raise ValueError("Map must contain every context/source exactly once")
        for cell in cells:
            if not all(isfinite(cell[k]) for k in ("estimate", "lower", "upper")):
                raise ValueError("Non-finite map value")
            if not cell["lower"] <= cell["estimate"] <= cell["upper"]:
                raise ValueError("Map interval must contain estimate")
    if "probability" in value and not isfinite(value["probability"]):
        raise ValueError("Non-finite probability")
    if "predictions" in value:
        expected = set(schema["properties"]["predictions"]["items"]["properties"]["profile_id"]["enum"])
        if {x["profile_id"] for x in value["predictions"]} != expected:
            raise ValueError("Every probe profile must occur exactly once")
        if not all(isfinite(x["probability"]) for x in value["predictions"]):
            raise ValueError("Non-finite probe probability")

