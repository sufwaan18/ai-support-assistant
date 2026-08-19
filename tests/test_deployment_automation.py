import json
import subprocess
from pathlib import Path

import pytest

from scripts.render_ssm_command import render_command


PROJECT_ROOT = Path(__file__).parent.parent
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "deploy.yml"


def test_deployment_script_has_valid_bash_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", "scripts/deploy_ec2.sh"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_workflow_uses_oidc_without_stored_aws_credentials() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "id-token: write" in workflow
    assert "AI-Support-Assistant-GitHub-Deploy" in workflow
    assert "AWS_ACCESS_KEY_ID" not in workflow
    assert "AWS_SECRET_ACCESS_KEY" not in workflow
    assert "secrets.OPENAI_API_KEY" not in workflow


def test_render_command_quotes_deployment_values() -> None:
    parameters = render_command(
        "echo deployment",
        {
            "IMAGE_URI": "example/image:sha-123",
            "OPENAI_API_KEY_PARAMETER": "/app/openai key",
            "APP_API_KEY_PARAMETER": "/app/api-key",
            "RAG_SNAPSHOT_S3_BUCKET": "example-bucket",
            "RAG_SNAPSHOT_S3_KEY": "snapshots/chroma.tar.gz",
        },
    )

    serialized = json.dumps(parameters)
    assert "export IMAGE_URI=example/image:sha-123" in serialized
    assert "'/app/openai key'" in serialized
    assert "echo deployment" in serialized


def test_render_command_rejects_missing_values() -> None:
    with pytest.raises(
        ValueError,
        match="Missing deployment values: APP_API_KEY_PARAMETER",
    ):
        render_command(
            "echo deployment",
            {
                "IMAGE_URI": "example/image:latest",
                "OPENAI_API_KEY_PARAMETER": "/app/openai-key",
                "APP_API_KEY_PARAMETER": "",
                "RAG_SNAPSHOT_S3_BUCKET": "example-bucket",
                "RAG_SNAPSHOT_S3_KEY": "snapshot.tar.gz",
            },
        )
