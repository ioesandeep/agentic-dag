---
name: agentic-dag
description: Decompose one large engineering task into a directed-acyclic graph of smaller tasks and drive coding agents to implement them in dependency order, each node producing one small, independently reviewable pull request. Use when a change is too big for a single reviewable pull request. A deterministic cron-driven controller decides which node wakes and when; coding agents do the engineering and publish their own pull requests.
---

# agentic-dag

Pre-alpha. `README.md` is the full account of how the framework works; this file is what you need
to use it. Do not invoke as a finished tool yet.

## Model

Two phases:

1. **Design (interactive, once, human-approved).** Decompose the input into a graph specification —
   nodes with file ownership, dependency edges, per-node instructions and definition of done. The
   human refines and approves. This is the part the framework cannot do for you, and the part that
   decides whether the run works at all.

2. **Execute (deterministic).** A cron-driven Python controller (`dagctl tick`) re-reads each node's
   pull request from GitHub, wakes that node's coding session whenever something has happened it has
   not already been told about, and unblocks dependents once a human merges. The agent writes the
   code, runs its own gates, and opens its own pull request. A node owns one session and resumes it,
   receiving only the facts it could not know; the framework never retells a node its own history,
   and never acts on an agent's claim about the state of the world.

## Cutting the graph

The framework drives whatever graph it is given. It cannot rescue a bad cut, so spend the effort
here.

- **Every node must be independently mergeable.** Its pull request has to build, pass CI, and be
  reviewable on its own, against the base branch as it stands. If a node only makes sense once
  another has landed, that is a dependency edge, not a hope.
- **An edge means "needs merged", not "relates to".** Edges serialize work. Add one only when the
  later node genuinely cannot build without the earlier one in its base.
- **Name the files the node will touch, in its `instructions`.** Nothing compares one node's files
  against another's, so two unordered nodes that touch the same file will conflict on whichever
  merges second.
- **`instructions` are a specification, not a hint.** Name the file to create, the signature to
  expose, the behavior at the edges, where the tests go, and which gates to run before finishing.
  The agent has the repository but not your intent.
- **Name the node's agent.** `name = "Iris"` is what a human sees in Slack; a run of anonymous ids
  is much harder to follow.
- **Make the fan-in an ordinary node.** Every node needs an executor agent, so a rollup that writes
  no code fails validation; give the fan-in its own `instructions` and depend it on the wave.

Prefer a few well-cut nodes over many thin ones. Each node costs a session, a pull request, and a
human's review attention.

## Running it

```sh
dagctl validate --dag dag.toml           # legal graph
dagctl preview  --dag dag.toml           # mermaid diagram + agent count, no side effects

dagctl start --dag dag.toml              # one pass, then a host job that keeps passing
dagctl abort <name>                      # kill the run's agents and unschedule it
```

`start` runs one pass and registers the host job that re-runs it until the run settles, so nothing
has to be put on cron by hand. A pass exits `3` when every node has settled, which is how a run
retires its own job, and `75` when another pass already holds the run.

See `README.md` for the signal model, the SSE bridge, adoption of existing pull requests, the store,
and the full option reference.
