# Challenges

A third track, for people who would rather not write code, is coming. We will
announce it on the day. If that is you, turn up anyway.

## Before you start

Everything you need is in the toolkit:

**<https://github.com/Cantor8/hackathon-toolkit>**

Read `SETUP.md`, then `README.md`. It has a working Python client for the
Canton ledger, a Daml starter project, and a troubleshooting file with every
error we hit while building it.

We will give you access to a shared Canton network on the day. You do not need
to run your own.

# API track

Python, JavaScript, whatever you like. No Daml required. You talk to the Canton
ledger over HTTP.

## A1. Build a scanner

**Canton has no block explorer, and it cannot have one.** A node only holds data
for the parties it hosts. There is no query for "everything", by design.

So if anyone wants a dashboard, a balance history, or an activity feed, someone
has to build an index: a service that follows the ledger and keeps its own
database of what it is entitled to see.

Build one.

**What to build**

- Connect to the Ledger API and read the active contract set for a set of
  parties. That gives you balances.
- Then stream updates forward from that point, so it stays current.
- Store it. SQLite is fine.
- Serve it: balance for a party, and a history of transfers.
- Survive a restart. Save your offset and resume, do not re-read everything.

**A good submission**

Balances correct, a live stream on top, and a restart that resumes from where
it stopped. Transfer history on top of that.

**Traps**

- Query the active contract set *first* for balances. If you only stream from
  the current end of the ledger you get the future, not the present, and your
  balances will read zero.
- `Holding` is a Daml *interface*, not a template. Filter for it with an
  `InterfaceFilter`. A template filter returns an empty list and a 200 OK, which
  looks exactly like a zero balance.
- Transactions are trees, not a flat list of events. You have to walk them.

**How it is judged**

Correctness first: do the balances match the ledger. Then does it resume
cleanly after a kill. Then how much of the history it can reconstruct.

**Where to start**

`c8lab.py` in the toolkit already reads balances. That is step one of maybe
eight. The Ledger API reference is at
<https://docs.canton.network/sdks-tools/api-reference/ledger-api>.

## A2. Ledger versus database: catch the drift

Every application that talks to a blockchain keeps its own database copy of what
it thinks happened. The two drift. Rows say `submitted` forever. Contracts exist
that your database has never heard of. Nobody notices until a user complains.

This is a real problem we have, and we fix it today with one-off scripts.

**What to build**

- A small service that holds an invariant and checks it continuously. For
  example: *every row marked submitted must have a matching active contract
  within 60 seconds.*
- Make the scan bounded and resumable. Naive full scans time out on real data.
- When it finds drift, do something useful: retry, requeue, mark it terminal,
  or escalate. Log every action.
- Expose metrics: how much drift, how old, how often you fixed it.

**A good submission**

One invariant, checked continuously, and a demo where you deliberately break
something and it gets caught.

**How it is judged**

We will inject drift in front of you and see if you catch it, and how fast.
Then we will ask what happens on a database with a million rows.

**Where to start**

You need a live feed of transactions to reconcile against. We will point you at
one on the day.

# Daml track

You write smart contracts. The Daml starter in the toolkit builds and its tests
pass, so you have something working from minute one.

## D1. A spend-limited wallet for an AI agent

Agents increasingly need to pay for things. The answer everywhere right now is
"give the agent a hot key", which is indefensible. If the agent goes wrong, or
someone talks it into something, there is nothing between it and your money.

Canton's authorisation model is a much better fit. Build the wallet an agent
should have.

**What to build**

- A mandate contract: this agent may spend up to X, only with these
  counterparties, until this date.
- **The limits must be enforced in Daml, not in your backend.** This is the
  whole point of the task.
- Instant revocation that the agent cannot block or delay.
- An audit trail: every action the agent took, and which permission allowed it,
  readable by a human.
- Then show it working. An agent buying something on its own, and the statement
  afterwards.

**A good submission**

A total spend cap, revocation, and tests proving that a charge under the cap
succeeds, a charge over it fails, and a charge after revocation fails. Then
anything on top: an allow-list of counterparties, per-period limits, a
frontend, an MCP server so a language model can hold the wallet.

Worth doing the total cap before per-period limits. Per-period looks simple and
turns into date arithmetic.

**How it is judged**

We will try to make your agent exceed its cap, and pay someone it should not.
Both must fail **on the ledger**, not in your API. Be ready to show us the line
of Daml that stops it. Then we will revoke and try again.

**Where to start**

`daml-starter/Mandate.daml` in the toolkit is exactly this shape, with passing
tests. Copy it and go. It records charges but does not move money yet, so
that is your first real step.

# Accelerator problems

These are bigger than one day. They are real problems on Canton, and we are
publishing them for the accelerator and follow-up challenges after the event.

If one of them interests you, come and talk to us.

## Holding management under load

Canton balances are UTXOs. Your balance is a set of contracts, not a number, and
that cuts both ways.

Two payments at once can reach for the same holding. One wins, the other fails
with a contention error, and both pay for the network traffic. So you want
several holdings.

But holdings are not free. Canton Coin charges a holding fee per UTXO over time,
regardless of the amount, so dust costs you money and can eventually be expired
by Super Validators. Each extra input also makes a transaction bigger, and
bigger transactions cost more traffic. Canton's own guidance is to keep users
under about 10 holdings. So you want few holdings.

Every Canton wallet team is solving this separately and badly. There is no
shared library.

**What to build**

- Coin selection that balances three things at once: fewest inputs (traffic),
  least change dust (holding fees), and lowest chance of colliding with
  something already in flight.
- A reservation layer with expiry and crash recovery, so a dead client does not
  lock a user's funds forever.
- Predictive splitting: forecast how much concurrency a party needs and pre-split
  their holdings so N parallel sends all succeed.
- A load simulator: X concurrent senders on one party, reporting success rate,
  retries, and traffic wasted on failures.
- **Package it as a standalone library with a clean interface**, not as code
  buried inside one backend. This is the point. It should be adoptable by any
  Canton wallet.

**Stretch**

- Adaptive backoff that learns the real contention window instead of sleeping a
  fixed amount.
- Batch merging of dust, and a figure for the holding fees saved over a
  simulated month.
- A visualiser showing the UTXO set moving during a load test.

**How it would be judged**

- Transfer success rate at 1, 5, 20 and 50 concurrent sends from one party.
- Traffic burned on failed transactions, against a naive baseline.
- Average holdings per user kept under 10 across the run.

## Token standard V2

The newer Canton token standard adds four things the current one cannot do, and
the first is the interesting one.

**Privacy-enhanced batch settlement.** One allocation per party covers all of
their legs in a settlement. The executor settles the whole batch with only their
own authority, so counterparties see nothing at settlement time. Each trader only
ever saw their own legs.

**Committed allocations.** Funds stay locked until the executor settles, the
executor cancels, the deadline passes, or the admin expires it. That is what
makes prefunded trading possible.

**Iterated settlement**, so a venue can settle repeatedly against one allocation.

**Account-based holdings**, for custody chains that need them.

**What to build**

- Implement the V2 interfaces on a standalone token of your own, with its own
  registry. You do not need any of our code.
- Add the registry endpoints for the settlement factory and its choice context.
- Write the canonical privacy test: three traders, nine legs, one batch
  settlement. Assert that each trader sees only their own legs and the executor
  sees all nine.
- Prove backwards compatibility. A V1 wallet must still be able to transfer the
  same token.
- Build the approval screen that shows a user all of their legs in one signature.

**How it would be judged**

- The nine-leg privacy test passing, with an explicit assertion that a trader
  cannot see a counterparty's leg. Without that test, a privacy claim is just a
  claim.
- Traffic cost per settled trade, V1 against V2.
- V1 compatibility demonstrated live.

## On-chain governance for a token

Every Ethereum token has a governor, a timelock and a treasury. It is a solved
pattern there. Canton has none of it at the application level: no proposals, no
voting, no treasury management. Decisions are social coordination or an admin
making a call.

**What to build**

- A proposal contract: who proposed it, what it does (transfer X from treasury
  to Y, change parameter Z), how long voting runs, and what quorum it needs.
- Voting weighted by holdings at a snapshot time, so nobody can buy tokens
  mid-vote to swing it.
- Timelock execution: a passed proposal executes after a delay, giving anyone
  who disagrees time to exit first.
- A treasury that can only pay out through a passed proposal.

**The genuinely hard parts**

Two, and they are why this is here rather than in the day track.

You cannot see all the token holders. Ethereum computes voting weight by reading
everyone's balance, and on Canton you simply cannot. Solving that without
breaking the privacy model is a real contribution.

And votes are visible as they are cast, which lets early votes influence later
ones. Commit-reveal fixes it: voters commit to a hidden vote, then reveal once
the period closes.

# Judging

| What | Weight |
|---|---|
| Does it measure the thing? | 30% |
| Does it survive an attack? | 25% |
| Does it work outside the demo? | 20% |
| Is the honesty good? | 15% |
| Would this ship? | 10% |

A few things worth knowing:

**Bring a number.** Balances indexed, drift caught, charges rejected, success
rate under load. A demo with no measurement scores badly however nice it looks.

**We will try to break it.** Exceed the cap, kill the process mid-flight,
observe something we should not be able to see. Teams that attacked their own
work first do much better.

**Say what is mocked.** Overclaiming is penalised harder than an incomplete
build. A team that says "this part is faked and here is why" scores above a team
that quietly hopes nobody asks.

**Enforce your rules in the right place.** If your spending cap lives in your
API, anyone reaching the ledger directly walks around it. We will check.

# Getting help

Davide is in the room all day. Come and find him.

The best question is one where you show the actual error rather than describing
it. Running `python3 c8lab.py check` first tells us which layer broke and saves
us both ten minutes.

Ask early rather than late.
