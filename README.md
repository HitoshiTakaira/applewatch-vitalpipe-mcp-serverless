# applewatch-vitalpipe-mcp-serverless

Apple Watchのヘルスデータ → AWSサーバーレスパイプライン → Claude Code向けMCPツール。

設計ドキュメント: [docs/要件定義.md](docs/要件定義.md)、[docs/基本設計.md](docs/基本設計.md)。

## 開発

[uv](https://docs.astral.sh/uv/)が必要です(Python 3.13のインタプリタと依存関係を管理します)。

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format .
```

## ディレクトリ構成

- `health_mcp/` — 共有ライブラリ。単位正規化、HAEペイロードのパース、DynamoDB
  アクセス、MCPクエリロジック、トレンド計算、認証ヘルパーを含む。`src/`配下では
  なくリポジトリ直下に置いているのは、`sam build`がリポジトリのツリーをそのまま
  コピーする(`template.yaml`の`CodeUri: .`)ため、テストとLambdaハンドラーの
  両方から直接importできるようにするため。
- `handlers/` — Lambda関数ごとのディレクトリ(`authorizer`、`ingest_function`、
  `mcp_function`)。それぞれ`health_mcp`への薄いラッパー。
- `tests/` — pytestのテスト。`moto`でDynamoDB/SSMをモックしている。
- `template.yaml` — AWS SAMテンプレート。
- `requirements.txt` — `uv.lock`から生成したもの。SAMのPythonビルダーは
  pyproject.tomlではなくrequirements.txtを前提とするため。依存関係を変更したら
  再生成すること:
  ```bash
  uv export --no-dev --no-hashes --no-emit-project -o requirements.txt
  ```

## デプロイ(このリポジトリではまだ未実施)

実装は完了していますが、**AWSへのデプロイはまだ行っていません**。`sam deploy`を
実行する前に:

1. [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)をインストールする。
2. 共有シークレット用のSSMパラメータを事前に作成する — CloudFormationの
   `AWS::SSM::Parameter`は`SecureString`をサポートしないため、このテンプレートでは
   作成できない:
   ```bash
   aws ssm put-parameter --name "/health-mcp/shared-secret" \
     --type SecureString --value "$(openssl rand -base64 32)"
   ```
3. `sam build && sam deploy --guided`を実行する(`NotificationEmail`の入力を
   求められるので入力し、それ以外はデフォルトのままでよい)。
4. AWS Budgetsのサブスクリプション確認メールに記載されたリンクから確認する。
5. Health Auto ExportのAutomationsで`<ApiEndpoint>/ingest`宛に
   `Authorization: Bearer <手順2のシークレット>`ヘッダーを設定する —
   **その前にHAEが実際にカスタムリクエストヘッダーの設定に対応しているか
   確認すること**(docs/要件定義.md §2で未検証と明記している)。
6. Claude CodeにMCPサーバーを登録する:
   ```bash
   claude mcp add --transport http health-data <ApiEndpoint>/mcp \
     --header "Authorization: Bearer <手順2のシークレット>"
   ```

`docs/基本設計.md` §9に`IngestFunction`が想定するHAEペイロードの形式を記載
しているが、実際のエクスポートで確認するまでは暫定仕様なので、実運用開始後は
CloudWatch Logsの`skipping ... record`警告を確認し、必要に応じて
`health_mcp/haepayload.py`を調整すること。
