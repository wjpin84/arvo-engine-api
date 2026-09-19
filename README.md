# The Arvo engine API

The contract between Arvo's engine and whatever talks to it: the desktop
window, the command line, a script, an agent. Two protobuf files and the notes
that go with them. There is no code here and no language — a front end in any
language generates these and reads a finding natively.

## What is here

Models by domain, services apart from them, and the shapes a front end renders
in their own package.

| Package | What it holds |
| --- | --- |
| `arvo.common.v1` | shapes with no domain of their own |
| `arvo.market.v1` | instruments, prices, and asking a vendor for either |
| `arvo.research.v1` | findings, the rules that produce them, and what a run is held to |
| `arvo.portfolio.v1` | what is held |
| `arvo.session.v1` | a rule trading against a venue, live |
| `arvo.platform.v1` | the engine's own jobs, plugins and accounts |
| `arvo.views.v1` | what a front end renders, split by the same domains |
| `arvo.services.v1` | the three services: `Research`, `Data`, `Sessions` |

`platform`, not `plugin`: `arvo.plugin.v1` is the provider contract in the
other repository, and one name cannot mean two things.

There is no error message anywhere here, on purpose. A refusal crosses as a
gRPC status code, one per kind, which is the same rule a provider follows.

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
- **The control token**, from `control.json` beside it, reaches `Data` and
  `Sessions`: the data library, accounts and their credentials, the plugins,
  the price stream, and live trading. Those are a person's decisions.

`engine.json` carries the address as well as the token, so a front end that
can find the file can find the engine. Both files are written by the engine
and readable only by the user it runs as.

## Versioning

Proto3, additively: new fields and new messages, never a renumbering, so a
client built against an older copy keeps working. The field numbers are the
contract.

`View { kind, json }` in `engine.proto` is on its way out, replaced by the
typed messages in `views.proto`. While both exist, `kind` names the message a
`View` is carrying.

## Generating

Whatever your toolchain does with a `.proto`. For example:

```
protoc -I protos --python_out=. --grpc_python_out=. protos/arvo/engine/v1/engine.proto
```

Rust callers point `tonic-prost-build` at the same directory. The engine and
the desktop each generate their own; neither ships the other's.
