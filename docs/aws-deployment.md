# AWS Deployment Guide

## Overview

AI Support Assistant runs as a Docker container on Amazon EC2. It uses a private Amazon ECR repository for the container image and a private Amazon S3 bucket for the ChromaDB snapshot.

The application retrieves relevant CFPB consumer complaints from ChromaDB and sends the retrieved context to OpenAI to generate a grounded customer-support response.

## Architecture

1. A client sends an authenticated request to the FastAPI application.
2. EC2 runs the application inside a non-root Docker container.
3. The container loads the ChromaDB snapshot from private Amazon S3 storage.
4. Sentence Transformers converts the request into an embedding.
5. ChromaDB retrieves relevant CFPB complaints.
6. OpenAI generates a grounded response using the retrieved complaints.
7. The API validates citations and returns the answer, sources, and disclaimer.

## AWS resources

- **EC2:** Runs the FastAPI Docker container.
- **EBS:** Stores the operating system and container data.
- **ECR:** Stores private application container images.
- **S3:** Stores the compressed ChromaDB snapshot.
- **IAM role:** Gives EC2 limited access to ECR, S3, and Parameter Store.
- **Parameter Store:** Stores the OpenAI and application API keys as encrypted parameters.
- **Security group:** Allows API access on port 8000 only from an approved IP address.
- **Systems Manager:** Provides remote server management without opening SSH.
- **AWS Budgets:** Alerts when estimated monthly spending approaches the configured limit.

## Security decisions

- The application container runs as a non-root user.
- Root AWS access keys are not used.
- Application secrets are not stored in Git, Docker images, or EC2 user data.
- S3 public access is blocked.
- The EC2 instance uses temporary credentials supplied by an IAM role.
- The API requires an `X-API-Key` header.
- Port 22 is not exposed.
- Port 8000 is restricted to an approved public IP address.

## Start the demo server

The commands below locate the server using its readable `Name` tag, so no instance ID needs to be hard-coded.

```bash
export AWS_PROFILE=ai-support-browser
export AWS_REGION=us-east-1

INSTANCE_ID=$(aws ec2 describe-instances \
  --filters \
  'Name=tag:Name,Values=AI Support Assistant Demo Server' \
  'Name=instance-state-name,Values=stopped,running' \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text)

aws ec2 start-instances \
  --instance-ids "$INSTANCE_ID"

aws ec2 wait instance-status-ok \
  --instance-ids "$INSTANCE_ID"

PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "Health URL: http://${PUBLIC_IP}:8000/health"
```

The public IP normally changes whenever the stopped instance starts.

## Health check

```bash
curl "http://${PUBLIC_IP}:8000/health"
```

Expected response:

```json
{
  "status": "healthy"
}
```

## Stop the demo server

```bash
aws ec2 stop-instances \
  --instance-ids "$INSTANCE_ID"
```

Stopping the instance ends EC2 compute charges. EBS, ECR, and S3 continue to incur small storage charges.

## Automated demo deployments

The **Deploy demo to AWS** GitHub Actions workflow performs an intentional, manual deployment. It does not start a stopped EC2 instance. This prevents a code push from unexpectedly turning on billable demo infrastructure.

The workflow:

1. authenticates to AWS using GitHub OpenID Connect (OIDC), not stored AWS access keys;
2. confirms EC2 is already running and online in Systems Manager;
3. builds and pushes an immutable image tagged with the Git commit;
4. deploys through Systems Manager without SSH;
5. retrieves application secrets directly on EC2 from Parameter Store;
6. verifies the `/health` endpoint; and
7. automatically restores the previous image if the new container is unhealthy.

Create a protected GitHub environment named `demo` and add these environment variables:

| Variable | Example purpose |
| --- | --- |
| `AWS_ROLE_ARN` | IAM role trusted by this GitHub repository through OIDC |
| `AWS_REGION` | `us-east-1` |
| `ECR_REPOSITORY` | `ai-support-assistant` |
| `EC2_INSTANCE_ID` | The demo server instance ID |
| `OPENAI_API_KEY_PARAMETER` | Encrypted Parameter Store name for the OpenAI key |
| `APP_API_KEY_PARAMETER` | Encrypted Parameter Store name for the application key |
| `RAG_SNAPSHOT_S3_BUCKET` | Private bucket containing the ChromaDB snapshot |
| `RAG_SNAPSHOT_S3_KEY` | Object key for the compressed snapshot |

No secret values belong in these variables. The two key-related variables contain only Parameter Store names. Configure the `demo` environment with required reviewer approval if another person may operate the repository.

To deploy:

1. intentionally start the EC2 demo server;
2. open **GitHub → Actions → Deploy demo to AWS**;
3. choose **Run workflow**;
4. enter `deploy` for confirmation; and
5. review the deployment summary before using the demo.

## Estimated demo cost

A `t3.medium` instance and public IPv4 address cost approximately five cents per running hour in `us-east-1`. A short demonstration should cost well below one dollar.

This estimate excludes OpenAI API usage and may change as AWS pricing changes.

## Production improvements

Before exposing the service to general internet traffic:

- place the API behind HTTPS;
- use a custom domain;
- add CloudWatch alarms and log retention;
- implement request rate limiting;
- restrict deployment permissions further;
- automate infrastructure creation using infrastructure as code.
