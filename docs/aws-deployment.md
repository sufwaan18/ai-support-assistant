# Tytus.ai AWS deployment notes

This page covers how I run the project as a small AWS demo. The setup is meant for short portfolio demonstrations, not public production traffic.

## Setup

The FastAPI app runs inside a Docker container on EC2. Caddy runs beside it and handles HTTPS for `sufwaan.shop` and `www.sufwaan.shop`. The container image is kept in a private ECR repository. A compressed copy of the ChromaDB database is kept in a private S3 bucket and loaded when the app starts.

The request flow is:

1. The user sends a question to the FastAPI app.
2. Sentence Transformers creates an embedding for the question.
3. ChromaDB finds related CFPB complaints.
4. OpenAI drafts an answer using those complaints.
5. The API checks the citations and returns the answer and sources.

The AWS services used here are EC2, ECR, S3, IAM, Parameter Store, Systems Manager, EBS, and AWS Budgets.

## Security choices

I kept the demo private and avoided saving secrets in the repository.

- The Docker container runs as a non-root user.
- The EC2 instance uses an IAM role with limited permissions.
- The OpenAI key and application key are stored in Parameter Store.
- The S3 bucket blocks public access.
- SSH is not open. I manage deployments through Systems Manager.
- Port 8000 is limited to an approved IP address.
- Paid AI routes require access and have a request limit.

## Start the demo server

Set the AWS profile and region first:

```bash
export AWS_PROFILE=ai-support-browser
export AWS_REGION=us-east-1
```

Find the instance by its name and start it:

```bash
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters \
  'Name=tag:Name,Values=AI Support Assistant Demo Server' \
  'Name=instance-state-name,Values=stopped,running' \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text)

aws ec2 start-instances --instance-ids "$INSTANCE_ID"
aws ec2 wait instance-status-ok --instance-ids "$INSTANCE_ID"
```

Find the current public IP address:

```bash
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "http://${PUBLIC_IP}:8000"
```

The address can change after the instance is stopped and started. When it changes, update the `A` records for `sufwaan.shop` and `www.sufwaan.shop` in Route 53. A TTL of 300 seconds keeps this manual update reasonably quick.

Check that the public HTTPS endpoint is running:

```bash
curl "https://sufwaan.shop/health"
```

The response should be:

```json
{
  "status": "healthy"
}
```

## Stop the demo server

```bash
aws ec2 stop-instances --instance-ids "$INSTANCE_ID"
```

Stopping the instance ends the main EC2 compute charge. EBS, ECR, S3, and the public IPv4 address may still have small charges depending on the account setup.

## Deploy a new version

Deployment is a manual GitHub Actions job. It will not start a stopped EC2 instance. This is intentional because I do not want a push to turn on paid demo resources.

The workflow does the following:

1. Connects to AWS through GitHub OIDC.
2. Checks that the EC2 instance is running and available in Systems Manager.
3. Builds a Docker image tagged with the Git commit.
4. Pushes the image to ECR.
5. Runs the deployment on EC2 through Systems Manager.
6. Loads secrets from Parameter Store on the instance.
7. Checks the health route and rolls back if the new container is unhealthy.

The GitHub environment is named `demo`. The deployment workflow needs these settings:

| Name | What it is used for |
| --- | --- |
| `AWS_ROLE_ARN` | IAM role trusted by this GitHub repository |
| `AWS_REGION` | AWS region, such as `us-east-1` |
| `ECR_REPOSITORY` | Name of the ECR repository |
| `EC2_INSTANCE_ID` | Demo EC2 instance ID |
| `OPENAI_API_KEY_PARAMETER` | Parameter Store name for the OpenAI key |
| `APP_API_KEY_PARAMETER` | Parameter Store name for the app key |
| `RAG_SNAPSHOT_S3_BUCKET` | Private bucket containing the database snapshot |
| `RAG_SNAPSHOT_S3_KEY` | Object key for the database snapshot |

The two key settings above contain Parameter Store names, not the secret values.

To deploy:

1. Start the EC2 instance and wait until it is ready.
2. Open the `Deploy demo to AWS` workflow in GitHub Actions.
3. Select `Run workflow`.
4. Enter `deploy` when asked for confirmation.
5. Check the workflow summary after it finishes.

## Cost note

I stop the EC2 instance when I am not using the demo. AWS prices can change, and OpenAI usage is billed separately, so I check the AWS billing page and budget alerts instead of relying on a fixed estimate in this file.

## What I would add for public use

The application already uses HTTPS and a custom domain. The next production improvements would be CloudWatch alarms and log retention, stricter deployment permissions, and infrastructure as code.
