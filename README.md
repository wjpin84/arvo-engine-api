# The Arvo engine API

The contract between Arvo's engine and whatever talks to it: the desktop
window, the command line, a script, an agent. Protobuf files and the notes
that go with them. There is no code here and no language — a front end in any
language generates these and reads a finding natively.

## What is here

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
| `arvo.platform.v1` | the engine's own jobs, plugins and accounts |
| `arvo.services.v1` | the services, one file per domain |

There was an `arvo.views.v1` and there is not any more. A view is a kind of
message, not a subject, and the tell was `arvo/views/v1/research.proto` next
to `arvo/research/v1/research.proto`: one word on two axes. Whoever wants
everything about research now opens one directory.

`platform`, not `plugin`: `arvo.plugin.v1` is the provider contract in the
other repository, and one name cannot mean two things.

There is no error message anywhere here, on purpose. A refusal crosses as a
gRPC status code, one per kind, which is the same rule a provider follows.

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

`Research` is the one an agent reaches. Nothing on it fetches, trades, shares,
imports, or names a credential, and a test in the engine reads this directory
to keep that true.

## The other direction is a different repository

This is what **calls Arvo**. A provider that **Arvo calls** — a data source, a
signal publisher — implements
[arvo-extension-api](https://github.com/wjpin84/arvo-extension-api) instead.

The two are not the same contract and should not be conflated. A provider
authenticates with its own vendor and is handed a grant for one call; a caller
authenticates with Arvo and holds one of its two tokens.

## Two tiers, two tokens

The engine serves on loopback and admits `authorization: Bearer <token>`.

- **The research token**, from `engine.json` in Arvo's application data
  directory, reaches the `Research` service. That service is the boundary an
  agent gets: it reads findings and runs studies, and no call on it fetches,
  trades, shares, imports, or names a credential.
- **The control token**, from `control.json` beside it, reaches every other
  service: the data library, accounts and their credentials, the plugins, the
  price stream, and live trading. Those are a person's decisions.

`engine.json` carries the address as well as the token, so a front end that
can find the file can find the engine. Both files are written by the engine
and readable only by the user it runs as.

## Versioning

Proto3, additively: new fields and new messages, never a renumbering, so a
client built against an older copy keeps working. The field numbers are the
contract.

There was a `View { kind, json }` in `arvo.common.v1` and there is not any
more. Every call names the message it answers with, so a reader in any
language gets a shape rather than a string and a blob it has to know the
meaning of out of band.

A call that answers with a list returns a message wrapping it — `SourcesView`,
`JobsView`, `ProblemsView` — because an RPC returns one message and never a
bare repeated field. The wrapper is also where a total or a cursor goes later,
without renumbering what is already there.

## Generating

Whatever your toolchain does with a `.proto`. For example:

```
protoc -I protos --python_out=. --grpc_python_out=. protos/arvo/services/v1/research.proto
```

Rust callers point `tonic-prost-build` at the same directory. The engine and
the desktop each generate their own; neither ships the other's.
