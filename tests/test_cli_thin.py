import pytest
from unittest.mock import MagicMock, patch
from smartmyodoo.cli import InteractiveCLI


@pytest.fixture(autouse=True)
def mock_prompt_session():
    with patch("smartmyodoo.cli.PromptSession") as MockSession:
        yield MockSession


def test_cli_initialization():
    mock_client = MagicMock()

    def dummy_callback(msg):
        return {"response": "Test", "tools_used": []}

    cli = InteractiveCLI(callback=dummy_callback, http_client=mock_client)
    assert cli.http_client == mock_client
    assert cli.workspace_id == "default"


def test_cli_show_previous_sessions_success():
    mock_client = MagicMock()
    mock_client.list_sessions.return_value = [
        {
            "session_id": "ses1",
            "preview": "Hello",
            "message_count": 1,
            "last_activity": "2026-06-08",
        }
    ]

    cli = InteractiveCLI(callback=lambda x: {}, http_client=mock_client)

    with patch.object(cli.console, "print") as mock_print:
        # We don't need to patch prompt because PromptSession is already patched globally in this file via fixture
        cli._show_previous_sessions()

        # Verify the client was called
        mock_client.list_sessions.assert_called_once_with("default", limit=5)
        # Verify print was called for the table
        assert mock_print.call_count >= 1


def test_cli_show_previous_sessions_no_client():
    cli = InteractiveCLI(callback=lambda x: {})  # no client

    with patch.object(cli.console, "print") as mock_print:
        cli._show_previous_sessions()
        mock_print.assert_not_called()


def test_cli_show_previous_sessions_api_error():
    mock_client = MagicMock()
    mock_client.list_sessions.side_effect = Exception("API Down")

    cli = InteractiveCLI(callback=lambda x: {}, http_client=mock_client)

    with patch.object(cli.console, "print") as mock_print:
        cli._show_previous_sessions()

        # Verify it printed the error
        mock_print.assert_called_once()
        assert "Nie udało się pobrać sesji: API Down" in mock_print.call_args[0][0]


def test_cli_url_param_forwarded(mocker):
    import sys
    from smartmyodoo.__main__ import main

    mocker.patch.object(sys, "argv", ["smartmyodoo", "--url", "http://custom-url:9999"])
    mocker.patch("getpass.getpass", return_value="1111")
    mocker.patch(
        "smartmyodoo.http_client.SmartMyOdooClient.login",
        return_value={"success": True},
    )

    mock_cli = mocker.patch("smartmyodoo.__main__.InteractiveCLI")
    mock_cli.return_value.run = MagicMock()

    main()

    mock_cli.assert_called_once()
    kwargs = mock_cli.call_args[1]
    client = kwargs["http_client"]
    assert client.base_url == "http://custom-url:9999"
