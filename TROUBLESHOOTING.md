# Troubleshooting

Every error below was hit for real while building this toolkit, in this order.
If you are stuck, `python3 c8lab.py` first. It checks auth, the ledger and your
parties in one go, and tells you which layer is broken.

## Setup

### `Bad CPU type in executable` when installing Daml

Apple Silicon, no Rosetta. The SDK is an Intel binary.

```bash
softwareupdate --install-rosetta --agree-to-license
```

### `daml build` works but `daml test` says "Unable to locate a Java Runtime"

You edited `~/.zshrc` but are still in the old terminal. The compiler shells out
to `java`, which is not on the old shell's PATH. Open a new terminal, or
`source ~/.zshrc`.

### LocalNet web pages load but nothing works

Docker cannot bind-mount from `Documents`, `Desktop` or `Downloads`. The web UI
containers need no mounts so they start; postgres, canton and splice all die.

```
error while creating mount source path '/host_mnt/Users/.../Documents/...':
operation not permitted
```

Copy the localnet directory to `~/localnet` and run from there.

### nginx will not start, `Bind for 0.0.0.0:3000 failed`

Something else owns port 3000. The ledger still works, but the scan registry is
unreachable, so **transfers will fail**. Restart with:

```bash
export APP_PROVIDER_UI_PORT=3001
```

### `PARTY_HINT is required`

It must look like `word-word-number`, e.g. `myteam-dev-1`.

## Auth

### 401 on every call

The Ledger API is authenticated. On LocalNet the token is a self-signed HS256
JWT with the secret `unsafe`. `c8lab.py` mints it for you.

A 401 from a fresh LocalNet is also the correct "it is up" signal before you have
a token. Do not panic at it.

### 403, with a token that works elsewhere

**This is the one that wastes the most time.** Your token proves who you are. It
does not grant you anything over a party's contracts. Two separate things.

The user in the token's `sub` needs rights on that party. On LocalNet use
`ledger-api-user` or `app-user`. Or grant them:

```
POST /v2/users/{userId}/rights
{"rights":[{"kind":{"CanActAs":{"value":{"party":"..."}}}}]}
```

`c8lab.py` has `grant_act_as(user, party)`.

## Parties

### `Party already exists`

You ran an allocate script twice. Look for an existing party with that hint
instead. `allocate_party()` does this.

### `NO_SYNCHRONIZER_ON_WHICH_ALL_SUBMITTERS_CAN_SUBMIT`

You are submitting as a party this node does not host. A node lists every party
it has heard about, including other people's. Only use ones where `isLocal` is
true.

## Reading data

### Empty holdings, HTTP 200, no error

You used a `TemplateFilter`. `Holding` is a Daml **interface**, not a template,
so the filter matches nothing and returns an empty list that looks exactly like a
zero balance.

Use `InterfaceFilter` with `includeInterfaceView: true` and:

```
#splice-api-token-holding-v1:Splice.Api.Token.HoldingV1:Holding
```

### My indexer shows nothing, or a zero balance

You streamed updates from the current ledger end. That gives you the future, not
the past. Query the **active contract set** first for the balance, then stream
forward from that same offset to stay current.

## Transfers

### The transfer succeeded but the receiver has no money

Check `transferKind` in the result.

- `direct`: the receiver had a live preapproval, money moved.
- `offer`: no preapproval. A `TransferInstruction` was created and **the receiver
  must accept it**. Their balance does not change until they do. Nothing is
  broken.

Creating a preapproval is not instant. You create the proposal, and the
validator's automation accepts it a moment later. Create it, wait, then transfer.

### `deadline-not-exceeded ... Lock.expiresAt`

You passed a **locked** holding as an input to a transfer. Locked holdings show
up in your balance but cannot be spent until the lock expires.

A holding gets locked when it is escrowed for a pending transfer offer. So if
you send an offer that nobody has accepted yet, part of your balance is locked
and your next transfer fails, with an error that says nothing about locks being
the problem.

Filter them out. `holdings()` returns a `locked` flag on every entry:

```python
spendable = [h for h in holdings(me) if not h["locked"]]
```

`transfer()` in `c8lab.py` does this. If you build your own, do it too.

### `LOCAL_VERDICT_LOCKED_CONTRACTS`

Contention. Another in-flight transaction is using the same holdings. Holdings
are UTXOs: a transfer archives the ones it spends, so two transfers touching the
same holding fight and one loses.

Retry after a moment. If it happens constantly, you have too few holdings for
your concurrency, which is a real Canton problem and the subject of one of the
challenges.

### The registry call fails or times out

On LocalNet the registry is the scan app behind nginx, routed by Host header.
Two things break it: nginx not running (see the port 3000 item above), and
`scan.localhost` not resolving. `c8lab.py` sends `Host: scan.localhost` to
`localhost:4000` to avoid the DNS problem.

### I want to build the transfer by hand without the registry

You cannot. Privacy means you cannot see the issuer's configuration contracts,
so the registry has to hand them to you as disclosed contracts for that one
transaction. That is the design, not a limitation of this toolkit.
