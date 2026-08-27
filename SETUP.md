# Setup

Two things you might need. Most tasks only need the first.

- **LocalNet** for anything that talks to a ledger. Or skip it and use DevNet.
- **The Daml toolchain** only if you are writing Daml contracts.

## LocalNet

A whole Canton network in Docker: three participants, three validators,
Postgres, and some web UIs.

### 1. Docker, with enough memory

Docker Desktop must be running. Then **Settings, Resources, set memory to 16 GB**.
The compose file asks for about 12 GB across the essential services, so 8 GB
will thrash and you will think Canton is slow when it is your laptop.

### 2. Put it somewhere Docker can read

**This is the one that catches people.** macOS privacy settings usually stop
Docker bind-mounting from `Documents`, `Desktop` or `Downloads`. You get a
network where the web pages load but the ledger is dead, which looks like it
worked.

You can grant Docker Desktop access to those folders in System Settings,
Privacy and Security, Files and Folders. Copying is faster and always works:

```bash
cp -R <path-to>/splice/cluster/compose/localnet ~/localnet
```

### 3. Start it

```bash
export LOCALNET_DIR=$HOME/localnet
export IMAGE_TAG=0.6.8
export PARTY_HINT=myteam-dev-1        # must be word-word-number, or it refuses

docker compose --env-file "$LOCALNET_DIR/compose.env" \
  --env-file "$LOCALNET_DIR/env/common.env" \
  -f "$LOCALNET_DIR/compose.yaml" \
  -f "$LOCALNET_DIR/resource-constraints.yaml" \
  --profile sv --profile app-provider --profile app-user up -d
```

Images come from `ghcr.io/digital-asset/decentralized-canton-sync/docker/` and
need no login.

**If port 3000 is already in use** (Open WebUI, Next.js, Grafana, plenty of
things use it) nginx will not start and the scan registry is unreachable, which
breaks transfers. Add this before the command and everything works:

```bash
export APP_PROVIDER_UI_PORT=3001
```

### 4. Wait for it

```bash
curl -s -o /dev/null -w "%{http_code}\n" localhost:2975/v2/state/ledger-end
```

**401 means it is working.** The API is up and wants a token. 60 to 90 seconds.
No response at all means it is still starting.

### Stop it

Same command with `down -v` instead of `up -d`. The `-v` wipes the database so
you start clean.

### Ports

Not 7575. That is the standalone sandbox. LocalNet prefixes per node: `2`
app-user, `3` app-provider, `4` sv.

```
JSON Ledger API    2975   3975   4975
Ledger API gRPC    2901   3901   4901
Participant admin  2902   3902   4902
Validator admin    2903   3903   4903
Web UIs            2000   3000   4000
Registry / scan    4000, Host: scan.localhost
Postgres           5432
```

`scan.localhost` often does not resolve. `c8lab.py` works around it by sending a
`Host: scan.localhost` header to `localhost:4000`, which is more portable than
editing `/etc/hosts`. If you want the browser UIs to work, add:

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
