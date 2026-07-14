# Initial hardware topology

The following topology is an owner-supplied project input. It is not a `MEASURED`
inventory or a performance result.

```text
Node A (M5 Pro, 48 GB) ===== Node B (M5 Max, 48 GB)
        \\                         //
         \\       direct         //
          Node C (M5 Max, 48 GB)
```

Each pair has a direct Thunderbolt 5 link: A-B, A-C, and B-C. Each node is declared to
have 1 TB internal SSD and to run the newest macOS available to it. Aggregate declared
physical memory is 144 GB. Node A is the logical control plane but may store weights
and compute. Nodes B and C are expected to perform more heavy computation, subject to
measurement.

## Unknown until inventory

The project must collect rather than assume:

- exact chip and GPU configuration, memory bandwidth, and available unified memory;
- macOS version and build, relevant firmware, compiler, and power configuration;
- internal SSD capacity available to QW5 and representative cold-tier behavior;
- Thunderbolt controller and route identity without publishing device serial numbers;
- negotiated link behavior, latency, throughput, copy counts, concurrency, errors, and
  thermal effects;
- time synchronization quality and tool versions.

The bootstrap `qw5 inventory` command is deliberately limited to compiler-target
metadata and labels its schema `bootstrap-target-v1`. It is read-only, but its output
is not a three-node hardware manifest and must not be cited as one.

## M1 inventory design

The full read-only probe will emit a versioned, deterministic-key-order manifest with
public-safe node identity, source command or API for each fact, collection timestamp,
units, tool version, and explicit unavailable/error fields. A separate reviewed schema
will distinguish owner-declared inputs from probed facts and benchmark measurements.

Inventory output will exclude credentials, usernames, home paths, serial numbers,
network secrets, and unrelated process or filesystem data. Committed reproducibility
manifests will use stable node aliases A, B, and C.

## Link characterization plan

Measure A-B, A-C, and B-C in both directions. For each direction, cover payload sizes
relevant to state transfer and expert dispatch; record transport, checksums, bytes,
messages, copies, synchronization, retries, latency distribution, and throughput. Run
links alone and in representative simultaneous combinations.

Peer-to-peer transfers are preferred when `MEASURED` evidence supports them. The
logical control plane is not a mandatory data relay. Prefill and decode traffic models
remain separate, and rejected topology assumptions are preserved as negative results.
