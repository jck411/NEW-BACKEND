"""Tests for backend main module."""

import argparse
import contextlib
from unittest.mock import MagicMock, patch

from backend.__main__ import launch_backend_server, main, parse_args


class TestBackendMain:
    """Test suite for backend main module."""

    def test_parse_args_default(self):
        """Test parse_args with default arguments."""
        with patch("sys.argv", ["backend"]):
            args = parse_args()
            assert args.server_path is None
            assert args.show_config is False
            assert args.verbose is False

    def test_parse_args_server_path(self):
        """Test parse_args with server path."""
        with patch("sys.argv", ["backend", "--server-path", "/path/to/server.py"]):
            args = parse_args()
            assert args.server_path == "/path/to/server.py"

    def test_parse_args_show_config(self):
        """Test parse_args with show-config flag."""
        with patch("sys.argv", ["backend", "--show-config"]):
            args = parse_args()
            assert args.show_config is True

    def test_parse_args_verbose(self):
        """Test parse_args with verbose flag."""
        with patch("sys.argv", ["backend", "--verbose"]):
            args = parse_args()
            assert args.verbose is True

    def test_parse_args_verbose_short(self):
        """Test parse_args with short verbose flag."""
        with patch("sys.argv", ["backend", "-v"]):
            args = parse_args()
            assert args.verbose is True

    def test_parse_args_all_options(self):
        """Test parse_args with all options."""
        with patch(
            "sys.argv",
            [
                "backend",
                "--server-path",
                "/path/to/server.py",
                "--show-config",
                "--verbose",
            ],
        ):
            args = parse_args()
            assert args.server_path == "/path/to/server.py"
            assert args.show_config is True
            assert args.verbose is True

    def test_parse_args_help(self):
        """Test parse_args help output."""
        with patch("sys.argv", ["backend", "--help"]):
            with patch("argparse.ArgumentParser.print_help") as mock_help:
                with contextlib.suppress(SystemExit):
                    parse_args()
                mock_help.assert_called_once()

    @patch("backend.__main__.ChatBot")
    @patch("backend.__main__.launch_backend_server")
    def test_main_default_behavior(self, mock_launch, mock_chatbot_class):
        """Test main function with default behavior."""
        mock_chatbot = MagicMock()
        mock_chatbot_class.return_value = mock_chatbot

        with patch("sys.argv", ["backend"]):
            main()

            # Should create chatbot
            mock_chatbot_class.assert_called_once()
            # Should launch backend server
            mock_launch.assert_called_once()

    @patch("backend.__main__.ChatBot")
    @patch("backend.__main__.launch_backend_server")
    def test_main_with_server_path(self, mock_launch, mock_chatbot_class):
        """Test main function with server path."""
        mock_chatbot = MagicMock()
        mock_chatbot_class.return_value = mock_chatbot

        with patch("sys.argv", ["backend", "--server-path", "/path/to/server.py"]):
            main()

            # Should set server path
            mock_chatbot.set_server_path.assert_called_once_with("/path/to/server.py")
            # Should launch backend server
            mock_launch.assert_called_once()

    @patch("backend.__main__.ChatBot")
    @patch("builtins.print")
    def test_main_show_config(self, mock_print, mock_chatbot_class):
        """Test main function with show-config flag."""
        mock_chatbot = MagicMock()
        mock_chatbot.get_configured_server_path.return_value = "/path/to/server.py"
        mock_chatbot.connection_config.get_backend_config.return_value = {
            "host": "localhost",
            "port": 8000,
            "enable_cors": True,
            "max_connections": 100,
        }
        mock_chatbot.connection_config.is_stt_enabled.return_value = True
        mock_chatbot_class.return_value = mock_chatbot

        with patch("sys.argv", ["backend", "--show-config"]):
            main()

            # Should show config
            mock_print.assert_called()
            mock_chatbot.get_configured_server_path.assert_called_once()
            mock_chatbot.connection_config.get_backend_config.assert_called_once()
            mock_chatbot.connection_config.is_stt_enabled.assert_called_once()

    @patch("backend.__main__.ChatBot")
    @patch("builtins.print")
    def test_main_show_config_error(self, mock_print, mock_chatbot_class):
        """Test main function with show-config flag and error."""
        mock_chatbot = MagicMock()
        mock_chatbot.get_configured_server_path.side_effect = Exception("Config error")
        mock_chatbot_class.return_value = mock_chatbot

        with patch("sys.argv", ["backend", "--show-config"]):
            main()

            # Should handle error gracefully
            mock_print.assert_called()

    @patch("backend.__main__.ChatBot")
    def test_main_keyboard_interrupt(self, mock_chatbot_class):
        """Test main function with keyboard interrupt."""
        mock_chatbot = MagicMock()
        mock_chatbot_class.side_effect = KeyboardInterrupt()
        mock_chatbot_class.return_value = mock_chatbot

        with patch("sys.argv", ["backend"]), patch("builtins.print") as mock_print:
            main()
            mock_print.assert_called_with("\n👋 Goodbye!")

    @patch("backend.__main__.ChatBot")
    def test_main_exception(self, mock_chatbot_class):
        """Test main function with exception."""
        MagicMock()
        mock_chatbot_class.side_effect = Exception("Test error")

        with patch("sys.argv", ["backend"]), patch("sys.exit") as mock_exit:
            with patch("builtins.print") as mock_print:
                main()
                mock_print.assert_called_with("\n❌ Error: Test error")
                mock_exit.assert_called_once_with(1)

    @patch("subprocess.run")
    @patch("pathlib.Path")
    def test_launch_backend_server_success(self, mock_path, mock_run):
        """Test launch_backend_server success."""
        mock_backend_script = MagicMock()
        mock_backend_script.exists.return_value = True
        mock_path.return_value.parent.parent.__truediv__.return_value = (
            mock_backend_script
        )

        with patch("builtins.print") as mock_print:
            launch_backend_server()

            mock_run.assert_called_once()
            mock_print.assert_called()

    @patch("pathlib.Path")
    def test_launch_backend_server_script_not_found(self, mock_path):
        """Test launch_backend_server with script not found."""
        mock_backend_script = MagicMock()
        mock_backend_script.exists.return_value = False
        mock_path.return_value.parent.parent.__truediv__.return_value = (
            mock_backend_script
        )

        with patch("sys.exit") as mock_exit:
            launch_backend_server()
            mock_exit.assert_called_once_with(1)

    @patch("subprocess.run")
    @patch("pathlib.Path")
    def test_launch_backend_server_subprocess_error(self, mock_path, mock_run):
        """Test launch_backend_server with subprocess error."""
        mock_backend_script = MagicMock()
        mock_backend_script.exists.return_value = True
        mock_path.return_value.parent.parent.__truediv__.return_value = (
            mock_backend_script
        )

        mock_run.side_effect = subprocess.CalledProcessError(1, "test")

        with patch("sys.exit") as mock_exit:
            launch_backend_server()
            mock_exit.assert_called_once_with(1)

    @patch("subprocess.run")
    @patch("pathlib.Path")
    def test_launch_backend_server_keyboard_interrupt(self, mock_path, mock_run):
        """Test launch_backend_server with keyboard interrupt."""
        mock_backend_script = MagicMock()
        mock_backend_script.exists.return_value = True
        mock_path.return_value.parent.parent.__truediv__.return_value = (
            mock_backend_script
        )

        mock_run.side_effect = KeyboardInterrupt()

        with patch("builtins.print") as mock_print:
            launch_backend_server()
            mock_print.assert_called_with("\n🛑 Server stopped by user")

    @patch("subprocess.run")
    @patch("pathlib.Path")
    def test_launch_backend_server_general_exception(self, mock_path, mock_run):
        """Test launch_backend_server with general exception."""
        mock_backend_script = MagicMock()
        mock_backend_script.exists.return_value = True
        mock_path.return_value.parent.parent.__truediv__.return_value = (
            mock_backend_script
        )

        mock_run.side_effect = Exception("Test error")

        with patch("sys.exit") as mock_exit:
            launch_backend_server()
            mock_exit.assert_called_once_with(1)

    def test_parse_args_help_text(self):
        """Test that help text contains expected information."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--server-path", help="Path to MCP server to use")
        parser.add_argument(
            "--show-config",
            action="store_true",
            help="Show current server configuration",
        )
        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Enable verbose logging"
        )

        # Test that arguments are properly defined
        assert any("--server-path" in str(action) for action in parser._actions)
        assert any("--show-config" in str(action) for action in parser._actions)
        assert any("--verbose" in str(action) for action in parser._actions)
        assert any("-v" in str(action) for action in parser._actions)

    @patch("backend.__main__.logging.basicConfig")
    def test_main_verbose_logging(self, mock_logging):
        """Test main function with verbose logging."""
        with (
            patch("sys.argv", ["backend", "--verbose"]),
            patch("backend.__main__.ChatBot"),
        ):
            with patch("backend.__main__.launch_backend_server"):
                main()
                mock_logging.assert_called_with(level=10)  # DEBUG level

    @patch("backend.__main__.logging.basicConfig")
    def test_main_normal_logging(self, mock_logging):
        """Test main function with normal logging."""
        with patch("sys.argv", ["backend"]), patch("backend.__main__.ChatBot"):
            with patch("backend.__main__.launch_backend_server"):
                main()
                mock_logging.assert_called_with(level=20)  # INFO level
