# virgo-agentic-dag

One large change, split into a graph of small ones, each implemented by its own coding agent and
landing as its own reviewable pull request.

A thousand-line pull request gets rubber-stamped. Ten hundred-line pull requests get read. This
package takes a task you have already decomposed, drives an agent per node, and keeps each node
moving — through review comments, red CI, and merge conflicts — until a human merges it.

## The one thing to understand

**The agent does the engineering. The framework decides who wakes up, and when.**

That line is the whole design. The framework never writes code, never commits, never pushes, never
opens a pull request, never replies to a reviewer. It reads what GitHub says about each node's pull
request, works out whether anything has happened that the node has not already been told about, and
if so resumes the configured Claude or Codex session carrying that news. Then it exits until the
next pass.

Everything follows from that split:

- **The framework holds no opinion it can be wrong about.** It stores a pointer to each node's pull
  request, never a copy of its state. Merged, approved, conflicted, red — all re-read from GitHub
  every pass.
- **A node owns one session, resumed.** The first wake opens it with the full instructions; every
  later wake resumes it and passes only what the node could not know — the comment just left, the
  checks that just failed, the paths that now conflict. Between wakes there is no process, only a
  session id.
- **Idle costs nothing.** A run waiting three days on a review holds no process and spends no
  tokens. A pass is a Python program the host starts and that exits in a second or two.
- **A human merges.** Always. The framework has no merge button and no way to earn one.

## How a node goes

```
PENDING ──► IN_PROGRESS ──► RESTING ──► MERGED
              (a session      (waiting on
               is running)     its PR)
```

1. **PENDING.** The node waits for every node it depends on to be merged.
2. **IN_PROGRESS.** The framework starts the node's configured agent in its own git worktree with a generated
   prompt. The agent writes the code, runs the gates, commits, pushes, and opens the pull request
   itself.
3. **RESTING.** The session has exited; the pull request is open. Each pass re-reads it and asks
   four questions — new comments? failing checks? conflicts? approved? Anything new and unanswered
   resumes the node's session carrying exactly that news. Anything already answered is ignored, so
   a node is never woken twice for the same thing.
4. **MERGED.** A human merged it. Dependents become eligible; the node's worktree is reclaimed.

Two states end a node early. **ERRORED** means the session crashed or ran past its deadline.
**NEEDS_HUMAN** means it ran cleanly but produced nothing publishable, was closed unmerged, or has
been woken as often as the run allows. Both stop the node's dependents rather than launching them
against a base that never got the change.

Neither is a dead end. `dagctl retry NODE --dag DAG` returns a stopped node to `PENDING`, and the
next pass starts it like any other pending node.

**SKIPPED** is a third ending, and a human is the only way into it. `dagctl skip NODE --dag DAG`
marks the node `SKIPPED` and returns to `PENDING` every node that stopped waiting on it, so the
rest of the run goes on. A node that is `IN_PROGRESS` or `MERGED` is refused.

A skipped node is taken out of the graph rather than counted as merged. Its dependents inherit its
dependencies: skip `B` in `A -> B -> C` and the graph becomes `A -> C`, so `C` still waits for `A`
to merge before it starts.

## Signals

The four questions in step 3 are the extension point. Each is a **signal**: a small class that
knows how to spot one kind of news, how to remember that it already reported it, how to word it for
the agent, and how to word it for a human in Slack.

| Signal | Fires when | Wakes the node |
|---|---|---|
| `comments` | a reviewer (not the agent) has written something new | yes |
| `checks` | a check has gone red on the current head | yes |
| `conflict` | the branch no longer merges into its base | yes |
| `approval` | someone approved it | no — announces only |

### Watermarks

A **watermark** is the one string a signal leaves behind to record the last version of the world it
reported. Next pass, the signal recomputes that string from what GitHub now says and compares. Same
string, no news. Different string, news — and the new value becomes the watermark.

| Signal | Watermark |
|---|---|
| `comments` | the timestamp of the newest comment reported |
| `checks` | the head commit joined with the sorted names of the checks failing on it |
| `conflict` | the head commit the conflict was reported against |
| `approval` | the head commit that was approved |

The `checks` watermark is the instructive one. It is not "CI is red" but *which commit failed which
checks* — so a node that pushes a fix and fails the same check again is told, because the commit
changed, while a pass that merely re-reads the same failure says nothing.

Watermarks live together in one JSON blob keyed by signal name, which is why **adding a fifth
signal needs no migration and no change to the pass**. Write the class, add it to the list.

## Defining a run

One TOML file. `dag.toml` describes the graph and how the host runs it:

```toml
name = "auth-split"                        # the run's name, and its home under ~/.virgo-dag
project_root = "/path/to/clone"            # the checkout agents work in; defaults to $PWD
workspace_path = "/path/to/worktrees"      # where per-node worktrees are cut
base_branch = "develop"                    # what pull requests target
executor_agent = "claude"                  # the agent every node inherits
agent_account = "acme-bot"                 # the agent's own login, so its comments never wake it
max_workers = 2                            # how many sessions may run at once
tick_interval_seconds = 300                # how long the host waits between passes
slack_channel = "C0123456789"              # omit for no Slack
sse_url = "http://127.0.0.1:8787/events"   # where `watch` subscribes

[caps]
node_wakes = 12                # how often one node may be woken before it asks for a human
node_recoveries = 3            # how many recovery attempts a node gets before it is left to a human
session_turns = 120            # Claude's turn cap; Codex uses the time limit below
session_timeout_seconds = 3600 # how long either provider may run before being stopped

[[nodes]]
id = "TOKENS"
name = "Iris"                                   # what to call the agent in Slack
title = "Issue and verify signed tokens"
instructions = """
Create src/auth/tokens.py with ...
Run the linter and the test suite before you finish.
"""

[[nodes]]
id = "MIDDLEWARE"
name = "Juno"
title = "Reject unsigned requests at the edge"
depends_on = ["TOKENS"]
instructions = """
..."""
```

Every top-level default a node does not override applies to it: `project_root`, `workspace_path`,
`executor_agent`, and `base_branch` are all read per node first and from the graph second.

### Choosing Claude or Codex

Set `executor_agent` to `"claude"` or `"codex"`. The top-level value selects the recovery and
learning-extraction agents as well as the default for nodes. A node override selects that node's
agent for its initial launch and every later wake, including wakes requested by recovery:

```toml
name = "mixed-agents"
executor_agent = "codex"

[[nodes]]
id = "API"
instructions = "Implement the API changes."

[[nodes]]
id = "TESTS"
executor_agent = "claude"
depends_on = ["API"]
instructions = "Add the integration tests."
```

Here Codex handles `API`, recovery, and learning extraction; Claude handles `TESTS`. When the
top-level value is absent, it is `claude`, so a graph written before Codex support runs as it did.

Install and authenticate each selected CLI on the machine running the graph, and make its binary
available on the scheduled job's `PATH`. Codex runs through `codex exec --json` and resumes the
thread ID it emits, using the model from the CLI configuration. The launcher sets reasoning effort
to `high` for new and resumed Codex sessions. Claude runs unattended with its
permission checks bypassed. The launcher sets effort to `max` for new and resumed Claude
sessions. Codex runs in its `workspace-write` sandbox with `approval_policy`
set to `on-request` and `approvals_reviewer` set to `auto_review`, so a command the sandbox
blocks, such as a push over the network, is an escalation that Codex's automatic reviewer
decides. Only run trusted graph instructions in an environment where that access is appropriate.

`caps.session_timeout_seconds` applies to both providers. `caps.session_turns` applies only to
Claude; Codex exec has no corresponding turn-limit flag. Both receive the run's saved learnings.

A conversation cannot move between providers. After changing a stopped node's executor, use
`dagctl retry NODE --reset --dag DAG` to start a fresh conversation in its existing worktree.
Codex execution transcripts are retained beside the worktree in `<node>.sessions/`, including
across wakes and worktree reclamation. For `adopt --session`, supply a Codex thread ID when the
selected provider is Codex; the dashboard records its new executions, not its pre-adoption history.

### Node instructions

A node's `instructions` are the only thing the agent is given, so name the files it may change in
there. Nothing bounds a node to those files afterwards — nothing inspects the diff, and nothing
compares one node's files against another's. What catches a node that wandered is the human reading
its pull request.

Every node needs an executor agent, its own or the graph's, so a rollup that writes no code fails
validation with `missing-executor`. Fan-in is an ordinary node that depends on the wave and carries
its own `instructions`.

### Where a run keeps its files

Everything a run owns lives under `~/.virgo-dag/<name>/`: `db.sqlite3` (unless the graph names a
`db_path`), the `.env.local` a scheduled pass reads its tokens from, and the `start.log` and
`watch.log` the host job and the watcher write to.

## Running your first graph

1. **Write `dag.toml`** — one `[[nodes]]` block per pull request you want, with `depends_on` edges
   and `instructions` that specify the change.
2. **`dagctl validate --dag dag.toml`** — is the graph legal.
3. **`dagctl preview --dag dag.toml`** — see it as a diagram and an agent count before spending
   anything.
4. **`dagctl start --dag dag.toml`** — one pass now, and a host job that keeps passing until the
   run settles.
5. **Review the pull requests as they arrive, and merge them.** Each merge unblocks dependents on
   the next pass, and the run retires its own host job when the last node settles.

Steps 2 and 3 cost nothing and contact nobody. Everything after step 4 happens whether or not you
are at the machine.

### Invoking it

Clone the repository and install the package with uv:

```sh
git clone https://github.com/ioesandeep/agentic-dag.git
cd agentic-dag
uv sync --extra web
uv run dagctl --help
```

The package requires Python 3.13.12 or a later Python 3.13 release. uv installs a compatible
interpreter when needed. Run the commands below with `uv run dagctl` from this checkout.

## dagctl

`dagctl` is the whole framework. There is no daemon and no service to install: every verb reads the
graph, does one thing, and exits. One of them stays in the foreground on purpose — `watch` holds an
event stream open.

The command you run is `start`. The rest are for looking, checking, and changing the graph.

| Command | What it does |
|---|---|
| `start --dag DAG` | One pass, then the host job that re-runs it every `tick_interval_seconds` until the run settles. Starts the watcher too when the graph names an `sse_url`. **This is the one you run.** |
| `tick --dag DAG` | One pass on its own, scheduling nothing. What `start` runs, and what the host job runs. |
| `abort NAME` | Stop a run for good: kill its agents, stop its watcher, and retire its host job. Named, not described, so a broken graph cannot block it. |
| `watch NAME` | Hold the event stream open and fire a pass within a debounce window of a pull request event. `start` spawns this; run it by hand to watch in the foreground. |
| `retry NODE --dag DAG` | Send a stopped node back to work: an `ERRORED` or `NEEDS_HUMAN` node returns to `PENDING` for the next pass to start. Refuses a node in any other state. |
| `skip NODE --dag DAG` | Take a node out of the run: it becomes `SKIPPED`, its dependents inherit its dependencies, and every node that stopped waiting on it returns to `PENDING`. Refuses a node that is `IN_PROGRESS` or `MERGED`. |
| `stop NODE --dag DAG` | Stop an `IN_PROGRESS` node's running session. |
| `status NAME` | What the named run's database records: each node's state, every open agent session, the watcher, and the scheduled job. Then, when the graph names an `sse_url`, whether the bridge behind it answers. |
| `log NAME` | Every transition the named run has recorded: each entry's node, state, and note, in the order they were written. |
| `validate --dag DAG` | Check the graph loads and is legal: no cycles, no unknown or self dependencies, no duplicate ids, every node resolving to an executor agent, and every `pr` an http url. |
| `adopt --pr URL --dag DAG` | Add a node that takes over a pull request that already exists to a run that is already going. |
| `preview --dag DAG` | Print the graph as a mermaid diagram plus the agent count. A node that takes over a pull request is marked `(adopted)`. Reads nothing, writes nothing, contacts nobody. |
| `serve` | Hold a read-only web api open over the runs this host records. Binds loopback on purpose and changes nothing. Needs the `web` extra. |

### Options

`start`, `tick`, `validate`, and `preview` accept `--dag PATH`, while `retry`, `skip`, and
`stop` accept `NODE --dag PATH`.

`abort`, `watch`, `status`, and `log` take the run's name as a positional; `watch` also takes
`--sse URL` to override the graph's `sse_url`.

`serve` names no run. It takes `--host` (default `127.0.0.1`) and `--port` (default `8788`).

`adopt` takes `--pr` (required, the pull request's url) and `--dag` (required, the run's graph
file), then optionally `--executor claude|codex` (defaults to the DAG's executor), `--id` (coined from the pull request when
unset), `--session` (an agent session to resume on the first wake), and `--project-root` and
`--workspace` (the adopted node's own checkout and worktree home, falling back to the dag's).

### Exit codes

| Code | Meaning |
|---|---|
| `0` | the pass did its work; the run continues |
| `1` | the command failed — a graph that will not load, a platform call that would not answer |
| `3` | **the run is complete.** Every node has settled |
| `75` | the run is busy: another pass already holds it. Not an error — the overlapping pass simply did nothing |

Exit `3` is how a run ends itself: the pass that sees it retires the host job and kills the watcher.

### Environment

| Variable | Read by | For |
|---|---|---|
| `SLACK_BOT_TOKEN` | `start`, `tick` | posting to `slack_channel`. Leave it unset and the framework says nothing |
| `GITHUB_WEBHOOK_SECRET` | `dag-webhook-sse` | verifying webhook signatures |
| `GH_TOKEN` | `gh`, and every agent session | the identity platform reads and agent pushes act as. The whole environment is handed to the session |

A scheduled pass reads no shell profile, so put these in the run's `.env.local`, which every
command loads from the run's home.

## The two loops

**The host job is the correctness net.** `start` registers a job that re-runs it every
`tick_interval_seconds`, does one full pass, and exits. If everything else fails, the next pass
still catches up. Every minute of latency is the worst that a missed webhook costs.

**Webhooks are the accelerant.** `watch` fires a pass within a debounce window of a GitHub event
instead of waiting for the next scheduled one. In practice this is the difference between an agent
answering a review comment while you are still looking at the pull request and answering it minutes
later.

### The SSE bridge

GitHub cannot deliver a webhook to a laptop, and a long-lived watcher should not be a web server.
So delivery and reaction are two processes, joined by server-sent events:

```
GitHub ──webhook──► tunnel ──► dag-webhook-sse ──SSE──► dagctl watch ──► one pass
                               (POST /webhook)          (GET /events?topics=…)
```

`dag-webhook-sse` is the package's second console script. It receives GitHub deliveries, verifies
the signature, works out which pull requests the delivery is about, and re-broadcasts the event
name to the subscribers watching those pull requests:

```sh
GITHUB_WEBHOOK_SECRET=... dag-webhook-sse --host 127.0.0.1 --port 8787
```

| Route | Purpose |
|---|---|
| `POST /webhook` | GitHub's delivery endpoint. Rejects anything whose signature does not verify |
| `GET /events?topics=owner/repo#12,…` | the SSE stream a watcher subscribes to, scoped to its own pull requests. This is what `sse_url` points at |
| `GET /healthz` | liveness, for whatever supervises it |

Point a tunnel at it (ngrok, Cloudflare, a bastion) and register that public URL as the
repository's webhook.

**The events carry no state — only "go look".** A delivery says `pull_request_review` and nothing
more; the watcher reacts by running the same pass the host job would run, which re-reads everything
from GitHub anyway. That is why the bridge can stay this small: it needs no delivery guarantees, no
replay, no ordering, and no persistence. A dropped event costs one interval of latency. A duplicated
event costs one wasted read. Neither can corrupt a run.

### Nothing supervises the bridge

A tunnel and `dag-webhook-sse` are machine-scoped and you start both by hand; nothing restarts them
if they die. **The run does not break** — the host job is the correctness net and keeps passing on
its own schedule — but the fast reactions stop. Nothing brings them back for you; `status` reads the
bridge's `/healthz` and prints whether it answered, so you can see it is gone and restart it. The
watcher itself is supervised: `start` spawns it, records its pid, and `abort` and the completing
pass both kill it.

## The read-only web api

`dagctl serve` opens a read-only HTTP window on the runs this host records. It is a second entry
point over the same services, not a second implementation: routes name the surface, controllers
answer them, and every collaborator is built by the application context the CLI already uses.

| Route | Purpose |
|---|---|
| `GET /api/runs` | one summary per run this host records |
| `GET /api/runs/NAME` | one run's nodes, dependency edges, and audit tail. `404` when no run answers to the name |
| `GET /healthz` | liveness, for whatever supervises it |

The routes and their response shapes are the contract; the answers are stubs until the run readers
land, so the listing comes back empty and the detail comes back fixed.

**No route changes a run.** This server cannot start, advance, adopt, or abort anything. That is a
design decision, not an omission — writing to a run stays on the CLI, where the run lock is.

**`fastapi` and `uvicorn` are an extra, not core dependencies.** Every other verb runs without them.
`serve` is the only one that needs them, and it names the install command and exits `1` when they
are absent:

```sh
uv sync --package virgo-agentic-dag --extra web
uv run --package virgo-agentic-dag dagctl serve
```

**It binds loopback on purpose.** Agent sessions on this host run with broad permissions, so
widening even a read-only window onto them is the operator's explicit decision: pass `--host` to
make it one.

**This is not the SSE bridge.** `dag-webhook-sse` stays what it is — a wake hint that carries no
state and reads nothing — and it is a separate process on a separate port. Both answer `/healthz`,
and the bridge line in `dagctl status` is about the bridge, not about this server.

## Adopting a pull request that already exists

A node does not have to start from nothing. Point one at a pull request somebody already opened and
the agent takes it over — answering its comments, fixing its CI, resolving its conflicts. Say so in
the graph file:

```toml
[[nodes]]
id = "TOKENS"
pr = "https://github.com/acme/virgo/pull/412"
depends_on = ["SCHEMA"]
```

The node waits on its dependencies like any other. When they merge, the pass cuts its worktree from
the pull request's head branch and launches the agent there, exactly as it launches a node that
starts from nothing, so a stack of pull requests that already exist is an ordinary graph. `validate`
refuses a `pr` that is not an http url — the alternative is a run that silently opens a second pull
request for work that already has one.

Adopt one into a run that is already going with the command:

```sh
dagctl adopt --pr https://github.com/acme/virgo/pull/412 --dag dag.toml
```

Either way the node lands **in progress**, with an agent working in a worktree cut from the pull
request's head branch. A node the graph declares is launched with the `instructions` in the graph
file; one the command adopts declares none, so it is launched with a standard takeover prompt that
tells it to read the pull request, answer its review threads, resolve its conflicts, and fix its
checks. When that session ends the node rests, and from there the resting handler owns it —
comments wake it, the merge ends it.

`--session` is the exception. Give the command an agent session id and the node rests on that
session from the start, launching nothing, and its first wake resumes that conversation.

An adopted node counts against `max_workers` like any other, because it holds a session in progress
from the moment it is adopted.

The url names both the pull request and its repository, so adopt needs no repository configuration:
it reads the pull request's details from the platform, and when neither the named nor the inferred
checkout belongs to the url's repository, it clones that repository into the workspace and cuts the
worktree from the clone. A checkout named explicitly with `--project-root` that belongs to another
repository is an error.

## What a human sees

One Slack thread per node, in sentences rather than in the controller's vocabulary:

```
🎉 ✅  Agent Iris started working on `Issue and verify signed tokens`
       Agent Iris opened pr#412
       pr#412 has failing checks: `release-note`. Looking into it
       Agent Iris pushed a1b2c3d4 to pr#412
       The checks on pr#412 are green again
       2 comments were added to pr#412. Addressing them now
       Addressed 2 comments on pr#412 in e5f6a7b8
       pr#412 has merge conflicts with the base branch. I will try to resolve them
       Agent Iris pushed 9c0d1e2f to pr#412
       pr#412 merges cleanly again
       sandeep merged pr#412. Agent Iris will wind down. Thank you!
```

A commit hash appears only when the agent actually made one. When it answered a reviewer and
changed nothing — because it disagreed, and said why — the thread says so and names no commit.

## The web console

The frontend lives in `web/`. It has two screens: every run on this host with its node counts, and
one run's graph, where clicking a node opens its pull request, agent, wakes, cost, and history.

```sh
cd web
npm install
npm run dev
```

Development needs Node 20 or newer. Every screen reads the api over `/api`, which a Next rewrite
proxies to `dagctl serve` on `127.0.0.1:8788`, so start that server alongside `npm run dev`.

## The store

One SQLite file per run, at `db_path` or `~/.virgo-dag/<name>/db.sqlite3`. It holds the nodes and
their states, the agent per node and the sessions it has spent, the worktrees cut for it, the Slack
threads, the host job, the watcher, each failure a node had and the recovery decided for it, each
session of the recovery agent with the node ids it was handed, and an append-only `audit_entries`
table of every transition with the note that explains it.

The row *is* the framework's memory. What is deliberately **not** in it: whether a pull request is
merged, approved, conflicted, or red. Those are GitHub's to know, and are re-read every pass.
Storing an identity is safe because it cannot go stale; storing a lifecycle guarantees the day a
human clicks merge and the framework carries on as if they had not.

A run is held by an exclusive file lock on a sidecar beside its database, taken without blocking. If
a pass overruns and the host job fires the next one, the second exits `75` and does nothing.

`status` and `log` read that database by run name.

## Where the code lives

```
domain/       entities, value objects, and the interfaces. No I/O.
  infra/      what the framework needs an outside system to do: agent/, code/, host/, locking/,
              messaging/, scheduling/, spec/, streaming/, workspace/
  persistence/ the repository interfaces and the entities they store
  service/    the model's own logic: building a graph, validating it, publishing an event
services/     one class per capability: node state handlers, signals, loading, watching,
              notifications, scheduling, listening, adoption
infra/        every implementation of those interfaces, one directory per capability: agent/,
              code/, host/, locking/, notification/, persistence/, scheduling/, streaming/,
              workspace/
api/          entry points: cli/ is dagctl, web/ is the read-only web api and its
              routes, controllers, and response entities
server/       the webhook receiver and SSE hub
bootstrap/    the application context and the one place every bean is declared
labels/       every sentence dagctl shows a person, in one catalog
utils/        the one helper that fills a label's placeholders
```

### Interfaces and their implementations

Every interface the framework needs an outside system to implement is declared in `domain/`, and the
class that implements it lives outside `domain/`. `CommandRunner`, `NodeRepo`, `CodeRepo` and
`Scheduler` are the interfaces; `SubprocessCommandRunner`, `SqliteNodeRepo`, `GitHubCodeRepo` and
`LaunchdScheduler` are their implementations, all of them under `infra/`.

Two homes inside `domain/`, told apart by what the interface is for. `domain/infra/<capability>/`
declares what the framework needs an outside system to do — run the agent, read the git host,
register a job, sleep. `domain/persistence/repos/` declares the repository interfaces, beside the
entities they store.

`infra/` is laid out to match, so knowing the interface tells you the directory: `EventStream` is
declared in `domain/infra/streaming/` and implemented in `infra/streaming/`, `Sleeper` in
`domain/infra/host/` and implemented in `infra/host/`. Two things break the symmetry. Everything
`domain/infra/messaging/` declares — the dispatcher, the subscriber, and the `JsonPoster` they send
through — is implemented in `infra/notification/`, the same group under a different word. And
`DagLoader` has no implementation under `infra/` at all: it is `TomlDagLoader`, in
`services/loading/toml/`.

Not every abstract class is one of these. `PrSignal` and `GraphValidator` are abstract too, but
nothing outside the process implements them — they are internal strategy families, so each sits with
its own implementations: `PrSignal` with the four signals in `services/signals/`, `GraphValidator`
with the four graph rules in `domain/service/validators/`.

Imports point one way, toward `domain/`. Every service is constructor-injected and programs to an
interface, and `bootstrap/register_beans.py` is the single place that says how each one is built.
Run the package checks from the repository root:

```sh
uv sync --extra web
uv run ruff check .
uv run ruff format --check .
uv run python tools/block_padding.py src tests
uv run mypy src/virgo_agentic_dag
uv run pytest
uv build
```

The default test run excludes tests that call live providers.

## Decisions worth keeping

Seven facts that were learned the expensive way and are easy to undo by accident.

**A session id is only ever created by the launch that uses it.** The framework must never store an
id no agent process has opened. Adoption once seeded a node resting on a minted id, and every wake
of that node died in seconds on "No conversation found" while the node read healthy in `status` —
because a wake resumes a conversation and only a launch creates one.

**Kill the process group, not the process.** A bare pid-kill leaks the grandchildren an agent
spawned — a watch-mode test runner holding a lock that fails the next node's install.

**Merged means the flag and the ancestry.** GitHub reporting a merge is not enough. Fetch after that
observation and confirm the merge commit is an ancestor of the base, or you will launch a dependent
against a base that is missing the thing it depends on, silently.

**Cut the worktree from what the remote holds, not from the clone.** Nothing else in a run fetches,
so the clone's own branches are only as fresh as the last human to touch it — and a branch that
lives only on the remote does not resolve by its bare name at all, which is every branch a node
adopts. Provisioning fetches the ref and cuts from what came back, falling back to the clone only
when there is no remote to ask.

**A node keeps its session across wakes.** This was tried the other way first — every wake a fresh
`claude -p` with a reconstructed prompt — and round two of a review reverted round one, because the
second session had never seen the first. A node now resumes its own session and is passed only what
it could not know. What must never come back is the framework *reconstructing* a node's history for
it: pass the new facts, not a retelling.

**Finish the teardown before the kill.** A completing pass drains its notifications and retires its
own job before it kills the watcher, because the watcher may be the process running that pass.

**A check with no conclusion is not a passing check.** Do not call CI green while it is still
queued.

## What this does not do

It does not decompose the task for you. It takes a graph you have already cut and drives it. If a
node is not genuinely independently mergeable, its pull request will not build alone, and no
scheduler fixes that — the riskiest part of the system is still the human conversation that decides
what the nodes are.

It does not review code, and it cannot merge. Branch protection on the target repository is what
guarantees a human read the change.

It runs on one host, against one clone, with a single-writer run lock. That is a deliberate ceiling,
not an oversight.

## Status

Pre-alpha. The graph, the passes, the host job, the watcher, and abort all work end to end; it has
not yet been pointed at production work.
