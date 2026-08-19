import argparse
import json
import shlex
from pathlib import Path


DEPLOYMENT_VARIABLES = (
    "IMAGE_URI",
    "OPENAI_API_KEY_PARAMETER",
    "APP_API_KEY_PARAMETER",
    "RAG_SNAPSHOT_S3_BUCKET",
    "RAG_SNAPSHOT_S3_KEY",
)


def render_command(script: str, values: dict[str, str]) -> dict[str, list[str]]:
    """Build safe AWS Systems Manager command parameters."""

    missing = [name for name in DEPLOYMENT_VARIABLES if not values.get(name)]
    if missing:
        raise ValueError(
            "Missing deployment values: " + ", ".join(missing)
        )

    exports = [
        f"export {name}={shlex.quote(values[name])}"
        for name in DEPLOYMENT_VARIABLES
    ]
    command = "\n".join([*exports, script])
    return {"commands": [command]}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    for variable_name in DEPLOYMENT_VARIABLES:
        option_name = "--" + variable_name.lower().replace("_", "-")
        parser.add_argument(option_name, dest=variable_name, required=True)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    values = {
        name: getattr(arguments, name)
        for name in DEPLOYMENT_VARIABLES
    }
    parameters = render_command(
        arguments.script.read_text(encoding="utf-8"),
        values,
    )
    arguments.output.write_text(
        json.dumps(parameters),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
