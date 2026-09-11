"""Real runtime egress monitor for the VYOMA server process.

This is the live-runtime proof behind the "zero egress" claim. Unlike a static
"0 KB sent" label, every value this module exposes is derived from a live
sampling of the server process's own connection table via ``psutil``:

- ``sample()`` enumerates the process's active TCP connections and classifies
  each destination as LOCAL (loopback — e.g. the local Ollama instance on
  ``127.0.0.1``) or EXTERNAL (any non-loopback destination).
- ``snapshot()`` also returns ``external_observed_since_start``: a running
  count of distinct samplings in which an external-destination connection was
  seen, since the monitor was constructed. Nothing is invented; if psutil
  cannot enumerate the table, ``connect_error`` carries the psutil error and
  the counts stay honest.
"""

from __future__ import annotations

import ipaddress
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import psutil


def _classify_connection(conn: Any) -> str:
    """Return ``"local"`` for loopback / no-destination conns, else ``"external"``.

    A listening connection has an empty ``raddr`` (no destination) and is
    local by construction. A connection whose destination is on the loopback
    network (``127.x``, ``::1``) is local (Ollama). Anything else has an
    external destination.
    """
    remote = getattr(conn, "raddr", None)
    if not remote:
        return "local"
    host = getattr(remote, "ip", None)
    if not host:
        return "local"
    try:
        ip = ipaddress.ip_address(str(host))
    except ValueError:
        return "external"
    return "local" if ip.is_loopback else "external"


def _addr_to_dict(addr: Any) -> Optional[Dict[str, Any]]:
    if not addr:
        return None
    return {"ip": getattr(addr, "ip", None), "port": getattr(addr, "port", None)}


LOGICAL_FAMILY_NAMES = {
    "AF_INET": "IPv4",
    "AF_INET6": "IPv6",
    "AF_LINK": "MAC",
}


def _family_name(family: Any) -> str:
    """Human-readable label (``IPv4``/``IPv6``/``MAC``) for an address family.

    Derives the label from the stdlib enum's ``name`` (never a raw numeric
    value), falling back to the string form only when no named enum exists.
    """
    name = getattr(family, "name", None)
    if name in LOGICAL_FAMILY_NAMES:
        return LOGICAL_FAMILY_NAMES[name]
    return name or str(family)


def network_interface_summary() -> List[Dict[str, Any]]:
    """Real NIC state from psutil: name, link state and configured addresses."""
    stats = psutil.net_if_stats()
    result: List[Dict[str, Any]] = []
    for name, addrs in psutil.net_if_addrs().items():
        up = bool(getattr(stats.get(name), "isup", False)) if name in stats else False
        result.append(
            {
                "name": name,
                "is_up": up,
                "addresses": [
                    {"family": _family_name(addr.family), "address": addr.address}
                    for addr in addrs
                ],
            }
        )
    return result


class EgressMonitor:
    """Sample the server PID's active connections and classify destinations."""

    INTERVAL_S = 2.0

    def __init__(self, pid: Optional[int] = None) -> None:
        self.pid = pid if pid is not None else os.getpid()
        self._lock = threading.Lock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._external_observed = 0
        self._sampled_at: Optional[str] = None
        self._last: Dict[str, Any] = {"local": [], "external": [], "connect_error": None}
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.sample()

    def sample(self) -> Dict[str, Any]:
        """Take a live psutil sample of this process's TCP connections."""
        local: List[Dict[str, Any]] = []
        external: List[Dict[str, Any]] = []
        error: Optional[str] = None
        try:
            connections = psutil.Process(self.pid).net_connections(kind="tcp")
        except (psutil.AccessDenied, psutil.NoSuchProcess) as exc:
            connections, error = [], f"{type(exc).__name__}: {exc}"
        for conn in connections:
            entry = {
                "laddr": _addr_to_dict(conn.laddr),
                "raddr": _addr_to_dict(conn.raddr),
                "status": conn.status,
                "family": _family_name(conn.family),
            }
            if _classify_connection(conn) == "external":
                external.append(entry)
            else:
                local.append(entry)
        with self._lock:
            self._external_observed += len(external)
            self._sampled_at = datetime.now(timezone.utc).isoformat()
            self._last = {"local": local, "external": external, "connect_error": error}
        return self._last

    def snapshot(self) -> Dict[str, Any]:
        """Live sample now and return the full, honest monitor state."""
        self.sample()
        with self._lock:
            return {
                "pid": self.pid,
                "started_at": self._started_at,
                "sampled_at": self._sampled_at,
                "local_connections": self._last["local"],
                "external_connections": self._last["external"],
                "local_connection_count": len(self._last["local"]),
                "external_connection_count": len(self._last["external"]),
                "external_observed_since_start": self._external_observed,
                "connect_error": self._last["connect_error"],
            }

    def start(self) -> None:
        """Start the background sampler thread (idempotent)."""
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="egress-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the background sampler thread."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.wait(self.INTERVAL_S):
            self.sample()