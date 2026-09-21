# Changelog

One entry per release, covering the protos and every binding of them. The
bump named on each release follows [VERSIONING.md](VERSIONING.md).

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

