# applewatch-vitalpipe-mcp-serverless

Apple Watchのヘルスデータ → AWSサーバーレスパイプライン → Claude Code向けMCPツール。

設計ドキュメント: [docs/要件定義.md](docs/要件定義.md)、[docs/基本設計.md](docs/基本設計.md)。

このリポジトリをフォーク・クローンすれば、**あなた自身のApple Watch/iPhoneのヘルスデータ**を、あなた自身のAWSアカウント上にデプロイしたパイプライン経由で、Claude Codeから自然言語で問い合わせられるようになります。個人利用規模(単一ユーザー)を前提とした構成です。

## できること・できないこと

- できること: Claude Codeから「直近1週間のactive_energyのサマリを教えて」「最新のワークアウトの状況を教えて」のように問い合わせ、Health Auto Export経由で同期したApple Healthデータ(消費エネルギー、心拍数、睡眠、ワークアウト等)を自然言語で確認できます。
- できないこと(現時点): **claude.ai(ブラウザ/デスクトップのチャット版)・Claude Coworkからの利用は未対応**です。どちらも同じ「カスタムコネクタを追加」画面を使っており、2026年時点ではOAuthのみ対応で、本サーバーが使う固定シークレット(Bearer)方式のヘッダー認証にはまだ対応していません(詳細: docs/基本設計.md §3・§11)。利用はClaude Codeに限られます。

## 前提条件

- **Apple Watch + iPhone**、および **[Health Auto Export](https://www.healthyapps.dev/)** アプリ。カスタムHTTPヘッダーを設定できる「Automations(REST API送信)」機能を使うため、**有料プランが必要な場合があります**(無料版で使えるかは各自ご確認ください)。実機で動作確認済みなのは買い切り版です。
- **AWSアカウント**。Lambda・DynamoDB・API Gateway(HTTP API)・IAMロール・AWS Budgetsを作成できるIAM権限が必要です。個人利用規模であれば月額コストはごく僅かです(docs/基本設計.md §10)。
- **[Claude Code](https://claude.com/claude-code)** がインストール済みであること(MCPツールを実際に使う側)。
- Gitとターミナル操作の基本知識。

## セットアップ

以下のいずれかのパターンで進めます。どちらも大まかな流れは同じです。

### パターンA: 自分のPC・Macで実行する

1. リポジトリをクローンする:
   ```bash
   git clone https://github.com/HitoshiTakaira/applewatch-vitalpipe-mcp-serverless.git
   cd applewatch-vitalpipe-mcp-serverless
   ```
2. 必要なツールをインストールする:
   - [uv](https://docs.astral.sh/uv/)(Python環境・依存関係の管理)
   - [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)(`aws configure`または`aws sso login`で自分のAWSアカウントに認証しておく)
   - [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
3. Python環境をセットアップし、テストが通ることを確認する:
   ```bash
   uv python install 3.13
   uv sync
   uv run pytest
   ```
4. [デプロイ](#デプロイ手順)に進む。

### パターンB: GitHub Codespacesで実行する

自分のマシンに何もインストールしたくない場合、ブラウザだけで作業できます。

1. このリポジトリを自分のGitHubアカウントにフォークする(右上の「Fork」)。
2. フォークしたリポジトリで「Code」→「Codespaces」タブ→「Create codespace on main」を選択する。
3. Codespace起動後、ターミナルで必要なツールをインストールする:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source $HOME/.local/bin/env
   pip install aws-sam-cli
   uv python install 3.13
   uv sync
   uv run pytest
   ```
4. AWSの認証情報をCodespaceに渡す。GitHubの「Settings → Codespaces → Secrets」で、あなたのAWSアカウントの`AWS_ACCESS_KEY_ID`・`AWS_SECRET_ACCESS_KEY`・`AWS_DEFAULT_REGION`をリポジトリ用のCodespaces Secretsとして登録しておくと、Codespace起動時に自動で環境変数として使えるようになります(登録後はCodespaceの再作成が必要です)。
5. [デプロイ](#デプロイ手順)に進む。

Codespaceは一定時間操作がないと自動停止します。継続的に24時間365日稼働させる用途には向かないので注意してください(Health Auto Export側からのingestはAWS側だけで完結するので問題ありませんが、Codespace自体は「作業するときだけ起動する開発環境」という位置づけです)。

## デプロイ手順

共通の手順です。

1. 共有シークレット用のSSMパラメータを作成する。CloudFormationの`AWS::SSM::Parameter`は`SecureString`をサポートしないため、このテンプレートでは作成できず、手動作成が必要です:
   ```bash
   aws ssm put-parameter --name "/health-mcp/shared-secret" \
     --type SecureString --value "$(openssl rand -base64 32)"
   ```
2. デプロイする:
   ```bash
   sam build && sam deploy --guided
   ```
   途中で聞かれる項目:
   - `Stack Name`: 好きな名前(例: `apple-watch-vitalpipe`)
   - `AWS Region`: 好きなリージョン
   - `Parameter SecretParameterName`: そのままEnter(デフォルトで手順1のパラメータ名と一致)
   - `Parameter NotificationEmail`: **必須**。コスト超過アラートを受け取りたいメールアドレス
   - `Parameter MonthlyBudgetLimitUsd`: そのままEnterでよい(デフォルト$2)
   - `Confirm changes before deploy`: `y`
   - `Allow SAM CLI IAM role creation`: `Y`
   - `Disable rollback`: `N`
   - (関数ごとに)`may not have authorization defined, Is this okay?`: `y`(カスタムLambda Authorizerを使っているための既知の表示で、問題ありません)
   - `Save arguments to configuration file`: `Y`(次回以降は`sam deploy`だけで済みます)
   - 最後にchangesetの内容が表示されるので、`AWS::Lambda::Permission`や`AWS::DynamoDB::Table`などが`+ Add`のみになっていることを確認して`y`
3. デプロイ完了後に表示される`ApiEndpoint`の値(例: `https://xxxxxxxxxx.execute-api.<region>.amazonaws.com`)を控える。
4. AWS Budgetsは`template.yaml`でメールアドレスを直接登録する方式なので、購読確認メールは届きません(SNSトピック経由の通知とは異なる仕組みです)。設定自体が有効かどうかは`aws budgets describe-budgets --account-id <アカウントID>`で確認できます。
5. Health Auto ExportのAutomations(REST API送信)を設定する:
   - URL: `<手順3のApiEndpoint>/ingest`
   - Method: POST
   - ヘッダーに `Authorization: Bearer <手順1のシークレット>` を追加する(実機で対応を確認済み。買い切り版のHAEには「ヘッダーを追加」というUIがあります)
   - エクスポートするデータ(消費エネルギー、心拍数、睡眠、ワークアウト等)と送信頻度を設定する
6. Claude CodeにMCPサーバーを登録する:
   ```bash
   claude mcp add --transport http health-data <手順3のApiEndpoint>/mcp \
     --header "Authorization: Bearer <手順1のシークレット>" \
     --scope user
   ```
7. HAEアプリで「今すぐ送信」などのテスト実行をし、Claude Codeで「直近1週間のactive_energyのサマリを教えて」のように聞いてみて、データが返ってくることを確認する。

## トラブルシューティング

- **`sam build`が`python3.13`を見つけられない/`pip`が無いと言われる**: `uv sync`で作った`.venv`は自動ではPATHに入りません。`source .venv/bin/activate`してから`sam build`を実行してください。また、uvが作る仮想環境にはデフォルトで`pip`が入っていないため、SAMのビルドが`pip`を要求する場合は`uv pip install pip`で追加してください。
- **`/ingest`や`/mcp`が403 Forbiddenを返す**: 認証ヘッダーの値(シークレット)が、SSMパラメータの値と完全に一致しているか確認してください。手入力による転記ミスが起きやすい箇所です。可能であればコピー&ペーストで転記してください。
- **HAEの自動送信がエラーで失敗する**: まずHAEアプリ内に送信履歴・エラー詳細を確認できる画面がないか探し、HTTPステータスコードが分かればそれを手がかりに調べてください。ステータスコードが返ってこない(ログにも何も残らない)場合は、URLの誤り、HTTPメソッドの誤り、またはネットワーク到達性の問題が疑われます。

## 開発

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

設計上の判断・実機検証で判明した内容の詳細は [docs/基本設計.md](docs/基本設計.md) を参照してください。
