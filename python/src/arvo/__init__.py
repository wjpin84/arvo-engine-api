"""Arvo's research from Python.

    import arvo

    engine = arvo.connect()
    for plan in engine.strategies():
        print(plan.name, plan.premise)

    found = engine.run_study("AAPL.RH", "sma_cross", author="script:first-look")
    print(found.verdict, found.read_this_first)
    for item in found.advice:
        print(item.severity, item.finding)

    prices = engine.bars("AAPL.RH")

This talks to a running ``arvo-engine`` through its research API (ADR-0018),
which reads research memory and runs research. Nothing here fetches data,
touches a credential or places an order, and nothing can: the API has no call
that would.

Every run needs an ``author``. It is saved as that author's finding and held to
the no-skill bar for **everything that author has run**, so a script that
tries configurations until one passes does not make it pass. Read ``verdict``,
``read_this_first`` and ``advice`` before any number in ``detail``.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import grpc

# The contract is split by domain (arvo-engine-api): one package per subject,
# holding its models and its views, with the services apart from them. `pb`
# keeps its old name so the rest of this module reads the same.
from arvo.common.v1 import models_pb2 as common
from arvo.research.v1 import models_pb2 as research
from arvo.services.v1 import research_pb2_grpc as rpc


class _Pb:
    """The shapes this client sends, from whichever package defines them."""

    Empty = common.Empty
    AttachRequest = research.AttachRequest
    FindingId = research.FindingId
    LedgerTrade = research.LedgerTrade
    Point = research.Point
    ReportRequest = research.ReportRequest
    RunRequest = research.RunRequest


pb = _Pb()

__all__ = [
    "Advice",
    "ArvoError",
    "Attachment",
    "Engine",
    "Finding",
    "FindingSummary",
    "Instrument",
    "Strategy",
    "connect",
    "default_root",
]

DAILY = "1day"
"""The interval name of daily bars, as the engine spells it."""

_SAFE_INSTRUMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ArvoError(RuntimeError):
    """A call the engine refused or could not complete, with its reason."""

    def __init__(self, message: str, code: str = "") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Strategy:
    name: str
    label: str
    interval: str
    premise: str
    ranks_a_set: bool


@dataclass(frozen=True)
class Instrument:
    id: str
    interval: str
    start: str
    end: str


@dataclass(frozen=True)
class FindingSummary:
    id: str
    kind: str
    subject: str
    verdict: str
    recorded_at: str
    author: str
    """The agent or script that ran it; empty for a person."""
    strategy: str = ""
    """Which rule or ruleset ran, by the name ``strategies()`` shows."""
    code_commit: str = ""
    """The engine build that produced it: a git commit, ``-dirty`` when the
    tree had uncommitted changes, ``unknown`` outside a checkout, empty for a
    finding recorded before builds were stamped."""
    ruleset_hash: str = ""
    """The ruleset document's hash at run time, when the strategy was a
    ruleset rather than a shipped rule. Two findings with different hashes
    measured different rules, whatever the ruleset is called."""


@dataclass(frozen=True)
class Advice:
    severity: str
    finding: str
    action: str
    evidence: str


@dataclass(frozen=True)
class Attachment:
    """One file kept with a finding: bytes stored once by content hash."""

    name: str
    media_type: str
    hash: str
    bytes: int
    added_at: str


@dataclass(frozen=True)
class Finding:
    id: str
    kind: str
    subject: str
    verdict: str
    recorded_at: str
    author: str
    read_this_first: str
    """How far the verdict may be read. Read before any number."""
    reasons: list[str]
    advice: list[Advice]
    strategy: str = ""
    code_commit: str = ""
    ruleset_hash: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    """The numbers, which differ by kind: ``search`` and ``out_of_sample`` for
    a study, ``combined`` for a walk-forward, ``pooled`` for a panel."""
    attachments: list[Attachment] = field(default_factory=list)
    """Files kept with it, in the order they were attached."""


def default_root() -> Path:
    """The Arvo app data directory, ``%APPDATA%/com.arvo.desktop``."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise ArvoError("APPDATA is not set; pass the Arvo app data directory to connect()")
    return Path(appdata) / "com.arvo.desktop"


def connect(root: str | os.PathLike[str] | None = None) -> Engine:
    """Connects to the engine running for this app data directory.

    Reads ``engine.json``, which the engine writes when it starts. Raises
    :class:`ArvoError` when no engine has written one.
    """
    base = Path(root) if root is not None else default_root()
    try:
        found = json.loads((base / "engine.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ArvoError(
            f"no engine.json in {base}; start arvo-engine first"
        ) from None
    return Engine(base, found["address"], found["token"])


class Engine:
    """One engine's research API, and read-only access to its bar library."""

    def __init__(self, root: Path, address: str, token: str) -> None:
        self.root = root
        # Room for a figure or a trades table attached to a finding; the
        # engine accepts the same.
        limit = 64 << 20
        self._channel = grpc.insecure_channel(
            address,
            options=[("grpc.max_send_message_length", limit), ("grpc.max_receive_message_length", limit)],
        )
        self._stub = rpc.ResearchStub(self._channel)
        self._metadata = (("authorization", f"Bearer {token}"),)

    def close(self) -> None:
        self._channel.close()

    def __enter__(self) -> Engine:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _call(self, method: Any, request: Any) -> Any:
        try:
            return method(request, metadata=self._metadata)
        except grpc.RpcError as err:
            code = err.code().name if hasattr(err, "code") else ""
            details = err.details() if hasattr(err, "details") else str(err)
            raise ArvoError(details or code, code) from None

    def strategies(self) -> list[Strategy]:
        """The rules Arvo can test."""
        reply = self._call(self._stub.ListStrategies, pb.Empty())
        return [
            Strategy(s.name, s.label, s.interval, s.premise, s.ranks_a_set)
            for s in reply.strategies
        ]

    def rank_findings(self, *, rule: str | None = None, instrument: str | None = None) -> Any:
        """The leaderboard (#226): every comparable finding in the one order
        Arvo ranks by. Supported under the conservative cost tier first, by
        mean profit per trade under that tier; then Supported under the stated
        costs where the tier was never measured; then everything else. Ties by
        drawdown, then trades. Returns the ``Ranking`` message: ``rows`` and
        ``notes``."""
        request = research.RankRequest()
        if rule is not None:
            request.rule = rule
        if instrument is not None:
            request.instrument = instrument
        return self._call(self._stub.RankFindings, request)

    def instruments(self) -> list[Instrument]:
        """Instruments with bars in the library, by interval and date range."""
        reply = self._call(self._stub.ListInstruments, pb.Empty())
        return [Instrument(i.id, i.interval, getattr(i, "from"), i.to) for i in reply.instruments]

    def findings(self) -> list[FindingSummary]:
        """Every finding in research memory."""
        reply = self._call(self._stub.ListFindings, pb.Empty())
        return [
            FindingSummary(
                f.id, f.kind, f.subject, f.verdict, f.recorded_at, f.author,
                f.strategy, f.code_commit, f.ruleset_hash,
            )
            for f in reply.findings
        ]

    def finding(self, id: str) -> Finding:
        """One finding: verdict, how far to read it, reasons, advice, numbers."""
        return _finding(self._call(self._stub.OpenFinding, pb.FindingId(id=id)))

    def run_study(self, instrument: str, strategy: str, *, author: str) -> Finding:
        """Searches ``strategy``'s grid on ``instrument``, chooses in-sample and
        judges out-of-sample. Saved as ``author``'s finding and deflated against
        everything ``author`` has run."""
        request = pb.RunRequest(instrument=instrument, strategy=strategy, author=author, origin=_caller())
        return _finding(self._call(self._stub.RunStudy, request))

    def run_walk_forward(self, instrument: str, strategy: str, *, author: str) -> Finding:
        """Re-selects on a rolling schedule across the whole history and judges
        the stitched out-of-sample record. Slower than :meth:`run_study`."""
        request = pb.RunRequest(instrument=instrument, strategy=strategy, author=author, origin=_caller())
        return _finding(self._call(self._stub.RunWalkForward, request))

    def record(
        self,
        *,
        author: str,
        hypothesis: str,
        claim: str,
        instrument: str,
        window: tuple[str, str],
        interval: str,
        dataset: tuple[str, str],
        strategy: str,
        engine: str,
        curve: Sequence[tuple[Any, float]],
        ledger: Sequence[dict[str, Any]] = (),
        benchmark_curve: Sequence[tuple[Any, float]] | None = None,
        params: dict[str, float] | None = None,
        costs_bps: tuple[float, float] = (0.0, 0.0),
        per_fill: float = 0.0,
        stop_atr_multiple: float | None = None,
        starting_cash: float = 0.0,
        adjustment: str = "split",
        trials: int | None = None,
    ) -> Finding:
        """Records a result this script computed itself, judged by Arvo.

        What a run produces, before anyone concludes anything from it: the
        experiment as data, the strategy's equity ``curve`` and trade
        ``ledger``, a ``benchmark_curve`` when there is one, and how many
        ``trials`` the whole search has run. Arvo computes the verdict from
        that with the criteria a study uses. There is no argument for a
        verdict, a metric or a p-value, on purpose.

        ``curve`` and ``benchmark_curve`` are ``(when, equity)`` pairs, where
        ``when`` is a ``datetime``, a ``date`` or a string like
        ``2026-01-31T09:30:00``. ``ledger`` rows are dicts with ``opened``,
        ``closed`` (omit while open), ``direction`` (``long``/``short``),
        ``quantity``, ``entry``, ``exit``, ``pnl``, ``commission`` and
        ``exit_reason`` (``signal``, ``stop``, ``halted``, ``expired``,
        ``still_open``), and optionally what the rule saw when it entered:
        ``rule`` (the condition, in words), ``signal`` (the value it was
        judged on), ``regime`` and ``asked`` (the quantity before the gate). ``dataset`` is ``(id, version)``, the version being
        a content hash of what the engine read. Without a benchmark the
        finding is Inconclusive: a return with nothing to beat is not a
        result.
        """
        trades = [
            pb.LedgerTrade(
                instrument=str(row.get("instrument", "")),
                opened=_when(row["opened"]),
                closed=_when(row["closed"]) if row.get("closed") else "",
                direction=str(row.get("direction", "long")),
                quantity=float(row.get("quantity", 0.0)),
                entry=float(row.get("entry", 0.0)),
                pnl=float(row.get("pnl", 0.0)),
                commission=float(row.get("commission", 0.0)),
                exit_reason=str(row.get("exit_reason", "signal")),
                **({"exit": float(row["exit"])} if row.get("exit") is not None else {}),
                **({"rule": str(row["rule"])} if row.get("rule") is not None else {}),
                **({"signal": float(row["signal"])} if row.get("signal") is not None else {}),
                **({"regime": str(row["regime"])} if row.get("regime") is not None else {}),
                **({"asked": float(row["asked"])} if row.get("asked") is not None else {}),
            )
            for row in ledger
        ]
        request = pb.ReportRequest(
            author=author,
            origin=_caller(),
            hypothesis_id=hypothesis,
            claim=claim,
            instrument=instrument,
            interval=interval,
            dataset_id=dataset[0],
            dataset_version=dataset[1],
            adjustment=adjustment,
            strategy=strategy,
            params=dict(params or {}),
            commission_bps=costs_bps[0],
            slippage_bps=costs_bps[1],
            per_fill=per_fill,
            starting_cash=starting_cash,
            engine=engine,
            strategy_curve=[pb.Point(at=_when(at), equity=float(equity)) for at, equity in curve],
            ledger=trades,
            benchmark_curve=[pb.Point(at=_when(at), equity=float(equity)) for at, equity in (benchmark_curve or [])],
            **({"trials": int(trials)} if trials is not None else {}),
            **({"stop_atr_multiple": float(stop_atr_multiple)} if stop_atr_multiple is not None else {}),
        )
        # `from` is a keyword in Python; the field is set by name.
        setattr(request, "from", window[0])
        request.to = window[1]
        return _finding(self._call(self._stub.RecordFinding, request))

    def attach(
        self,
        finding_id: str,
        path: str | os.PathLike[str] | None = None,
        *,
        data: bytes | None = None,
        name: str | None = None,
        media_type: str | None = None,
    ) -> list[Attachment]:
        """Keeps a file with a finding: a report, a figure, the trades.

        Give a ``path`` to read, or ``data`` with a ``name``. The bytes are
        stored once by content hash and the finding lists them; attaching the
        same file under the same name again changes nothing. Returns every
        attachment the finding now has. ``media_type`` is guessed from the
        name when not given.
        """
        if path is not None:
            file = Path(path)
            payload = file.read_bytes()
            name = name or file.name
        elif data is not None:
            payload = data
        else:
            raise ArvoError("attach needs a path or data")
        if not name:
            raise ArvoError("attach needs a name for the file")
        if media_type is None:
            media_type = _MEDIA_TYPES.get(Path(name).suffix.lower(), "application/octet-stream")
        request = pb.AttachRequest(finding_id=finding_id, name=name, media_type=media_type, data=payload)
        reply = self._call(self._stub.AttachFile, request)
        return [_attachment(a) for a in reply.attachments]

    def bars(self, instrument: str, interval: str = DAILY) -> Any:
        """The library's bars for ``instrument`` as a pandas DataFrame indexed
        by time, read straight from the engine's files.

        Read-only. Stocks and funds only; an option contract is filed under its
        underlying and is not read here.
        """
        import pandas as pd

        if not _SAFE_INSTRUMENT.fullmatch(instrument) or ".." in instrument:
            raise ArvoError(f"{instrument!r} is not an instrument id")
        if not re.fullmatch(r"[0-9]+[a-z]+", interval):
            raise ArvoError(f"{interval!r} is not an interval, e.g. '1day' or '5minute'")
        data = self.root / "data"
        folder = data if interval == DAILY else data / interval
        path = folder / f"{instrument}.csv"
        if not path.is_file():
            raise ArvoError(f"no {interval} bars for {instrument} in {folder}")
        frame = pd.read_csv(path, parse_dates=["date"], index_col="date")
        return frame


def _caller() -> str:
    """Where the script asked for a run, as ``path:line``: the frame above the
    client's own method. The workbench shows the finding's caveats against
    that line. Empty when there is no such frame."""
    import inspect

    frames = inspect.stack()
    if len(frames) < 3:
        return ""
    caller = frames[2]
    return f"{os.path.abspath(caller.filename)}:{caller.lineno}"


def _when(value: Any) -> str:
    """A point in time as the engine reads it: ``2026-01-31T09:30:00``, or a
    date. A ``datetime``, a ``date``, a pandas ``Timestamp`` or a string."""
    if isinstance(value, str):
        return value
    if hasattr(value, "strftime"):
        if hasattr(value, "hour"):
            return value.strftime("%Y-%m-%dT%H:%M:%S")
        return value.strftime("%Y-%m-%d")
    return str(value)


_MEDIA_TYPES = {
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".txt": "text/plain",
    ".html": "text/html",
    ".pdf": "application/pdf",
}


def _attachment(kept: Any) -> Attachment:
    return Attachment(kept.name, kept.media_type, kept.hash, int(kept.bytes), kept.added_at)


def _finding(reply: Any) -> Finding:
    summary = reply.summary
    return Finding(
        id=summary.id,
        kind=summary.kind,
        subject=summary.subject,
        verdict=summary.verdict,
        recorded_at=summary.recorded_at,
        author=summary.author,
        read_this_first=reply.read_this_first,
        reasons=list(reply.reasons),
        advice=[Advice(a.severity, a.finding, a.action, a.evidence) for a in reply.advice],
        strategy=summary.strategy,
        code_commit=summary.code_commit,
        ruleset_hash=summary.ruleset_hash,
        detail=json.loads(reply.detail_json) if reply.detail_json else {},
        attachments=[_attachment(a) for a in reply.attachments],
    )
