# arvo (Python)

Arvo's research from Python: read research memory, run studies and
walk-forwards, and load the bar library into pandas. It talks to a running
`arvo-engine` through the research API of the
[contract](https://github.com/wjpin84/arvo-engine-api), which has no call
that fetches, touches a credential or trades.

```sh
pip install arvo-client        # the package is `arvo-client`; the module is `arvo`
```

```python
import arvo

engine = arvo.connect()                      # reads engine.json from the Arvo app data directory
found = engine.run_study("AAPL.RH", "sma_cross", author="script:first-look")
print(found.verdict)                         # read these three before any number
print(found.read_this_first)
for item in found.advice:
    print(item.severity, item.finding, "->", item.action)
print(found.detail["out_of_sample"])

prices = engine.bars("AAPL.RH")              # pandas DataFrame, read-only
```

**`author` is required, and it matters.** A run is saved as that author's
finding and deflated against everything the author has run, so a script
trying configurations until one passes does not make it pass.

## What is in the package

Two layers, and you can use either.

**`arvo`**, the client: `connect()`, `Engine`, and plain dataclasses for what
comes back (`Finding`, `Advice`, `Strategy`, ...). This is what a script
wants. It reads only `engine.json`, so it holds only the research token: it
cannot reach the control tier that fetches data, holds credentials or trades,
and that is by construction rather than by policy.

**`arvo.<domain>.v1`**, the generated stubs: one module per proto package
(`arvo.research.v1.models_pb2`, `arvo.research.v1.views_pb2`, and so on) and
the services under `arvo.services.v1`. Use these for anything the client
does not wrap, or to reach the control tier from a front end you are writing
yourself, with the token from `control.json`:

```python
import grpc, json, pathlib
from arvo.services.v1 import platform_pb2_grpc
from arvo.common.v1 import models_pb2 as common

root = arvo.default_root()
address = json.loads((root / "engine.json").read_text())["address"]
control = json.loads((root / "control.json").read_text())["token"]
platform = platform_pb2_grpc.PlatformStub(grpc.insecure_channel(address))
metadata = (("authorization", f"Bearer {control}"),)
for job in platform.ListJobs(common.Empty(), metadata=metadata).jobs:
    print(job.id, job.label, job.next_run_at)
```

Every message and field carries the comment written on it in the protos;
`help(models_pb2.StudyView)` shows what your editor does.

## Setup for development

```sh
cd python && uv sync
```

The tests start a real `arvo-engine` over a temporary directory, so they
need one built. Point them at it:

```sh
ARVO_ENGINE=/path/to/arvo-engine uv run pytest
```

Without it they are skipped, not failed.

## Regenerating the stubs

The modules under `src/arvo/*/v1` are generated from `../protos` and
committed. After a proto changes:

```sh
cd python && uv run python -m grpc_tools.protoc -I ../protos --python_out=src --grpc_python_out=src $(find ../protos -name '*.proto')
```

## Versioning

This package, `arvo-api` and `arvo-client` on crates.io share one version
with the protos they are generated from. The rules are in
[VERSIONING.md](https://github.com/wjpin84/arvo-engine-api/blob/main/VERSIONING.md).

## License

Apache-2.0.
