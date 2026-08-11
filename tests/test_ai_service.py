from unittest.mock import Mock

from app.ai_service import generate_support_reply


def test_generate_support_reply() -> None:
    mock_client = Mock()
    mock_client.responses.create.return_value.output_text = (
        "Please check your spam folder and request a new reset email."
    )

    reply = generate_support_reply(
        subject="Cannot reset password",
        message="The password reset email never arrives.",
        client=mock_client,
    )

    assert reply == (
        "Please check your spam folder and request a new reset email."
    )
    mock_client.responses.create.assert_called_once()