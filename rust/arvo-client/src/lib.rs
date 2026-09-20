//! Talk to Arvo's engine over gRPC.
//!
//! This is the client side of the
//! [contract](https://github.com/wjpin84/arvo-engine-api): the stubs
//! generated from its services, how to find the engine running for this
//! user, and the token each service takes. The types the stubs carry are
//! `arvo-api`, re-exported under [`proto`] so a call site names one path
//! whether it wants a stub or a shape.
//!
//! # Finding the engine
//!
//! The engine serves on loopback and writes where it is into the user's app
//! data directory. [`discovery`] reads that: the address, whether the engine
//! at it is still answering, and the two tokens.
//!
//! # Two tokens
//!
//! Which token a service takes is a property of the service, not of the
//! call. The **research token**, from `engine.json`, reaches the `Research`
//! service and nothing else: an agent or a script holding it can read
//! findings and run studies, and cannot fetch, trade, share, import or name
//! a credential. The **control token**, from `control.json`, reaches every
//! other service, which is where a person's decisions live. [`request`] puts
//! either one on a call.
//!
//! # A call
//!
//! ```no_run
//! use arvo_client::{discovery, proto, request};
//! use proto::common::Empty;
//! use proto::services::research_client::ResearchClient;
//!
//! # #[tokio::main] async fn main() -> Result<(), Box<dyn std::error::Error>> {
//! let engine = discovery::running(&discovery::default_root()?).ok_or("start arvo-engine first")?;
//! let mut research = ResearchClient::connect(engine.endpoint()).await?;
//! let listed = research.list_strategies(request(&engine.token, Empty {})?).await?.into_inner();
//! for strategy in listed.strategies {
//!     println!("{}: {}", strategy.name, strategy.premise);
//! }
//! # Ok(()) }
//! ```
//!
//! A refusal crosses as a gRPC status code, never as a message with an error
//! field. A study's answer is large; see [`wire::MAX_MESSAGE_BYTES`].
//!
//! # The server side
//!
//! The same generated module holds the server traits, `research_server::Research`
//! and the rest. Arvo's engine implements them; so can a test double.

#![warn(missing_docs)]

/// The contract, as this side of the wire uses it.
///
/// The services are generated here; every type they carry is generated once,
/// in `arvo-api`, and re-exported below so a call site names one path whether
/// it wants a stub or a shape.
pub mod proto {
    pub use crate::generated::services;

    pub use arvo_api::{common, market, platform, portfolio, research, session};
}

mod generated;

pub mod discovery;
pub mod wire;

mod error;
pub use error::CommandError;

/// `message`, carrying `token` the way the engine admits it.
///
/// Which token is the caller's business: the research token for the
/// `Research` service, the control token for everything else. A token from
/// the wrong file is refused as `Unauthenticated`, not as a bad request.
///
/// # Errors
///
/// A token that is not printable ASCII, which the engine never writes.
pub fn request<T>(
    token: &str,
    message: T,
) -> Result<tonic::Request<T>, tonic::metadata::errors::InvalidMetadataValue> {
    let mut request = tonic::Request::new(message);
    request.metadata_mut().insert("authorization", format!("Bearer {token}").parse()?);
    Ok(request)
}
