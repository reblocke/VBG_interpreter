"""Reserved screening contract; no owner-approved categorical threshold."""


def screening_result() -> dict[str, object]:
    return {
        "status": "NOT_CONFIGURED",
        "values": {},
        "units": {},
        "input_origins": {},
        "output_provenance": "NONE",
        "method_id": None,
        "evidence_tier": "NOT_CONFIGURED",
        "limitations": ["No owner-approved PvCO2 screening threshold is configured."],
    }
