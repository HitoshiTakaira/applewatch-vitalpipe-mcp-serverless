# applewatch-vitalpipe-mcp-serverless

Apple Watch health data → AWS serverless pipeline → MCP tools for Claude Code.

Design docs: [docs/要件定義.md](docs/要件定義.md), [docs/基本設計.md](docs/基本設計.md).

## Development

Requires [uv](https://docs.astral.sh/uv/) (manages the Python 3.13 interpreter and dependencies).

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format .
```

## Project layout

- `health_mcp/` — shared library: unit normalization, HAE payload parsing, DynamoDB
  access, MCP query logic, trend calculation, auth helpers. Lives at the repo root
  (not under `src/`) so it can be imported directly both by tests and by the Lambda
  handlers once `sam build` copies the repo tree as-is (see `template.yaml`'s
  `CodeUri: .`).
- `handlers/` — one directory per Lambda function (`authorizer`, `ingest_function`,
  `mcp_function`), each a thin wrapper around `health_mcp`.
- `tests/` — pytest tests, using `moto` to mock DynamoDB/SSM.
- `template.yaml` — AWS SAM template.
- `requirements.txt` — generated from `uv.lock` for SAM's Python builder (which
  expects a requirements.txt, not a pyproject.toml). Regenerate after changing
  dependencies:
  ```bash
  uv export --no-dev --no-hashes --no-emit-project -o requirements.txt
  ```

## Deploying (not yet done in this repo)

This has been implemented but **not deployed**. Before running `sam deploy`:

1. Install the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html).
2. Create the shared-secret SSM parameter out of band — CloudFormation's
   `AWS::SSM::Parameter` doesn't support `SecureString`, so this template can't
   create it for you:
   ```bash
   aws ssm put-parameter --name "/health-mcp/shared-secret" \
     --type SecureString --value "$(openssl rand -base64 32)"
   ```
3. `sam build && sam deploy --guided` (you'll be prompted for `NotificationEmail`
   and can accept the default for everything else).
4. Confirm the AWS Budgets subscription email (AWS sends a confirmation link).
5. Point Health Auto Export's Automations at `<ApiEndpoint>/ingest` with header
   `Authorization: Bearer <the secret from step 2>` —
   **first verify HAE actually supports setting a custom request header**
   (docs/要件定義.md §2 flags this as unverified).
6. Register the MCP server with Claude Code:
   ```bash
   claude mcp add --transport http health-data <ApiEndpoint>/mcp \
     --header "Authorization: Bearer <the secret from step 2>"
   ```

`docs/基本設計.md` §9 documents the HAE payload shape `IngestFunction` expects;
it's provisional until checked against a real export, so watch CloudWatch Logs
for `skipping ... record` warnings after the first real syncs and adjust
`health_mcp/haepayload.py` accordingly.
