# Versioning

One version, three artifacts. The protos are the contract; `arvo-api` and
`arvo-client` on crates.io and `arvo-client` on PyPI are generated from them
and carry the same number. A git tag `vX.Y.Z` on this repository is a
release of all of it at once, so a reader in any language can say "engine
API 0.3" and mean one thing.

The version lives in two places, bumped together:

- `rust/Cargo.toml`, under `[workspace.package]`
- `python/pyproject.toml`, under `[project]`

## Which part moves

Semantic versioning, read from the point of view of an existing client.

| Bump | When | Examples |
| --- | --- | --- |
| **MAJOR** | an existing client can break | a field, message, service or call removed or renamed; a field's number or type changed; a call moved to the other token; a `oneof` variant removed |
| **MINOR** | anything a new client can use and an old one ignores | a new field, message, call, service or `oneof` variant; a new `enum` value; a new accessor or helper in a binding |
| **PATCH** | nothing on the wire changed | comments, documentation, a binding fixed without touching a proto, a dependency bump |

Two rules the table implies:

- **Field numbers are the contract.** Once published, a number is never
  reused for something else, and a removed field's number is reserved.
- **A new enum value is MINOR, and a reader must survive it.** proto3 carries
  values a reader cannot name as their number; the Rust accessors read those
  as the zero value, which is why every enum has one.

## Before 1.0

While the major version is 0, a MINOR bump may break, as semver allows, and
the changelog says so plainly when it does. The intent is still to break as
little as possible: the engine, the desktop, the Python package and any
other front end all read this contract, and a break costs every one of them
a change.

## What a release checks

A release runs from a GitHub workflow on the tag. Before anything publishes
it verifies:

- the protos compile;
- `buf breaking` against the previous tag reports nothing, or the bump is
  MAJOR;
- `cargo run -p generate` and the Python regeneration leave the tree
  unchanged, so the committed bindings match the protos;
- the Rust workspace builds, tests and documents with no warnings;
- the Python package builds and its tests pass, with an engine when one is
  available to the workflow.

Then it publishes `arvo-api`, then `arvo-client`, then the Python package,
in that order because each depends on the one before.

## What a release needs, once

- On the repository, the secret `CARGO_REGISTRY_TOKEN`: a crates.io API
  token allowed to publish `arvo-api` and `arvo-client`.
- On PyPI, a trusted publisher on the project `arvo-client`: owner
  `wjpin84`, repository `arvo-engine-api`, workflow `release.yml`,
  environment `pypi`. The job then needs no secret; its OIDC token is the
  credential. Create the `pypi` environment on the repository as well.
- Nothing for the GitHub release itself: the workflow's own token writes it.

The release workflow runs CI first (`ci.yml` is called, not copied), then
checks that the tag, `rust/Cargo.toml`, `python/pyproject.toml` and the
changelog agree, then publishes `arvo-api`, `arvo-client`, the Python
package, and the GitHub release with the changelog section as its notes.
`buf lint` runs with the protocol's own naming style allowed (a shared
`SessionId` or `Empty` across calls is deliberate; see `buf.yaml`), and
`buf breaking` compares against the previous tag when there is one.

## How to cut one

1. Decide the bump from the table above, looking at the diff of `protos/`
   since the last tag.
2. Set the version in both files.
3. Move the `Unreleased` section of `CHANGELOG.md` under the new version
   with the date, and say which bump it is and why.
4. Commit, tag `vX.Y.Z`, push the tag.
