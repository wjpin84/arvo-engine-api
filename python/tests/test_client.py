"""Against a real arvo-engine over a temporary app data directory.

Needs a built engine: set ``ARVO_ENGINE`` to its path, or have it on the PATH.
Skipped, loudly, when it is not.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

import arvo

# The engine is built elsewhere: point ARVO_ENGINE at it, or have it on the PATH.
# ARVO_ENGINE_BINARY is the older name and still works.
_named = os.environ.get("ARVO_ENGINE") or os.environ.get("ARVO_ENGINE_BINARY")
BINARY = Path(_named) if _named else Path(shutil.which("arvo-engine") or "arvo-engine")


@pytest.fixture
def engine(tmp_path: Path):
    if not BINARY.is_file():
        pytest.skip(f"set ARVO_ENGINE to a built arvo-engine ({BINARY} missing)")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "DEMO.SIM.csv").write_text(
        "date,open,high,low,close,volume\n"
        "2024-01-02,10,11,9,10.5,100\n"
        "2024-01-03,10.5,12,10,11.5,200\n",
        encoding="utf-8",
    )
    process = subprocess.Popen([str(BINARY), str(tmp_path)], stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 15
        while not (tmp_path / "engine.json").is_file():
            if time.monotonic() > deadline or process.poll() is not None:
                raise RuntimeError("the engine did not start")
            time.sleep(0.1)
        with arvo.connect(tmp_path) as client:
            yield client
    finally:
        process.kill()
        process.wait()


def test_reads_what_the_engine_offers(engine: arvo.Engine) -> None:
    names = [plan.name for plan in engine.strategies()]
    assert "sma_cross" in names
    assert engine.findings() == []
    assert [i.id for i in engine.instruments()] == ["DEMO.SIM"]


def test_a_run_says_why_it_could_not_run_and_a_missing_finding_is_not_found(
    engine: arvo.Engine,
) -> None:
    with pytest.raises(arvo.ArvoError) as refused:
        engine.run_study("NOPE.SIM", "sma_cross", author="script:test")
    assert refused.value.code == "FAILED_PRECONDITION"

    with pytest.raises(arvo.ArvoError) as anonymous:
        engine.run_study("DEMO.SIM", "sma_cross", author="")
    assert anonymous.value.code == "INVALID_ARGUMENT"
    assert "author" in str(anonymous.value)

    with pytest.raises(arvo.ArvoError) as missing:
        engine.finding("nope")
    assert missing.value.code == "NOT_FOUND"


def test_a_script_records_what_it_computed_and_arvo_judges_it(engine: arvo.Engine) -> None:
    """ADR-0026: the evidence goes in, the verdict comes out of Arvo, and the
    finding is the author's like any other. Nothing about it is a claim."""
    from datetime import date, timedelta

    start = date(2024, 1, 1)
    curve = [(start + timedelta(days=n), 100_000 * (1.002**n)) for n in range(300)]
    benchmark = [(start + timedelta(days=n), 100_000 * (1.0005**n)) for n in range(300)]
    ledger = [
        {"opened": start + timedelta(days=n), "closed": start + timedelta(days=n + 1), "entry": 100.0, "exit": 101.0, "pnl": 1.0}
        for n in range(40)
    ]
    found = engine.record(
        author="script:their-engine",
        hypothesis="h-momentum",
        claim="momentum persists for a month",
        instrument="SPY.THEIRS",
        window=("2024-01-01", "2024-10-26"),
        interval="1day",
        dataset=("theirs:SPY-1min", "sha256-of-their-inputs"),
        strategy="rsi2-pullback",
        engine="their-engine 0.2",
        curve=curve,
        ledger=ledger,
        benchmark_curve=benchmark,
        trials=12,
    )
    assert found.kind == "reported"
    assert found.verdict in {"Supported", "NotSupported", "Inconclusive"}
    assert found.author == "script:their-engine"
    assert found.detail["reported"]["engine"] == "their-engine 0.2"
    assert found.detail["reported"]["trades"] == 40
    assert [f.id for f in engine.findings()] == [found.id]

    # Files kept with it (#157): stored once by content, listed on the
    # finding, and the same file under the same name attached twice is one.
    kept = engine.attach(found.id, data=b"a,b\n1,2\n", name="trades.csv")
    assert [(a.name, a.media_type, a.bytes) for a in kept] == [("trades.csv", "text/csv", 8)]
    again = engine.attach(found.id, data=b"a,b\n1,2\n", name="trades.csv")
    assert len(again) == 1
    more = engine.attach(found.id, data=b"# report", name="report.md")
    assert [a.name for a in more] == ["trades.csv", "report.md"]
    assert [a.name for a in engine.finding(found.id).attachments] == ["trades.csv", "report.md"]
    with pytest.raises(arvo.ArvoError):
        engine.attach("nope", data=b"x", name="x.txt")

    # No benchmark is not a result, and Arvo says so rather than guessing one.
    alone = engine.record(
        author="script:their-engine",
        hypothesis="h-momentum",
        claim="momentum persists for a month",
        instrument="SPY.THEIRS",
        window=("2024-01-01", "2024-10-26"),
        interval="1day",
        dataset=("theirs:SPY-1min", "sha256-of-their-inputs"),
        strategy="rsi2-pullback",
        engine="their-engine 0.2",
        curve=curve,
    )
    assert alone.verdict == "Inconclusive"
    assert any("benchmark" in reason for reason in alone.reasons)

    # What cannot be left out is named, not defaulted.
    with pytest.raises(arvo.ArvoError) as missing:
        engine.record(
            author="script:their-engine", hypothesis="h", claim="", instrument="", window=("2024-01-01", "2024-02-01"),
            interval="1day", dataset=("d", "v"), strategy="s", engine="e", curve=curve,
        )
    assert missing.value.code == "INVALID_ARGUMENT"
    assert "instrument" in str(missing.value)


def test_bars_read_the_library_and_refuse_a_path_out_of_it(engine: arvo.Engine) -> None:
    frame = engine.bars("DEMO.SIM")
    assert list(frame["close"]) == [10.5, 11.5]
    assert str(frame.index[0].date()) == "2024-01-02"

    for escape in ["../engine", "..\\x", "a/b"]:
        with pytest.raises(arvo.ArvoError):
            engine.bars(escape)


def test_a_wrong_token_is_refused(engine: arvo.Engine) -> None:
    impostor = arvo.Engine(engine.root, _address(engine.root), "guess")
    with pytest.raises(arvo.ArvoError) as refused:
        impostor.strategies()
    assert refused.value.code == "UNAUTHENTICATED"
    impostor.close()


def test_no_engine_says_how_to_start_one(tmp_path: Path) -> None:
    with pytest.raises(arvo.ArvoError, match="start arvo-engine"):
        arvo.connect(tmp_path)


def _address(root: Path) -> str:
    import json

    return json.loads((root / "engine.json").read_text(encoding="utf-8"))["address"]


def test_a_finding_carries_its_ruleset_hash_and_goes_stale_when_the_ruleset_changes(
    engine: arvo.Engine, tmp_path: Path
) -> None:
    """#189: two findings from different versions of one ruleset are told apart,
    and the earlier one is marked stale for the ruleset, not the data."""
    import datetime
    import random

    from arvo.common.v1 import models_pb2 as common
    from arvo.research.v1 import models_pb2 as research

    # A series long enough for a moving-average rule to run on.
    random.seed(1)
    rows = ["date,open,high,low,close,volume"]
    price, day = 100.0, datetime.date(2022, 1, 3)
    while len(rows) < 600:
        if day.weekday() < 5:
            price *= 1 + random.gauss(0.0003, 0.01)
            rows.append(f"{day.isoformat()},{price:.2f},{price * 1.01:.2f},{price * 0.99:.2f},{price:.2f},1000")
        day += datetime.timedelta(days=1)
    (tmp_path / "data" / "LONG.SIM.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    # A ruleset over a shipped rule, fixing every parameter to one value.
    rules = engine._call(engine._stub.ListRules, common.Empty()).rules
    rule = next(r for r in rules if r.name == "sma_cross")
    params = [research.Param(name=f.name, values=[f.value]) for f in rule.fixed]
    params += [research.Param(name=a.name, values=[a.values[0]]) for a in rule.axes]
    form = research.RulesetForm(name="my_cross", rule="sma_cross", label="Mine", premise="", params=params)
    engine._call(engine._stub.WriteRuleset, form)

    first = engine.run_study("LONG.SIM", "my_cross", author="script:test")
    assert first.strategy == "my_cross"
    assert first.ruleset_hash, "a ruleset run records the document's hash"
    assert first.code_commit, "every run records the build"

    # The same ruleset, edited: one axis moved to its other end.
    axis = next(p for p in form.params if p.name == rule.axes[0].name)
    axis.values[:] = [rule.axes[0].values[-1]]
    engine._call(engine._stub.WriteRuleset, form)
    second = engine.run_study("LONG.SIM", "my_cross", author="script:test")
    assert second.ruleset_hash != first.ruleset_hash, "a different rule, whatever it is called"

    entries = {e.id: e for e in engine._call(engine._stub.ViewHistory, common.Empty()).entries}
    assert entries[first.id].stale is True
    assert entries[first.id].stale_reason == "ruleset", "the data did not change; the rule did"
    assert entries[second.id].stale is False
    assert entries[second.id].ruleset_hash == second.ruleset_hash
