# The Arvo engine API

The contract between Arvo's engine and whatever talks to it: the desktop
window, the command line, a script, an agent. The protobuf files are the
contract. The Rust crates and the Python package beside them are generated
from those files and published under the same version, so a front end in
either language reads a finding natively and two front ends never disagree
about what one is.

| | Where | Published as |
| --- | --- | --- |
| the contract | [`protos/`](protos) | this repository, tagged `vX.Y.Z` |
| Rust types | [`rust/arvo-api`](rust/arvo-api) | [`arvo-api`](https://crates.io/crates/arvo-api) on crates.io |
| Rust client | [`rust/arvo-client`](rust/arvo-client) | [`arvo-client`](https://crates.io/crates/arvo-client) on crates.io |
| Python | [`python/`](python) | [`arvo-client`](https://pypi.org/project/arvo-client/) on PyPI, imported as `arvo` |

Nothing is in a binding that is not in a proto, with two exceptions that
are documented as such: the small ergonomics over generated shapes
(accessors for fields the engine always sends, constructors for `oneof`s),
and discovery, which is how a front end finds a running engine and which
token it holds. The generated code is committed, so a reader can open the
types without generating anything and a consumer needs no `protoc`.

## Using it

**From Rust**, the types alone or the client with them:

```toml
[dependencies]
arvo-client = "0.1"   # brings arvo-api with it
```

```rust,no_run
use arvo_client::{discovery, proto, request};
use proto::common::Empty;
use proto::services::research_client::ResearchClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let engine = discovery::running(&discovery::default_root()?).ok_or("start arvo-engine first")?;
    let mut research = ResearchClient::connect(engine.endpoint()).await?;
    for strategy in research.list_strategies(request(&engine.token, Empty {})?).await?.into_inner().strategies {
        println!("{:<14} {}", strategy.name, strategy.premise);
    }
    Ok(())
}
```

**From Python**, a client for scripts and the raw stubs for everything else:

```sh
pip install arvo-client
```

```python
import arvo

engine = arvo.connect()
found = engine.run_study("AAPL.RH", "sma_cross", author="script:first-look")
print(found.verdict, found.read_this_first)
```

Each binding's own README says more: [Rust types](rust/arvo-api/README.md),
[Rust client](rust/arvo-client/README.md), [Python](python/README.md).

## The protos

One package per domain, and the services apart from them. A domain directory
holds `models.proto`, what the domain is made of, and `views.proto`, what a
front end renders of it. Both declare the same package, so everything about a
subject is in one place.

| Package | What it holds |
| --- | --- |
| `arvo.common.v1` | shapes with no domain of their own |
| `arvo.market.v1` | instruments, prices, and asking a vendor for either |
| `arvo.research.v1` | findings, the rules that produce them, and what a run is held to |
| `arvo.portfolio.v1` | what is held |
| `arvo.session.v1` | a rule trading against a venue, live |
| `arvo.platform.v1` | the engine's own jobs, plugins, accounts and scripts |
| `arvo.services.v1` | the services, one file per domain |

`platform`, not `plugin`: `arvo.plugin.v1` is the provider contract in the
[other repository](https://github.com/wjpin84/arvo-extension-api), and one
name cannot mean two things.

There is no error message anywhere here, on purpose. A refusal crosses as a
gRPC status code, one per kind, which is the same rule a provider follows.

Every call names the message it answers with. A call that answers with a
list returns a message wrapping it — `SourcesView`, `JobsView`,
`ProblemsView` — because an RPC returns one message and never a bare
repeated field, and the wrapper is where a total or a cursor goes later
without renumbering what is already there.

## The services, and which token each is behind

A service is named for its domain, not for who may call it. Which token it
admits is a property of the service, applied by an interceptor, and it is
stated at the top of each file.

| Service | Token | What it is for |
| --- | --- | --- |
| `Research` | research | the agent surface: findings, studies, the shapes a workbench renders |
| `ResearchFiles` | control | importing an experiment someone sent, and what a finding turns into on disk |
| `Market` | control | the data library, the sources that fill it, and prices |
| `Accounts` | control | a person's relationship with each vendor |
| `Portfolio` | control | what is held, valued |
| `Platform` | control | jobs and the plugins this engine hosts |
| `Sessions` | control | a rule trading against a venue, live |
| `Scripts` | control | a person's own scripts: running one, and the cadences they set |

`Research` is the one an agent reaches. Nothing on it fetches, trades,
shares, imports, or names a credential, and a test in the engine reads this
directory to keep that true.

## Two tiers, two tokens

The engine serves on loopback and admits `authorization: Bearer <token>`.

- **The research token**, from `engine.json` in Arvo's application data
  directory, reaches the `Research` service. That service is the boundary an
  agent gets: it reads findings and runs studies, and no call on it fetches,
  trades, shares, imports, or names a credential.
- **The control token**, from `control.json` beside it, reaches every other
  service: the data library, accounts and their credentials, the plugins, the
  price stream, scripts, and live trading. Those are a person's decisions.

`engine.json` carries the address as well as the token, so a front end that
can find the file can find the engine. Both files are written by the engine
and readable only by the user it runs as. The Rust client's `discovery`
module and the Python package's `connect()` read them.

## The other direction is a different repository

This is what **calls Arvo**. A provider that **Arvo calls** — a data source,
a signal publisher — implements
[arvo-extension-api](https://github.com/wjpin84/arvo-extension-api) instead.

The two are not the same contract and should not be conflated. A provider
authenticates with its own vendor and is handed a grant for one call; a
caller authenticates with Arvo and holds one of its two tokens.

## Versioning and releasing

One version for the protos and every binding, bumped by the rules in
[VERSIONING.md](VERSIONING.md) and recorded in [CHANGELOG.md](CHANGELOG.md).
Proto3, additively where possible: new fields and new messages, never a
renumbering, so a client built against an older copy keeps working. The
field numbers are the contract.

A release is a tag; a GitHub workflow publishes the three artifacts from it,
in dependency order, after checking that the committed bindings match the
protos. Nothing publishes from a laptop.

## Regenerating the bindings

After a proto changes, both bindings are regenerated and the result
committed:

```sh
cd rust && cargo run -p generate
cd python && uv run python -m grpc_tools.protoc -I ../protos --python_out=src --grpc_python_out=src $(find ../protos -name '*.proto')
```

Any other language points its own toolchain at `protos/`:

```sh
protoc -I protos --<lang>_out=. $(find protos -name '*.proto')
```
