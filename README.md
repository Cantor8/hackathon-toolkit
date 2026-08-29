# 🌺 IronFlower (Tekkadan Protocol)
### Resilient Canton Scanner, Drift Sentinel & Confidential Humanitarian EHR

> **Cantor8 Hackathon 2026 Submission** | Targeting Track A1 (Scanner), Track A2 (Drift Sentinel) & Track N1 (Humanitarian Architecture)

---

## ⚡ Quickstart & Live Demo

1. **Launch the Interactive Web Portal:**
   ```bash
   python server.py
   ```
   Open **`http://localhost:8088`** in your browser to view the real-time Medical Stock tracker, WHO clinical EHR triage, live Canton Scanner, and Drift Sentinel fault lab.

2. **Run the Automated Resilience & Attack Benchmark:**
   ```bash
   python test_resilience.py
   ```

3. **Key Submission Documents:**
   - 📄 **3-Page Whitepaper:** [`submission_N1_humanitarian_medical_supply.md`](submission_N1_humanitarian_medical_supply.md)
   - 🎤 **Pitch Deck & Script:** [`PITCH_DECK.md`](PITCH_DECK.md)
   - 📜 **Daml Smart Contract:** [`daml-starter/daml/MedicalEscrow.daml`](daml-starter/daml/MedicalEscrow.daml)

---

# Canton Hackathon Toolkit

- **LocalNet**, a whole Canton network in Docker on your laptop. The default.
- **DevNet**, the shared Cantor8 node. Set four environment variables.

| File | What |
|---|---|
| `CHALLENGES.md` | The problems, and what to build |
| `SETUP.md` | Install LocalNet, and the Daml toolchain if you need it |
| `API.md` | Tested cheat sheet of the APIs you will use, and what needs a token |
| `TROUBLESHOOTING.md` | Every error we actually hit, and the fix |
| `c8lab.py` | The lab |
| `daml-starter/` | Working Daml to copy from, including the mandate task |

Start with `SETUP.md`, come back here.

**Looking for the problems?** They are in [`CHALLENGES.md`](CHALLENGES.md).

## The lab

Six steps. This is the shape of every Canton app.

```
1. Get a token                    the API is authenticated
2. Allocate a party               your identity on the ledger
3. Set up a TransferPreapproval   so people can pay you directly
4. Read your balance from the ACS zero, at first
5. Get some Canton Coin           LocalNet mints it, on DevNet ask the team
6. Send a token standard transfer to another party
```

### Run it

```bash
python3 c8lab.py                          # check everything, list parties, balances
python3 c8lab.py party myteam             # step 2
python3 c8lab.py preapproval <party>      # step 3
python3 c8lab.py holdings <party>         # steps 4 and 5
python3 c8lab.py transfer <from> <to> 25  # step 6
python3 c8lab.py accept <instructionCid> <to>   # if step 6 returned an offer
python3 c8lab.py grant <user> <party>           # fix a 403
```

`check` first, always. It verifies auth, the ledger, your parties and their
balances. It does **not** check that the registry is reachable, that you have
act-as rights on every party, or that a preapproval has been accepted. So a
clean `check` means the basics are fine, not that everything is.

### What good output looks like

```
base       http://localhost:2975
mode       LocalNet / unsafe HS256
token      ok
ledger end 104
local parties (3):
    app_user_cantor8-hackathon-1::1220...
    participant::1220...

holdings for app_user_cantor8-hackathon-1: 1 contract(s), total 4220.16
    {'amount': '4220.16', 'instrument': 'Amulet', 'locked': False}
```

`Amulet` is Canton Coin. Amulet is the name in the Daml code, Canton Coin is the
name in the marketing. Same thing.

On LocalNet the balance grows on its own as mining rounds tick over and pay the
validator. Nothing is broken.

## Three things worth understanding

### Your balance is not a number

It is a set of contracts. `total 4220.16` is the sum of the `Holding` contracts
you can see. A transfer archives the ones it spends and creates new ones, like
handing over a note and getting change.

This is why two transfers at the same time can fight over the same holding.
One wins, the other fails, and both pay for the traffic.

### A token is a Daml package plus a web service

Step 6 is two phases, and the first surprises everyone:

```
1. Ask the registry for a transfer factory and a choice context.
2. Exercise TransferFactory_Transfer, attaching what it gave you.
```

Why the registry exists: privacy. You cannot see the issuer's configuration
contracts, so it hands them to you as **disclosed contracts**, valid for that one
transaction. On LocalNet the registry is the scan app; ours returned five
disclosed contracts and a context with `amulet-rules`, `open-round`,
`transfer-preapproval` and `external-party-config-state`.

If you skip this and try to build the transfer by hand, it will not work, and
the error will not tell you why.

### `transferKind` tells you which flow you are in

The registry answers with one of:

- **`direct`**: the receiver has a live `TransferPreapproval`. Money moves
  immediately.
- **`offer`**: no preapproval. A `TransferInstruction` is created and the
  receiver has to accept it. Their balance does **not** change until they do.
- **`self`**: sender and receiver are the same party.

We saw both. A party with an accepted preapproval got `direct` and received the
money straight away. A party with no preapproval got `offer`, the transfer
succeeded, and the balance stayed empty until we accepted it.

`transfer` prints the `instructionCid` and the exact accept command when it
returns an offer. Run it and the money moves.

**So if you send money and the receiver sees nothing, check `transferKind`
before you debug anything else.** Preapproval acceptance is not instant: you
create the proposal, and the validator's automation accepts it a moment later.

## The functions

Import it, do not just use the CLI.

| Function | Does |
|---|---|
| `token(sub)` | HS256 on LocalNet, Keycloak on DevNet |
| `call(path, body, sub)` | Any Ledger API call. Prints the real error on failure. |
| `ledger_end()` | Current offset |
| `parties()` / `local_parties()` | What the node knows, and what it hosts |
| `allocate_party(hint)` | Allocate, or reuse if it exists |
| `grant_act_as(user, party)` | Fix a 403 |
| `holdings(party)` | Balances, via the interface filter |
| `submit(cmds, act_as, disclosed)` | Any command, with disclosed contracts |
| `create_preapproval(me, provider)` | Step 3 |
| `registry(path, body)` | Call the token registry |
| `transfer(from, to, amount)` | Step 6, both phases |
| `check()` | Run this first when something is broken |

Only reuse parties where `isLocal` is true. A node lists parties it has heard
about from the network, including ones hosted elsewhere that it cannot submit
for. Using one of those gives you
`NO_SYNCHRONIZER_ON_WHICH_ALL_SUBMITTERS_CAN_SUBMIT`.

## Running against DevNet

```bash
export C8_BASE=https://api.validator.dev.digik.cantor8.tech/api/ledger
export C8_IDP=https://auth.dev.digik.cantor8.tech
export C8_CLIENT_ID=hackathon
export C8_CLIENT_SECRET=<ask the Cantor8 team>
export C8_REGISTRY=<registry base url>       # needed for transfers
python3 c8lab.py check
```

Setting `C8_IDP` switches from a self-signed LocalNet token to a real Keycloak
client-credentials token. Everything else is the same.

For DevNet you will also need `C8_REGISTRY` pointing at the Cantor8 registry, and
Canton Coin has to be sent to you: give the team your party ID.

**Not yet verified on DevNet.** Party allocation there may need the
external-party topology flow rather than `POST /v2/parties`. If it fails at step
2, that is why.

## Docs

```
Canton docs, has a chatbot   https://docs.canton.network
Ledger API                   https://docs.canton.network/sdks-tools/api-reference/ledger-api
Validator Admin API          https://docs.canton.network/sdks-tools/api-reference/admin-api
Token standard               https://docs.canton.network/appdev/deep-dives/token-standard
```
