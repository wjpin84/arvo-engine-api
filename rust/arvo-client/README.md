# arvo-client

Talk to Arvo's engine over gRPC. This crate is the client side of the
[contract](https://github.com/wjpin84/arvo-engine-api): the stubs generated
from its services, how to find the engine running for this user, and which
token each service takes. The types the stubs carry are
[`arvo-api`](https://crates.io/crates/arvo-api), re-exported here so a call
site names one path whether it wants a stub or a shape.

```toml
[dependencies]
arvo-client = "0.1"
tokio = { version = "1", features = ["rt-multi-thread", "macros"] }
```

## Finding the engine

The engine serves on loopback and writes where it is into the user's app
data directory: `engine.json` with the address and the **research token**,
and `control.json` beside it with the **control token**. The
[`discovery`](https://docs.rs/arvo-client/latest/arvo_client/discovery/)
module reads both, and answers whether the engine at that address is still
there.

```rust,no_run
use arvo_client::discovery;

let root = discovery::default_root()?;
let engine = discovery::running(&root).ok_or("no engine is running; start arvo-engine")?;
println!("engine at {} (pid {})", engine.address, engine.pid);
# Ok::<(), Box<dyn std::error::Error>>(())
```

## Two tokens

Which token a service takes is a property of the service, not of the call.

| Token | File | Reaches | For |
| --- | --- | --- | --- |
| research | `engine.json` | `Research` | an agent, a script: reads findings, runs studies. No call on it fetches, trades, shares, or names a credential. |
| control | `control.json` | everything else | a person's front end: the data library, accounts, portfolios, plugins, sessions, scripts. |

A script or an agent that only reads `engine.json` cannot reach the control
tier, by construction rather than by policy. The token goes on each request
as `authorization: Bearer <token>`; [`request`] puts it there.

## Calling it

```rust,no_run
use arvo_client::{discovery, proto, request};
use proto::common::Empty;
use proto::services::research_client::ResearchClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let root = discovery::default_root()?;
    let engine = discovery::running(&root).ok_or("no engine is running; start arvo-engine")?;

    let mut research = ResearchClient::connect(engine.endpoint()).await?;
    let listed = research.list_strategies(request(&engine.token, Empty {})?).await?.into_inner();
    for strategy in listed.strategies {
        println!("{:<14} {}", strategy.name, strategy.premise);
    }
    Ok(())
}
```

A study is the same shape of call, and answers with the typed view a front
end renders:

```rust,no_run
use arvo_client::{proto, request};
use proto::research::StudyRequest;
use proto::services::research_client::ResearchClient;

async fn study(research: &mut ResearchClient<tonic::transport::Channel>, token: &str) -> Result<(), Box<dyn std::error::Error>> {
    let asked = StudyRequest { instrument: "AAPL.YF".to_owned(), strategy: Some("sma_cross".to_owned()) };
    let study = research.view_study(request(token, asked)?).await?.into_inner();
    println!("{}: {} — {}", study.instrument, study.verdict, study.read_this_first);
    println!("sharpe {:.2}, max drawdown {:.1}%", study.strategy().sharpe, study.strategy().max_drawdown * 100.0);
    Ok(())
}
```

The control tier's services take the control token the same way. A refusal
crosses as a gRPC status code, never as a message with an error field: an
unknown token is `Unauthenticated`, a bad argument `InvalidArgument`.

Large answers are large. A study carries curves, a ledger and a search
surface, and tonic's default four-megabyte limit does not fit one. Set the
limit on a client to [`wire::MAX_MESSAGE_BYTES`], which is what the engine
allows:

```rust,no_run
# use arvo_client::proto::services::research_client::ResearchClient;
# async fn f(channel: tonic::transport::Channel) {
let research = ResearchClient::new(channel).max_decoding_message_size(arvo_client::wire::MAX_MESSAGE_BYTES);
# }
```

## The server side

The same stubs include the server traits: `research_server::Research`,
`market_server::Market`, and so on under `proto::services`. Arvo's engine
implements them; so can a test double.

## Regenerating

The generated code under `src/generated` is produced by `cargo run -p
generate` in the contract repository and committed. Do not edit it; change
the proto and regenerate.

## Versioning

This crate, `arvo-api` and the Python package share one version with the
protos they are generated from, and this crate pins `arvo-api` to exactly
that version. The rules are in
[VERSIONING.md](https://github.com/wjpin84/arvo-engine-api/blob/main/VERSIONING.md).

## License

Apache-2.0.
