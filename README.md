# Lambda Function Store ⚡

A GitHub Actions CI/CD pipeline for deploying AWS Lambda functions and layers across multiple regions. Uses SHA-256 hash-based change detection to skip unchanged functions, OIDC for keyless AWS authentication, and branch-based aliasing for environment isolation.

## Features 🚀

- **Multi-region deployments** via matrix strategy (`us-east-1`, `eu-central-1`)
- **Hash-based change detection** -- only deploys functions whose code or config has changed (SHA-256 hashes persisted to S3)
- **Independent code and config tracking** -- a config-only change updates configuration without redeploying code
- **Branch-to-alias mapping** -- `main` -> `prod`, `release/*` -> `staging`, `test/*` -> `test`, `feature/*` -> `dev`
- **Lambda versioning** -- every deploy publishes a new version and updates the alias
- **Layer change detection** -- layers are only redeployed when their source files change (`git diff`)
- **Multi-runtime support** -- Node.js, Python, Go, Ruby
- **Validation gate** -- ShellCheck linting must pass before deploy
- **Concurrency control** -- prevents simultaneous deploys to the same branch
- **OIDC authentication** -- keyless AWS access via GitHub Actions OIDC federation
- **Structured JSON logging** -- all Lambda functions output JSON logs for CloudWatch Insights

## Pipeline 🔄

```
push to main, test/**, release/** or feature/**
        |
        v
    validate
    (ShellCheck)
        |
        v
    deploy-layers  (matrix: us-east-1, eu-central-1)
        |
        v
    deploy-functions  (matrix: us-east-1, eu-central-1)
        |
        v
    upload hashes to S3
```

## Directory Structure 📁

```
functions/
  <app-name>/
    <function-name>/
      index.js | lambda_function.py
      config.json
      package.json (optional)
layers/
  <layer-name>/
    package.json | requirements.txt
    config.json
scripts/
  expand-config.sh          # Parses config.json into shell variables
  generate-function-hashes.sh  # SHA-256 hashing for change detection
  get-alias.sh              # Maps git branch to Lambda alias
  install-packages.sh       # Multi-runtime package installer
```

## Function `config.json` ⚙️

```json
{
  "layers": [
    {
      "eu-central-1": ["MyLayer:1"],
      "us-east-1": ["MyLayer:2"]
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `layers` | Region-specific layer versions in `LayerName:Version` format |

The function itself is owned by Terraform (`lambda-functions-tf`): name, `runtime`,
`handler`, execution role, `timeout`, `memory_size`, environment. This repo owns only
the code and the layer attachment above. The function name is derived from the
directory name — `functions/<app>/my-function` deploys to `MyFunction`, matching
Terraform's `replace(title(name), "-", "")`. Directory names must therefore be
unique across apps.

## Layer `config.json` ⚙️

```json
{
  "name": "Axios",
  "description": "Axios layer for Node.js functions.",
  "type": "node",
  "runtimes": ["nodejs18.x", "nodejs20.x", "nodejs22.x"]
}
```

| Field | Description |
|-------|-------------|
| `name` | Lambda layer name |
| `description` | Layer description |
| `type` | Package type: `node`, `pip`, `golang`, `ruby` |
| `runtimes` | Compatible Lambda runtimes |

## Alias Strategy 👾 

| Branch Pattern | Alias | Purpose |
|---|---|---|
| `main` | `prod` | Production |
| `release/*` | `staging` | Pre-production |
| `test/*` | `test` | Testing |
| `feature/*` or other | `dev` | Development |

## Deployment Artifacts 📦 

Lambda packages are named with a timestamp and Git commit SHA:

| Type | S3 Key Pattern |
|------|---------------|
| Functions | `s3://<bucket>/<app>/<function>/<app>-<function>-<timestamp>-<sha>.zip` |
| Layers | `s3://<bucket>/<layer>/<layer>-<timestamp>-<sha>.zip` |

## Required Variables 🔧

These are configured as GitHub Actions environment variables/secrets per region:

| Name | Type | Description |
|------|------|-------------|
| `FUNCTIONS_S3_BUCKET` | variable | S3 bucket for Lambda function artifacts |
| `LAYERS_S3_BUCKET` | variable | S3 bucket for Lambda layer artifacts |
| `HASHES_S3_BUCKET` | variable | S3 bucket for hash-based change tracking |
| `ACCOUNT_NUMBER` | secret | AWS account number |

## Authentication 🔐

Authentication is handled via [GitHub OIDC federation](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services) -- no long-lived AWS credentials are stored in GitHub. The workflow assumes an IAM role (`GitHubActionsDeployRole`) scoped to this repository.

Infrastructure (IAM roles, S3 buckets, Lambda function shells) is managed in a separate Terraform repository.

## Adding a New Function ➕

1. Create `functions/<app-name>/<function-name>/` with your handler code — the
   kebab-case directory name maps to the function name defined in Terraform
2. Add a `config.json` with `layers` (empty list if none)
3. Ensure the Lambda function and IAM role exist in AWS (managed via Terraform)
4. Push to a recognized branch (`main`, `test/*`, `release/*`, `feature/*`) -- the pipeline handles the rest
