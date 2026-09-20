# arvo-api

The types of Arvo's engine API: every message in the
[contract](https://github.com/wjpin84/arvo-engine-api), generated from the
protos and committed, with the small amount of Rust the generated shapes
cannot say for themselves.

Messages only. There is no transport here, which is what lets this crate
build for WebAssembly: a browser-side front end links it, and the gRPC stubs
live next door in [`arvo-client`](https://crates.io/crates/arvo-client).

```toml
[dependencies]
arvo-api = "0.1"
```

## What you get

**One module per domain**, named as the proto package is: `common`,
`market`, `research`, `portfolio`, `session`, `platform`. Every shape is also
re-exported at the crate root, because a front end names a view on nearly
every line and `arvo_api::research::StudyView` would be noise.

**Documentation from the protos.** Every message and field carries the
comment written on it in the contract. That is the single source: nothing is
documented here that is not documented there.

**serde on everything.** The shapes cross JSON bridges as well as gRPC, so
each derives `Serialize` and `Deserialize` with serde's defaults.

**Accessors for what proto cannot promise.** proto3 makes every nested
message optional, so a study's metrics arrive as `Option<MetricsView>` even
though the engine always sends them. The accessors say so in one place:

```rust
use arvo_api::StudyView;

fn sharpe(study: &StudyView) -> f64 {
    // `strategy()` rather than `strategy.as_ref().unwrap()` at every reader.
    // It panics only if the sender left the field out, which would mean the
    // two sides disagree about the contract.
    study.strategy().sharpe
}
```

**Constructors and matches for the oneofs.** A Rust enum carrying data is a
`oneof` in proto, generated as a nested `Of` enum inside an `Option`. The
constructors and the accessors keep that out of your code:

```rust
use arvo_api::{record_view::Of, RecordView, StudyView};

fn open(record: RecordView) {
    match record.of {
        Some(Of::Study(study)) => show_study(study),
        Some(Of::Walkforward(walk)) => show_walk(walk),
        Some(Of::Panel(panel)) => show_panel(panel),
        Some(Of::Reported(reported)) => show_reported(reported),
        // A kind this build cannot name: a newer engine. Not an error.
        None => {}
    }
}

fn reopened(study: StudyView) -> RecordView {
    RecordView::study(study)
}
# fn show_study(_: StudyView) {}
# fn show_walk(_: arvo_api::WalkForwardView) {}
# fn show_panel(_: arvo_api::PanelView) {}
# fn show_reported(_: arvo_api::ReportedView) {}
```

**Counts.** A count is `u32` on the wire, explicit about width because a
reader in another language has to be. `count` and `size` convert to and from
`usize` at the edges, saturating rather than panicking.

## Regenerating

The generated code under `src/generated` is produced by `cargo run -p
generate` in the contract repository and committed. Do not edit it; change
the proto and regenerate.

## Versioning

This crate, `arvo-client` and the Python package share one version with the
protos they are generated from. The rules for what moves which part are in
[VERSIONING.md](https://github.com/wjpin84/arvo-engine-api/blob/main/VERSIONING.md).

## License

Apache-2.0.
