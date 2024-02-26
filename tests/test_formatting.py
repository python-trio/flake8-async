"""Test formatting in error codes."""

from flake8_async.visitors import ERROR_CLASSES


def test_error_messages_ends_with_period():
    for error_class in ERROR_CLASSES:
        for code, message in error_class.error_codes.items():
            assert message.endswith("."), f"{code} in {error_class} missing period."
