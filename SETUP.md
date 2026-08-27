# Setup

Two things you might need. Most tasks only need the first.

- **LocalNet** for anything that talks to a ledger. Or skip it and use DevNet.
- **The Daml toolchain** only if you are writing Daml contracts.

## Where you run things

Two options. **Start with the shared network.**

| | Shared network (DevNet) | Your own (LocalNet) |
|---|---|---|
| Setup | none, we give you a token | Docker, 6 GB of images, 16 GB RAM |
| Works offline | no | yes |
| Recommended | **yes** | only if you want to break things |

You do not need LocalNet to take part, and it is the slowest way to start.
Ask us for DevNet credentials on the day and skip this whole section.

## Optional: your own Canton network

A whole network in Docker: three participants, three validators, Postgres and
some web UIs. Useful if you want to work offline or reset everything.

### 1. Docker, with enough memory

Docker Desktop running, then **Settings, Resources, memory: 16 GB**. The
compose file wants about 12 GB, so 8 GB thrashes and you will blame Canton
when it is your laptop.

### 2. Pull the images before you arrive

**About 6 GB.** Do this at home. Fifty people pulling 6 GB on venue wifi will
not work.

```bash
docker pull ghcr.io/digital-asset/decentralized-canton-sync/docker/splice-app:0.6.8
docker pull ghcr.io/digital-asset/decentralized-canton-sync/docker/canton:0.6.8
docker pull ghcr.io/digital-asset/decentralized-canton-sync/docker/wallet-web-ui:0.6.8
docker pull ghcr.io/digital-asset/decentralized-canton-sync/docker/sv-web-ui:0.6.8
docker pull ghcr.io/digital-asset/decentralized-canton-sync/docker/scan-web-ui:0.6.8
docker pull ghcr.io/digital-asset/decentralized-canton-sync/docker/ans-web-ui:0.6.8
docker pull postgres:14
docker pull nginx:1.27.0
docker pull busybox:1.37.0
```

All public, no login. `splice-app` is 2.4 GB and `canton` is 1.6 GB, the rest
are a few hundred MB each.

### 3. Get the compose files and start it

They ship in the Splice release bundle, not in this repo. Follow the official
instructions, which are kept up to date:

<https://docs.dev.sync.global/app_dev/testing/localnet.html>

Short version: download and extract `splice-node.tar.gz`, and the compose files
are in `splice-node/docker-compose/localnet`. Then, from that directory:

```bash
export LOCALNET_DIR=$PWD
export IMAGE_TAG=0.6.8
export PARTY_HINT=myteam-dev-1
export APP_PROVIDER_UI_PORT=3001    # port 3000 is usually taken

docker compose --env-file "$LOCALNET_DIR/compose.env" \
  --env-file "$LOCALNET_DIR/env/common.env" \
  -f "$LOCALNET_DIR/compose.yaml" \
  -f "$LOCALNET_DIR/resource-constraints.yaml" \
  --profile sv --profile app-provider --profile app-user up -d
```

Same command with `down -v` to stop and wipe.

`PARTY_HINT` must look like `word-word-number` or compose refuses to start.

### 4. Check it is up

```bash
curl -s -o /dev/null -w "%{http_code}\n" localhost:2975/v2/state/ledger-end
```

**401 means it worked.** The API is up and wants a token. Takes 60 to 90
seconds. No response at all means it is still starting.

### Two things that go wrong

**Docker cannot bind-mount from Documents, Desktop or Downloads on macOS.**
Extract the bundle somewhere else, like your home folder. Otherwise the web
pages load while the ledger is dead, which looks like it worked.

**Port 3000 is usually taken** by Next.js, Grafana or similar. nginx then fails
and the registry is unreachable, so transfers break. `APP_PROVIDER_UI_PORT=3001`
above avoids it.

### Ports

Not 7575. That is the standalone sandbox. LocalNet prefixes per node: `2`
app-user, `3` app-provider, `4` sv.

```
JSON Ledger API    2975   3975   4975
Ledger API gRPC    2901   3901   4901
Participant admin  2902   3902   4902
Validator admin    2903   3903   4903
Web UIs            2000   3001   4000
Registry / scan    4000, Host: scan.localhost
Postgres           5432
```

`scan.localhost` often does not resolve. `c8lab.py` sends a `Host:` header
instead. For the browser UIs, add to `/etc/hosts`:

```
127.0.0.1  scan.localhost
127.0.0.1  wallet.localhost
```

## Daml toolchain

Only for the Daml tasks. Everything else is HTTP.

### 1. Rosetta, on Apple Silicon

The Daml SDK's macOS build is x86_64. On an M-series Mac without Rosetta the
install dies with `Bad CPU type in executable` and nothing explains why.

```bash
softwareupdate --install-rosetta --agree-to-license
```

It is a few hundred megabytes, so do it before you arrive, not on venue wifi.

### 2. Java

```bash
brew install openjdk@21
```

### 3. Daml SDK, pinned

```bash
curl -sSL https://get.daml.com/ -o get-daml.sh
sh get-daml.sh 3.4.10
```

Pinned on purpose. The Daml Assistant is deprecated in SDK 3.4 and removed in
3.5, so an unpinned install can leave you with no `daml` command at all.

### 4. Put it on your PATH

Add to `~/.zshrc`, then open a new terminal:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@21
export PATH="$HOME/.daml/bin:$JAVA_HOME/bin:$PATH"
```

**Open a new terminal.** Editing `.zshrc` does nothing to the shell you already
have open, and `daml build` will work while `daml test` fails with "Unable to
locate a Java Runtime", because the compiler shells out to `java`.

### 5. Check it

```bash
daml version
cd ioulab && daml build && daml test
```

The deprecation warning about DPM is expected. Ignore it.

### Commands worth knowing

| Command | Does |
|---|---|
| `daml version` | First thing to check when stuck |
| `daml new <dir>` | Scaffold a project |
| `daml build` | Compile to a `.dar` in `.daml/dist/` |
| `daml test` | Run every Daml Script in memory, about a second, no node |
| `daml start` | Sandbox plus JSON API, if you want a real ledger |

`daml test` is the loop you want. It needs no node and no network.

`daml.yaml`'s `sdk-version` must match your installed SDK or the build fails
with a confusing message.
