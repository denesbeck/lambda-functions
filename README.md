# Lambda Function Store ⚡

This repository uses a GitHub Actions workflow to automate the deployment of AWS Lambda functions.

## Features 💥

- Deploys all Lambda functions in `functions/<app-name>/<function-name>/`-style directories
- Deploys all Lambda layers in `layers/<layer-name>/`-style directories
- Automatically zips and uploads code to S3
- Creates or updates Lambda functions using configuration from `config.json`
- Attaches layers to Lambda functions using configuration from `config.json`
- Publishes a new version after each successful deployment
- Updates the appropriate alias based on the branch name
- Skips unchanged functions by comparing commit diffs

## Directory Structure 📁

Each Lambda function and layer should live in its own subdirectory and include a `config.json` file:

```
functions/
  <app-name>/
    <function-name>/
      index.js
      config.json
layers/
  <layer-name>/
    index.js
    config.json
```

### Example `config.json`:

```json
{
  "function_name": "MyFunction",
  "runtime": "nodejs18.x",
  "handler": "index.handler",
  "role": "MyLambdaExecutionRole",
  "layers": [
    {
      "eu-central-1": ["MyLayer:1", "MyLayer:2"],
      "us-east-1": ["MyLayer:3", "MyLayer:4"]
    }
  ]
}
```

## Alias Strategy 👾

The workflow chooses a Lambda alias based on the Git branch:
| Branch Pattern | Alias |
|---------------------|---------|
| `main` | `prod` |
| `release/*` | `staging` |
| `test/*` | `test` |
| `feature/*` or other| `dev` |

## Deployment Artifacts 📦

Lambda packages are named with a timestamp and Git commit SHA:

**Functions:**
`<app>-<function>-<timestamp>-<sha>.zip`

**Layers:**
`<layer-name>-<timestamp>-<sha>.zip`

These are uploaded to S3 under:

**Functions:**
`s3://<bucket>/<app>/<function>/`

**Layers:**
`s3://<bucket>/<layer>`

## Reguired variables 🔧

- `FUNCTIONS_S3_BUCKET` (variable): S3 bucket for Lambda functions
- `LAYERS_S3_BUCKET` (variable): S3 bucket for Lambda layers
- `HASHES_S3_BUCKET` (variable): S3 bucket for version/hash tracking
- `ACCOUNT_NUMBER` (secret): Your AWS account number (keep it secret!)

## Authentication & Authorization 🔐

Authentication is handled via GitHub OIDC, and access control is managed through AWS IAM roles.

## Lambda Requirements 🛠️

- Ensure each Lambda function and layer has a valid `config.json`
- IAM role must allow Lambda execution and access to CloudWatch Logs
