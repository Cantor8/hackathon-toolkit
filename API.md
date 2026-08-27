# API reference

Every URL below was tested on 27 Aug 2026. The status column is what it actually
returned, not what it should return.

## Start here: what needs a token

| Base URL | Auth | Tested |
|---|---|---|
| `https://sv-proxy.dev.digik.cantor8.tech` | **none** | 200 |
| `https://scanner-ledger-read-api.dev.digik.cantor8.tech` | health is open, data needs a token | 200 / 401 |
| `https://wallet-backend.dev.digik.cantor8.tech` | health and spec open, data needs a token | 200 / 401 |
| `https://api.validator.dev.digik.cantor8.tech/api/ledger` | Keycloak token | 401 without one |
| `https://api.validator.dev.digik.cantor8.tech/api/validator` | Keycloak token | not open |
| `https://auth.dev.digik.cantor8.tech` | none, this is where tokens come from | 200 |
| `https://collector-service.dev.digik.cantor8.tech` | docs open | 200 |
| `https://identity-service.dev.digik.cantor8.tech` | not publicly reachable | no response |

**If you have no credentials yet, start with sv-proxy.** It needs nothing and it
serves real network data.

## Getting a token

The Ledger API, and the scanner and wallet-backend data endpoints, want a
Keycloak token. The public token registry endpoints under `/registry/...`
generally do not. Admin endpoints use a separate machine-to-machine token.

```python
import json, urllib.parse, urllib.request
data = urllib.parse.urlencode({
    "grant_type": "client_credentials",
    "client_id": "hackathon",
    "client_secret": SECRET,          # ask the Cantor8 team
}).encode()
url = "https://auth.dev.digik.cantor8.tech/realms/master/protocol/openid-connect/token"
tok = json.loads(urllib.request.urlopen(
    urllib.request.Request(url, data=data)).read())["access_token"]
```

Then `Authorization: Bearer <tok>` on every call. `c8lab.py` does this for you
when `C8_IDP` is set.

Remember: **a token says who you are, it does not give you rights over a party.**
That is a separate grant. See TROUBLESHOOTING.md.

## Ledger API

`https://api.validator.dev.digik.cantor8.tech/api/ledger`

This is the one that matters. It is the standard Canton JSON Ledger API v2, so
the official docs apply directly:
`https://docs.canton.network/sdks-tools/api-reference/ledger-api`

Four endpoints do almost everything:

| Endpoint | Does |
|---|---|
| `GET  /v2/state/ledger-end` | Current offset. Use it as a health check too. |
| `POST /v2/state/active-contracts` | Read the contracts you can see, at an offset |
| `POST /v2/commands/submit-and-wait` | Write, and block until committed |
| `WS   /v2/updates` | Stream every change from an offset |

Plus the ones you need for setup:

| Endpoint | Does |
|---|---|
| `GET  /v2/parties` | List parties. Only `isLocal: true` ones can submit. |
| `POST /v2/parties` | Allocate a party |
| `POST /v2/users/{userId}/rights` | Grant `CanActAs`, this is the 403 fix |

The WebSocket variant is at `wss://api.validator.dev.digik.cantor8.tech/api/ledger`,
and gRPC at `api.validator.dev.digik.cantor8.tech/api/rpc_ledger`.

## Scanner

`https://scanner-ledger-read-api.dev.digik.cantor8.tech`

Cantor8's off-ledger index. It reads the Ledger API and the Scan API, parses
transaction trees, and serves the result. **This is the reference for anyone
building the scanner task**, because it is the thing you are rebuilding.

- **Live docs:** `/docs/`
- **Machine-readable spec:** `/docs/openapi.yaml`
- **Health, no auth:** `/health`

Health is worth knowing because it tells you the lag:

```json
{"status":"ok","db":{"status":"ok","scannerDelaySecs":10.845}, ...}
```

45 endpoints. The ones worth knowing:

| Endpoint | Does |
|---|---|
| `/health` | Status and how far behind the index is |
| `/tokens/balance/{party}` | Balance for a party |
| `/tokens/balance-history/{party}` | Balance over time |
| `/tokens/transfers/{party}` | Transfers for a party |
| `/tokens/transfers/history/{party}` | Unified history |
| `/tokens/owners` | Who holds what |
| `/contracts/active` | Active contracts |
| `/round/global-rewards-by-round` | Rewards per round, per provider, CC and USD |
| `/round/marker-rewards-by-round` | Activity marker rewards |
| `/round/global-traffic-by-round` | Traffic per round |
| `/economics/rewards-and-costs` | Reward vs cost per activity marker |
| `/economics/transfers-histogram-log` | Transfer size distribution |
| `/traffic/purchase-stats` | Traffic purchases |
| `/update/transfers/{update_id}` | What a single transaction did |

Data endpoints return `401` without a token. Some also return `403` with a
valid token: either the party is not yours, or the endpoint is machine-to-machine
only. 401 means "who are you", 403 means "not yours".

## Cantor8 wallet-backend

`https://wallet-backend.dev.digik.cantor8.tech`

Cantor8's own wallet API. Not the Splice wallet API, which is a different thing
under `/v0/wallet/...`. Useful as a worked example of an application on top of Canton.

- **Spec, no auth:** `/openapi.json`
- **Health, no auth:** `/healthz`
- 73 paths

Worth knowing:

| Endpoint | Does |
|---|---|
| `GET  /api/balance` | User balance |
| `GET  /api/holdings` | Raw holdings |
| `GET  /api/history` | Transaction history |
| `POST /api/external/prepare` | Prepare a transaction for external signing |
| `POST /api/external/execute` | Submit the signed transaction |
| `GET  /api/offers_v3` | Pending transfer offers |
| `GET  /api/command/{id}/status` | Track a submission |
| `POST /api/swap/offer/prepare` | Swap flows |

Endpoints ending `_m2m` are service-to-service and use a different token.

The `prepare` and `execute` pair is the interesting bit: the backend builds the
transaction, the user's key signs it, the backend submits it. The key never
leaves the client.

## Scan API, public

`https://sv-proxy.dev.digik.cantor8.tech`

**No auth.** Network-wide data published by the super validators. If you want to
start now with no credentials, start here.

| Endpoint | Method | Does |
|---|---|---|
| `/api/scan/v0/scans` | GET | Every scan node on the network |
| `/api/scan/v0/splice-instance-names` | GET | Network name and branding |
| `/api/scan/v0/open-and-issuing-mining-rounds` | POST | Current mining rounds |
| `/api/scan/v0/amulet-rules` | POST | Canton Coin rules contract |
| `/registry/metadata/v1/info` | GET | Token standard registry info |

Note the POST-only ones. A GET returns
`405 HTTP method not allowed, supported methods: POST`, which reads like an
error but is just the wrong verb.

Full Scan API reference:
`https://docs.dev.sync.global/app_dev/scan_api/scan_bulk_data_api.html`

## Token standard registry

The registry is how a wallet gets what it needs to build a transfer. It is not
one host, it is an API that each token issuer implements.

| Endpoint | Does |
|---|---|
| `GET  /registry/metadata/v1/info` | Who the admin is, which APIs are supported |
| `GET  /registry/metadata/v1/instruments` | Which tokens this registry serves |
| `GET  /registry/metadata/v1/instruments/{id}` | One token's details |
| `POST /registry/transfer-instruction/v1/transfer-factory` | Factory and choice context for a transfer |
| `POST /registry/transfer-instruction/v1/{id}/choice-contexts/accept` | Context to accept an offer |
| `POST /registry/transfer-instruction/v1/{id}/choice-contexts/reject` | Context to reject an offer |
| `POST /registry/transfer-instruction/v1/{id}/choice-contexts/withdraw` | Context for the sender to withdraw |

One shape trap: in these choice-context requests `meta` is a **flat** string map,
`{"meta": {}}`. Send the wrapped `{"meta": {"values": {}}}` and you get
`DecodingFailure at .meta.values`.

Verified working on LocalNet. The transfer-factory call returns `factoryId`,
`transferKind` and a `choiceContext` containing `choiceContextData` and
`disclosedContracts`. You attach those disclosed contracts to your submission.

On LocalNet the registry is the scan app at `localhost:4000` with
`Host: scan.localhost`. Set `C8_REGISTRY` for DevNet, and only set
`C8_REGISTRY_HOST` if that deployment routes by Host header.

Different tokens have different registries. Canton Coin's is the scan app.
Cantor8's own tokens (`c8ETH`, `c8BTC`) are served by the token-factory registry
under its own base path, and they have their own admin party, not the DSO. The
`transfer()` helper in `c8lab.py` is written for Amulet; for a c8 token you also
need that token's admin and instrument id.

## Docs

```
Canton docs, has a chatbot   https://docs.canton.network
Ledger API                   https://docs.canton.network/sdks-tools/api-reference/ledger-api
Validator Admin API          https://docs.canton.network/sdks-tools/api-reference/admin-api
Token standard               https://docs.canton.network/appdev/deep-dives/token-standard
Scan bulk data API           https://docs.dev.sync.global/app_dev/scan_api/scan_bulk_data_api.html
```
