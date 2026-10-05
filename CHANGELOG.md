# Changelog

One entry per release, covering the protos and every binding of them. The
bump named on each release follows [VERSIONING.md](VERSIONING.md).

## Unreleased

A minor bump when it is released. On the wire it is additive: three fields and
one metadata key, and an older engine ignores all of them. **One binding
breaks:** the Python `run_panel` now requires `author`, because a panel run
without one was the hole this closes.

- **`PanelRequest.author`** and **`PanelRequest.origin`** (#8): who is running
  a panel, with the meaning they have on `RunRequest`. With an author the
  panel is saved as that author's finding and deflated against everything the
  author has run. Until now every panel was recorded as a person's, so an
  agent or a script could run panels until one passed and nothing counted
  them. Empty is a person at the window. Additive.
- **`arvo-author` metadata** (#8): how a caller that is not a person names
  itself on a call that records no finding, such as writing a rule or
  translating a script. The engine's audit trail reads it. A field on those
  requests was the alternative and was not taken: `RulesetForm` is also what
  `ReadRuleset` answers with, and who is asking is not part of a ruleset.
  `arvo_client::AUTHOR`, `request_as` and `author_of` in Rust; the `author=`
  argument on `write_rule` and `translate_pine` in Python. Additive.
- **`Finding.data_findings`** (#9): what is wrong with the bars a finding was
  produced from, in the shape a window already shows beside a chart. An agent
  or a script opening a finding had the verdict and no word about the series
  under it. `Finding.data_findings` in Python, as `DataFinding`. Additive.
- **Python `run_panel(universe, *, author, strategy=None)`**: `author` is
  required. A script is never a person at the window. **Breaking for a script
  that calls `run_panel` today.**
- **`SessionStatus.state` may be `dropped`** (arvo-engine#13): a session the
  engine hosting it ended without stopping. The next engine finds its record
  unfinished and lists it, with why in `last_error`, until it is started
  again. A state is a string, so nothing changes on the wire; a client that
  switches on the state should treat it as it treats `failed`.
- **`PromotionView.paper_days` counts days with bars** (arvo-engine#36): the
  days the paper session took a bar on, not the calendar days from its first
  start to its last line. A comment; nothing changes on the wire.

## 0.6.0 (2026-09-27)

A minor bump, additive throughout: five calls, seven messages, four fields on
existing messages, and one event kind. No field number changed and nothing was
removed, so an existing client keeps working and an older engine answers
`Unimplemented` to the new calls. The last five entries are what a chart needs
from the engine and nothing else (arvo-finance-chart).

`ReviewView.refusals` and `ReviewView.spans` below are inside that one new
`json` field rather than proto fields of their own, which is why the review's
shape can grow without a bump: what a chart reads is JSON, and a reader that
does not know a key ignores it.

- **`Research.ListRuleFiles`** and **`Research.WriteRule`**, with `RuleFile`,
  `RuleFiles` and `RuleText` (#225): the project's rules written as data, and
  writing one. Additive.
- **`ReviewView.json`** (#229): the day's review as JSON, so a chart can draw
  the fills against their decision prices, the refusals and the frozen
  stretches. Additive, and the review gains `refusals` and `spans`.
- **`Research.TranslatePine`**, with `PineScript` and `PineTranslation`
  (#228): a Pine v5 strategy translated into a rule, with every construct it
  cannot say named. It writes nothing; the rule it returns goes to
  `WriteRule`. Additive.
- **`CandlePoint.volume`** and **`BarView.time`** (arvo-engine-api #3): one
  bar shape. A chart keys by `time` and draws volume from either message
  without a second decoder. `BarView.time` is the same instant as `at`, UTC,
  as seconds since the epoch. Additive.
- **`BarsView.zone`** (#5): the IANA zone the instrument's sessions are
  stated in, `America/New_York` for US equities. Bar times stay UTC, which
  the messages now say; the zone is what a chart converts with. Additive.
- **`Research.StreamBars`** (#4): a window of the library whole, in messages
  of at most 2000 bars, oldest first, for paging through history. `ReadBars`
  and its cap are unchanged. Additive.
- **`Research.ReadIndicator`** with **`IndicatorRequest`** (#6): one
  indicator over a window of bars, declared as a rule declares it and
  computed by the same code with the same warm-up, answered as a
  `NamedCurveView`. Additive.
- **`LibraryEvent`** on `EventKindView` (#7): a fetch wrote an instrument's
  bars; carries the library's new content hash. Additive.

## 0.5.0 (2026-09-26)

A minor bump, additive: one call, one message, two fields. An older engine
answers `Unimplemented` to a panel over a universe.

- **`Research.RunPanel`** with `PanelRequest` (#227): a panel over one of the
  project's universes, under a rule or the default. `PanelView` gains
  `universe` and `notes`. Additive.

## 0.4.0 (2026-09-25)

A minor bump, additive: one call and its two messages. An older engine
answers `Unimplemented` to the leaderboard; a client built against 0.3.0
never asks.

- **`Research.RankFindings`**, with `RankRequest`, `Ranking` and
  `RankingRowView` (#226): the leaderboard, every comparable finding in the
  one order the research tier ranks by (Supported under conservative costs
  first, by that expectancy; ties by drawdown, then trades). Additive.

## 0.3.0 (2026-09-21)

A minor bump, all additive: a message and a call. A client built against
0.2.0 reads no divergence and an older engine answers `Unimplemented` to
the review.

- **`Research.ViewReview`**, with `ReviewRequest` and `ReviewView` (#217):
  the review after the close for a day, as Markdown, written under the
  project's `reviews/` if it was not already.
- **`SessionStatus.divergence`** and the `Divergence` message (#18): what a
  session's fills cost against their decision prices, and the latency, with
  the slippage the finding assumed beside them. Absent until something
  filled, and for an older engine.

## 0.2.0 (2026-09-21)

A minor bump, all additive: messages grew and two services gained calls. A
client built against 0.1.0 reads empty fields and an older engine answers
`Unimplemented` to the new calls.

- **`SessionStatus.verdict` and `verdict_reason`.** A session's verdict in
  the research vocabulary — `holding`, `diverging` or `inconclusive` —
  judged from its own trades against the finding's out-of-sample
  expectation, with the reason when it is diverging (#221). A client built
  against 0.1.0 reads an empty verdict and no reason.
- **`SessionStatus.warnings`.** The gate's limits the session is within
  four fifths of, in the gate's words (#191). Empty for an older engine.
- **`Sessions.CheckPromotion` and `PromotionView`.** What the promotion
  gate would say to a start, without starting (#194, #199). An older
  engine answers `Unimplemented`.
- **`Research.ReadBars` and `Research.ViewRegime`**, with `BarsRequest`,
  `BarsView`, `BarView`, `RegimeView` and `RegimePointView` (#195). The
  research tier can now look at what a study saw: bars over a window, and
  the regime each bar closed in. Read-only; nothing here fetches.

## 0.1.0 (2026-09-21)

The first version of the contract as a published thing. Nothing shipped to
a registry before this, so there is no bump to name and nothing here is a
break of anything.

- **Protos.** One package per domain, each holding `models.proto` and
  `views.proto`; the services apart from them under `arvo.services.v1`, one
  file per domain, each behind either the research token or the control
  token. Every call names the message it answers with; there is no untyped
  envelope. Lists cross as messages (`SourcesView`, `JobsView`, ...) so a
  total or a cursor can join them later without renumbering.
- **Services.** `Research` (research token), and behind the control token
  `ResearchFiles`, `Market`, `Accounts`, `Portfolio`, `Platform`,
  `Sessions` and `Scripts`. Scripts and the cadences a person sets for them
  are the engine's, so a schedule runs with no window open.
- **Rust.** `arvo-api` (messages, serde, no transport, builds for
  WebAssembly) and `arvo-client` (stubs, discovery, tokens). Generated code
  is committed; consumers need no protoc.
- **Provenance (#189).** A finding says what produced it: `strategy`,
  `code_commit` and `ruleset_hash` on `FindingSummary`, and the same with a
  `stale_reason` on `HistoryEntryView`. A finding whose ruleset has changed
  since is stale, like one whose data has.
- **Python.** The `arvo` package as `arvo-client`: a research client and
  the generated stubs for every service.
- **Reconciliation as an incident (#187).** A session whose book disagrees
  with the venue's freezes: `SessionStatus.state` gains `frozen`, with
  `frozen` naming the disagreement and `reconciled` saying whether it has
  been squared. `Sessions` gains `ReconcileSession` and `ResumeSession`,
  both by `SessionId`; a resume before a reconcile is refused.
- **Trade journal (#190).** `LedgerTrade`, `TradeRow` and `TradeRowView`
  gain `rule`, `signal`, `regime` and `asked`: what the rule saw when it
  opened the trade and what it asked the gate for. All optional; a trade
  recorded before the journal carries none.
- **Kill switch (#127).** `Sessions.HaltSession(HaltRequest{id, reason})`
  arms the gate and flattens what the session holds; the status comes back
  `halted`.

