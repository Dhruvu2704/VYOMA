"""Active-permit overlap EVIDENCE for the KAVACH plant-safety layer.

The backend supplies only evidence: which ACTIVE permits overlap the
submitted permit in time and area. The authoritative conflict decision is
made by the existing Role 3 deterministic rules.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional


def permit_to_active_permit(permit: Any) -> Dict[str, Any]:
    """Convert a backend Permit row into the shared ActivePermit shape."""
    location: List[str] = []
    for field in ("plant", "equipment"):
        value = getattr(permit, field, None)
        if value:
            location.append(str(value))
    return {
        "permit_id": permit.permit_id,
        "location": location,
        "start_time": _iso(getattr(permit, "valid_from", None)),
        "end_time": _iso(getattr(permit, "valid_to", None)),
        "status": permit.status,
    }


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return "" if value is None else str(value)


def _parse_time(value: str) -> Optional[datetime]:
    text = (value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _overlaps(
    start_a: Optional[datetime],
    end_a: Optional[datetime],
    start_b: Optional[datetime],
    end_b: Optional[datetime],
) -> bool:
    if not (start_a and end_a and start_b and end_b):
        return False
    return start_a < end_b and start_b < end_a


def _shares_area(
    task_locations: List[str],
    permit_locations: List[str],
) -> bool:
    return bool(set(task_locations) & set(permit_locations))


def build_overlap_check(
    ptw: Mapping[str, Any],
    active_permits: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build the ``overlap_check`` evidence envelope expected by Role 3.

    A permit is evidence of overlap when its time window overlaps the
    submitted PTW window AND it shares at least one location area with the
    PTW. ``same_area_active`` is reported whenever any active permit shares
    the area, regardless of the window.
    """
    task_start = _parse_time(str(ptw.get("start_time") or ""))
    task_end = _parse_time(str(ptw.get("end_time") or ""))
    task_locations = list(ptw.get("location") or [])

    overlapping: List[str] = []
    same_area_active = False

    for permit in active_permits:
        if str(permit.get("status", "")).upper() != "ACTIVE":
            continue
        area = _shares_area(
            task_locations,
            list(permit.get("location") or []),
        )
        window = _overlaps(
            task_start,
            task_end,
            _parse_time(str(permit.get("start_time") or "")),
            _parse_time(str(permit.get("end_time") or "")),
        )
        if area:
            same_area_active = True
        if area and window:
            overlapping.append(str(permit["permit_id"]))

    return {
        "overlapping_permits": overlapping,
        "same_area_active": same_area_active,
    }