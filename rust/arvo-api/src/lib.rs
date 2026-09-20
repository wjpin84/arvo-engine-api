//! The types of Arvo's engine API, generated from its protobuf contract.
//!
//! Every message in the [contract](https://github.com/wjpin84/arvo-engine-api)
//! is here, one module per proto package and every shape at the root as
//! well. Each carries the comment written on it in the proto: that is the
//! single source of what a field means, and nothing is documented here that
//! is not documented there.
//!
//! # Messages only
//!
//! There is no transport in this crate, which is what lets it build for
//! WebAssembly. A browser-side front end links this; the gRPC stubs live in
//! `arvo-client`, which depends on this and re-exports it.
//!
//! # What is not generated
//!
//! proto3 makes every nested message optional and spells a Rust enum with
//! data as a `oneof`. The [ergonomics](#accessors-and-constructors) at the
//! bottom of this crate are the small amount of hand-written Rust that says
//! what the generated shapes cannot: which nested fields the engine always
//! sends, and how to build or match a `oneof` without naming its `Of`.
//!
//! # Accessors and constructors
//!
//! - A field the engine always fills has an accessor of the same name that
//!   returns it by reference: `study.strategy()` rather than
//!   `study.strategy.as_ref().unwrap()`. It panics only if the sender left
//!   the field out, which would mean the two sides disagree about the
//!   contract, and an empty panel would hide that.
//! - A `oneof` has constructors (`RecordView::study(view)`,
//!   `EventKindView::plugin(id, reachable)`) and, where a reader wants one
//!   question answered, an accessor (`plugin.reachable()`, `event.of()`).
//! - [`count`] and [`size`] convert a count between `usize` and the `u32` it
//!   is on the wire, saturating rather than panicking.
//!
//! # Serde
//!
//! Every shape derives `Serialize` and `Deserialize` with serde's defaults,
//! because the same shapes cross JSON bridges as well as gRPC.

#![warn(missing_docs)]

/// Generated from `protos/` by `cargo run -p generate` and committed.
///
/// The module tree mirrors the package names, because that is how a type in
/// one package refers to a type in another. The services are not here;
/// `arvo-client` generates those and points them back at these types.
mod generated;

/// One module per domain, for code that wants to say which it means.
pub use generated::arvo::{
    common::v1 as common, market::v1 as market, platform::v1 as platform,
    portfolio::v1 as portfolio, research::v1 as research, session::v1 as session,
};

/// Every shape at the root as well, because a window names a view on nearly
/// every line and `arvo_api::research::StudyView` would be noise. The names
/// do not collide: proto has no overloading and neither does this.
pub use generated::arvo::{
    common::v1::*, market::v1::*, platform::v1::*, portfolio::v1::*, research::v1::*,
    session::v1::*,
};

/// What the generated shapes cannot say for themselves.
///
/// proto3 makes every message field absent-able, so a nested shape arrives as
/// an `Option` even where it is always sent. These accessors say "the sender
/// always fills this", in one place, instead of at every reader.
mod ergonomics {
    use super::{
        platform::{event_kind_view, plugin_status_view},
        research::record_view,
        EventKindView, EventView, FeedEvent, FindingsEvent, PluginEvent, SessionEvent, SeverityView,
        StreamEvent,
        BookView, ImportView, MetricsView, PanelView, PluginStatusView, PluginStatusViewReachable,
        PluginStatusViewUnreachable, PluginView, PortfolioView, RecordView, ReportedView, StudyView,
        TradesView, WalkForwardView,
    };

    /// A count on the wire. Rust counts in `usize`; the contract is explicit
    /// about width, because a reader in another language has to be.
    #[must_use]
    pub fn count(n: usize) -> u32 {
        u32::try_from(n).unwrap_or(u32::MAX)
    }

    /// A count read back, for code that indexes with it.
    #[must_use]
    pub fn size(n: u32) -> usize {
        usize::try_from(n).unwrap_or(usize::MAX)
    }

    macro_rules! always {
        ($owner:ty, $field:ident, $ty:ty) => {
            impl $owner {
                /// The sender always fills this.
                ///
                /// # Panics
                ///
                /// Only if it did not, which would mean the two sides disagree
                /// about the contract.
                #[must_use]
                pub fn $field(&self) -> &$ty {
                    self.$field.as_ref().expect(concat!(stringify!($owner), " always carries ", stringify!($field)))
                }
            }
        };
    }
    always!(StudyView, strategy, MetricsView);
    always!(StudyView, benchmark, MetricsView);
    always!(StudyView, trades_detail, TradesView);
    always!(WalkForwardView, strategy, MetricsView);
    always!(WalkForwardView, benchmark, MetricsView);
    always!(WalkForwardView, trades_detail, TradesView);
    always!(BookView, metrics, MetricsView);
    always!(PortfolioView, import, ImportView);

    impl PluginView {
        /// Whether the last probe reached it.
        #[must_use]
        pub fn reachable(&self) -> bool {
            matches!(self.status.as_ref().and_then(|s| s.of.as_ref()), Some(plugin_status_view::Of::Reachable(_)))
        }

        /// What it said it is, if the last probe reached it.
        #[must_use]
        pub fn reached(&self) -> Option<&PluginStatusViewReachable> {
            match self.status.as_ref().and_then(|status| status.of.as_ref()) {
                Some(plugin_status_view::Of::Reachable(status)) => Some(status),
                _ => None,
            }
        }

        /// Why the last probe did not reach it, if it did not.
        ///
        /// A plugin whose status is missing counts as unreached: the window
        /// says so rather than drawing it as healthy.
        #[must_use]
        pub fn unreachable(&self) -> Option<&str> {
            match self.status.as_ref().and_then(|status| status.of.as_ref()) {
                Some(plugin_status_view::Of::Unreachable(status)) => Some(&status.reason),
                Some(plugin_status_view::Of::Reachable(_)) => None,
                None => Some("the engine sent no status"),
            }
        }
    }

    impl PluginStatusView {
        /// It answered, and said what it is.
        #[must_use]
        pub fn reachable(name: String, version: String, capabilities: Vec<String>) -> Self {
            Self {
                of: Some(plugin_status_view::Of::Reachable(PluginStatusViewReachable { name, version, capabilities })),
            }
        }

        /// It did not answer, and why.
        #[must_use]
        pub fn unreachable(reason: String) -> Self {
            Self { of: Some(plugin_status_view::Of::Unreachable(PluginStatusViewUnreachable { reason })) }
        }
    }

    impl EventKindView {
        /// A plugin became reachable, or stopped being.
        #[must_use]
        pub fn plugin(id: String, reachable: bool) -> Self {
            Self { of: Some(event_kind_view::Of::Plugin(PluginEvent { id, reachable })) }
        }

        /// A broker connection came up or went away.
        #[must_use]
        pub fn feed(id: String, connected: bool) -> Self {
            Self { of: Some(event_kind_view::Of::Feed(FeedEvent { id, connected })) }
        }

        /// The live price stream stopped or came back.
        #[must_use]
        pub fn stream(live: bool) -> Self {
            Self { of: Some(event_kind_view::Of::Stream(StreamEvent { live })) }
        }

        /// Stored findings went stale.
        #[must_use]
        pub fn findings(count: u32) -> Self {
            Self { of: Some(event_kind_view::Of::Findings(FindingsEvent { count })) }
        }

        /// A trading session changed state.
        #[must_use]
        pub fn session(id: String, state: String) -> Self {
            Self { of: Some(event_kind_view::Of::Session(SessionEvent { id, state })) }
        }
    }

    impl EventView {
        /// An event, with the kind and the text a renderer shows.
        #[must_use]
        pub fn new(kind: EventKindView, title: String, detail: String, severity: SeverityView) -> Self {
            Self { kind: Some(kind), title, detail, severity: severity as i32 }
        }

        /// What happened, structurally, if the sender said.
        #[must_use]
        pub fn of(&self) -> Option<&event_kind_view::Of> {
            self.kind.as_ref()?.of.as_ref()
        }
    }

    impl RecordView {
        /// A study, as a reopened record.
        #[must_use]
        pub fn study(view: StudyView) -> Self {
            Self { of: Some(record_view::Of::Study(view)) }
        }

        /// A walk-forward, as a reopened record.
        #[must_use]
        pub fn walk_forward(view: WalkForwardView) -> Self {
            Self { of: Some(record_view::Of::Walkforward(view)) }
        }

        /// A panel, as a reopened record.
        #[must_use]
        pub fn panel(view: PanelView) -> Self {
            Self { of: Some(record_view::Of::Panel(view)) }
        }

        /// Evidence Arvo did not compute, as a reopened record.
        #[must_use]
        pub fn reported(view: ReportedView) -> Self {
            Self { of: Some(record_view::Of::Reported(view)) }
        }
    }
}

pub use ergonomics::{count, size};
