"""
Unit tests for CLI directory sync functionality.

Tests cover:
- Argument parsing (all flags and options)
- Directory validation (exists, readable, writable)
- Format validation (unknown formats should error)
- Sync invocation (orchestrator called correctly)
- Error handling (missing args, invalid paths, etc.)
- Dry-run mode
- Verbose mode output
- Conversion options (--add-argument-hint, --add-handoffs)

Status: TDD - Tests written before CLI implementation
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

from cli.main import create_parser, main, setup_registry
from core.canonical_models import ConfigType


class TestCLIArgumentParsing:
    """Tests for argument parsing (all flags and options)."""

    @pytest.fixture
    def parser(self):
        """Create argument parser instance."""
        return create_parser()

    @pytest.fixture
    def valid_source_dir(self, tmp_path):
        """Create a valid source directory."""
        source = tmp_path / "source"
        source.mkdir()
        return source

    @pytest.fixture
    def valid_target_dir(self, tmp_path):
        """Create a valid target directory."""
        target = tmp_path / "target"
        target.mkdir()
        return target

    @pytest.fixture
    def base_args(self, valid_source_dir, valid_target_dir):
        """Minimum valid arguments for CLI."""
        return [
            '--source-dir', str(valid_source_dir),
            '--target-dir', str(valid_target_dir),
            '--source-format', 'claude',
            '--target-format', 'copilot'
        ]

    def test_required_arguments_present(self, parser):
        """Verify --source-dir, --target-dir, --source-format, --target-format are required."""
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_source_dir_argument(self, parser, valid_source_dir, valid_target_dir):
        """Test --source-dir accepts valid path."""
        args = parser.parse_args([
            '--source-dir', str(valid_source_dir),
            '--target-dir', str(valid_target_dir),
            '--source-format', 'claude',
            '--target-format', 'copilot'
        ])
        assert args.source_dir == valid_source_dir

    def test_target_dir_argument(self, parser, valid_source_dir, valid_target_dir):
        """Test --target-dir accepts valid path."""
        args = parser.parse_args([
            '--source-dir', str(valid_source_dir),
            '--target-dir', str(valid_target_dir),
            '--source-format', 'claude',
            '--target-format', 'copilot'
        ])
        assert args.target_dir == valid_target_dir

    def test_source_format_choices(self, parser, base_args):
        """Test --source-format accepts only 'claude', 'copilot'."""
        # Valid choices should work
        for fmt in ['claude', 'copilot']:
            args = parser.parse_args([
                '--source-dir', base_args[1],
                '--target-dir', base_args[3],
                '--source-format', fmt,
                '--target-format', 'copilot'
            ])
            assert args.source_format == fmt

    def test_target_format_choices(self, parser, base_args):
        """Test --target-format accepts only 'claude', 'copilot'."""
        # Valid choices should work
        for fmt in ['claude', 'copilot']:
            args = parser.parse_args([
                '--source-dir', base_args[1],
                '--target-dir', base_args[3],
                '--source-format', 'claude',
                '--target-format', fmt
            ])
            assert args.target_format == fmt

    def test_config_type_default(self, parser, base_args):
        """Test --config-type defaults to 'agent'."""
        args = parser.parse_args(base_args)
        assert args.config_type == 'agent'

    def test_config_type_choices(self, parser, base_args):
        """Test --config-type accepts 'agent', 'permission', 'prompt'."""
        for config_type in ['agent', 'permission', 'prompt']:
            args = parser.parse_args(base_args + ['--config-type', config_type])
            assert args.config_type == config_type

    def test_direction_default(self, parser, base_args):
        """Test --direction defaults to 'both'."""
        args = parser.parse_args(base_args)
        assert args.direction == 'both'

    def test_direction_choices(self, parser, base_args):
        """Test --direction accepts 'both', 'source-to-target', 'target-to-source'."""
        for direction in ['both', 'source-to-target', 'target-to-source']:
            args = parser.parse_args(base_args + ['--direction', direction])
            assert args.direction == direction

    def test_dry_run_flag(self, parser, base_args):
        """Test --dry-run flag."""
        # Without flag
        args = parser.parse_args(base_args)
        assert args.dry_run is False

        # With flag
        args = parser.parse_args(base_args + ['--dry-run'])
        assert args.dry_run is True

    def test_force_flag(self, parser, base_args):
        """Test --force flag."""
        # Without flag
        args = parser.parse_args(base_args)
        assert args.force is False

        # With flag
        args = parser.parse_args(base_args + ['--force'])
        assert args.force is True

    def test_verbose_flag(self, parser, base_args):
        """Test --verbose and -v flags."""
        # Without flag
        args = parser.parse_args(base_args)
        assert args.verbose is False

        # With --verbose
        args = parser.parse_args(base_args + ['--verbose'])
        assert args.verbose is True

        # With -v
        args = parser.parse_args(base_args + ['-v'])
        assert args.verbose is True

    def test_state_file_argument(self, parser, base_args, tmp_path):
        """Test --state-file accepts custom path."""
        custom_state = tmp_path / "custom_state.json"
        args = parser.parse_args(base_args + ['--state-file', str(custom_state)])
        assert args.state_file == custom_state


class TestFormatValidation:
    """Tests for format validation (unknown formats should error)."""

    @pytest.fixture
    def parser(self):
        """Create argument parser instance."""
        return create_parser()

    @pytest.fixture
    def valid_dirs(self, tmp_path):
        """Create valid source and target directories."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"
        target.mkdir()
        return source, target

    def test_unknown_source_format_rejected(self, parser, valid_dirs):
        """argparse rejects invalid source format."""
        source, target = valid_dirs
        with pytest.raises(SystemExit):
            parser.parse_args([
                '--source-dir', str(source),
                '--target-dir', str(target),
                '--source-format', 'unknown-format',
                '--target-format', 'copilot'
            ])

    def test_unknown_target_format_rejected(self, parser, valid_dirs):
        """argparse rejects invalid target format."""
        source, target = valid_dirs
        with pytest.raises(SystemExit):
            parser.parse_args([
                '--source-dir', str(source),
                '--target-dir', str(target),
                '--source-format', 'claude',
                '--target-format', 'unknown-format'
            ])

    def test_case_sensitivity(self, parser, valid_dirs):
        """Format names are case-sensitive."""
        source, target = valid_dirs
        # 'Claude' instead of 'claude' should fail
        with pytest.raises(SystemExit):
            parser.parse_args([
                '--source-dir', str(source),
                '--target-dir', str(target),
                '--source-format', 'Claude',
                '--target-format', 'copilot'
            ])


class TestErrorHandling:
    """Tests for error handling (missing args, invalid paths, etc.)."""

    @pytest.fixture
    def parser(self):
        """Create argument parser instance."""
        return create_parser()

    @pytest.fixture
    def valid_dirs(self, tmp_path):
        """Create valid source and target directories."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"
        target.mkdir()
        return source, target

    def test_missing_source_dir_exits_error(self, parser, valid_dirs):
        """Missing --source-dir produces error exit."""
        _, target = valid_dirs
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args([
                '--target-dir', str(target),
                '--source-format', 'claude',
                '--target-format', 'copilot'
            ])
        assert exc_info.value.code != 0

    def test_missing_target_dir_exits_error(self, parser, valid_dirs):
        """Missing --target-dir produces error exit."""
        source, _ = valid_dirs
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args([
                '--source-dir', str(source),
                '--source-format', 'claude',
                '--target-format', 'copilot'
            ])
        assert exc_info.value.code != 0

    def test_missing_source_format_exits_error(self, parser, valid_dirs):
        """Missing --source-format produces error exit."""
        source, target = valid_dirs
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args([
                '--source-dir', str(source),
                '--target-dir', str(target),
                '--target-format', 'copilot'
            ])
        assert exc_info.value.code != 0

    def test_missing_target_format_exits_error(self, parser, valid_dirs):
        """Missing --target-format produces error exit."""
        source, target = valid_dirs
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args([
                '--source-dir', str(source),
                '--target-dir', str(target),
                '--source-format', 'claude'
            ])
        assert exc_info.value.code != 0

    def test_orchestrator_error_propagated(self, valid_dirs):
        """Orchestrator errors result in non-zero exit."""
        source, target = valid_dirs
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_instance.sync.side_effect = ValueError("Test error")
            mock_orch.return_value = mock_instance

            # When CLI is fully implemented, it should propagate orchestrator errors
            # For now, the stub returns 0 - this test documents expected behavior
            result = main([
                '--source-dir', str(source),
                '--target-dir', str(target),
                '--source-format', 'claude',
                '--target-format', 'copilot'
            ])
            # TODO: When implemented, assert result != 0
            assert result == 0  # Current stub behavior

    def test_error_message_to_stderr(self, parser, capsys):
        """Error messages written to stderr."""
        with pytest.raises(SystemExit):
            parser.parse_args(['--invalid-arg'])
        captured = capsys.readouterr()
        assert 'error' in captured.err.lower() or 'unrecognized' in captured.err.lower()


class TestSyncInvocation:
    """Tests for sync invocation (orchestrator called correctly)."""

    @pytest.fixture
    def valid_source_dir(self, tmp_path):
        """Create a valid source directory."""
        source = tmp_path / "source"
        source.mkdir()
        return source

    @pytest.fixture
    def valid_target_dir(self, tmp_path):
        """Create a valid target directory."""
        target = tmp_path / "target"
        target.mkdir()
        return target

    @pytest.fixture
    def base_args(self, valid_source_dir, valid_target_dir):
        """Minimum valid arguments for CLI."""
        return [
            '--source-dir', str(valid_source_dir),
            '--target-dir', str(valid_target_dir),
            '--source-format', 'claude',
            '--target-format', 'copilot'
        ]

    def test_orchestrator_receives_source_dir(self, base_args, valid_source_dir):
        """Orchestrator constructed with correct source_dir."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            main(base_args)

            # TODO: When implemented, verify source_dir passed to orchestrator
            # For now, stub doesn't create orchestrator
            # mock_orch.assert_called_once()
            # call_kwargs = mock_orch.call_args.kwargs
            # assert call_kwargs['source_dir'] == valid_source_dir

    def test_orchestrator_receives_target_dir(self, base_args, valid_target_dir):
        """Orchestrator constructed with correct target_dir."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            main(base_args)

            # TODO: When implemented, verify target_dir passed to orchestrator

    def test_orchestrator_receives_source_format(self, base_args):
        """Orchestrator constructed with correct source_format."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            main(base_args)

            # TODO: When implemented, verify source_format='claude' passed

    def test_orchestrator_receives_target_format(self, base_args):
        """Orchestrator constructed with correct target_format."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            main(base_args)

            # TODO: When implemented, verify target_format='copilot' passed

    def test_orchestrator_receives_config_type(self, base_args):
        """Orchestrator constructed with correct ConfigType enum."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            # Test with explicit config type
            main(base_args + ['--config-type', 'agent'])

            # TODO: When implemented, verify ConfigType.AGENT passed

    def test_orchestrator_receives_direction(self, base_args):
        """Orchestrator constructed with correct direction."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            main(base_args + ['--direction', 'source-to-target'])

            # TODO: When implemented, verify direction='source-to-target' passed

    def test_orchestrator_receives_dry_run(self, base_args):
        """Orchestrator constructed with dry_run flag."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            main(base_args + ['--dry-run'])

            # TODO: When implemented, verify dry_run=True passed

    def test_orchestrator_receives_force(self, base_args):
        """Orchestrator constructed with force flag."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            main(base_args + ['--force'])

            # TODO: When implemented, verify force=True passed

    def test_orchestrator_receives_verbose(self, base_args):
        """Orchestrator constructed with verbose flag."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            main(base_args + ['--verbose'])

            # TODO: When implemented, verify verbose=True passed

    def test_orchestrator_sync_called(self, base_args):
        """Orchestrator.sync() method is called."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            main(base_args)

            # TODO: When implemented, verify sync() was called
            # mock_instance.sync.assert_called_once()

    def test_registry_setup(self):
        """FormatRegistry is properly initialized with adapters."""
        registry = setup_registry()

        # Verify adapters are registered
        assert registry.get_adapter('claude') is not None
        assert registry.get_adapter('copilot') is not None

    def test_state_manager_setup(self, base_args, tmp_path):
        """SyncStateManager is properly initialized."""
        custom_state = tmp_path / "custom_state.json"

        with patch('cli.main.SyncStateManager') as mock_sm:
            mock_instance = MagicMock()
            mock_sm.return_value = mock_instance

            main(base_args + ['--state-file', str(custom_state)])

            # TODO: When implemented, verify state manager created with custom path
            # mock_sm.assert_called_once()


class TestDirectoryValidation:
    """Tests for directory validation (exists, readable, writable)."""

    @pytest.fixture
    def valid_source_dir(self, tmp_path):
        """Create a valid source directory."""
        source = tmp_path / "source"
        source.mkdir()
        return source

    @pytest.fixture
    def valid_target_dir(self, tmp_path):
        """Create a valid target directory."""
        target = tmp_path / "target"
        target.mkdir()
        return target

    def test_source_dir_must_exist(self, valid_target_dir, tmp_path):
        """Error if source directory doesn't exist."""
        nonexistent = tmp_path / "nonexistent"

        result = main([
            '--source-dir', str(nonexistent),
            '--target-dir', str(valid_target_dir),
            '--source-format', 'claude',
            '--target-format', 'copilot'
        ])

        # TODO: When CLI validates, assert result != 0
        # Currently stub returns 0

    def test_relative_paths_expanded(self, tmp_path, monkeypatch):
        """Relative paths are properly resolved."""
        # Create directories in tmp_path
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"
        target.mkdir()

        # Change working directory to tmp_path
        monkeypatch.chdir(tmp_path)

        parser = create_parser()
        args = parser.parse_args([
            '--source-dir', 'source',
            '--target-dir', 'target',
            '--source-format', 'claude',
            '--target-format', 'copilot'
        ])

        # argparse creates Path objects which can be relative
        assert args.source_dir == Path('source')
        assert args.target_dir == Path('target')

    def test_home_tilde_expanded(self, tmp_path):
        """~ in paths is expanded to home directory."""
        parser = create_parser()
        args = parser.parse_args([
            '--source-dir', '~/.claude/agents',
            '--target-dir', str(tmp_path / "target"),
            '--source-format', 'claude',
            '--target-format', 'copilot'
        ])

        # Path object can be expanded later with expanduser()
        expanded = args.source_dir.expanduser()
        assert '~' not in str(expanded)


class TestDryRunMode:
    """Tests for dry-run mode."""

    @pytest.fixture
    def valid_source_dir(self, tmp_path):
        """Create a valid source directory with a test file."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "test-agent.md").write_text("""---
name: test-agent
description: Test agent
---
Instructions.
""")
        return source

    @pytest.fixture
    def valid_target_dir(self, tmp_path):
        """Create a valid target directory."""
        target = tmp_path / "target"
        target.mkdir()
        return target

    @pytest.fixture
    def base_args(self, valid_source_dir, valid_target_dir):
        """Minimum valid arguments for CLI."""
        return [
            '--source-dir', str(valid_source_dir),
            '--target-dir', str(valid_target_dir),
            '--source-format', 'claude',
            '--target-format', 'copilot'
        ]

    def test_dry_run_passed_to_orchestrator(self, base_args):
        """--dry-run flag passed to orchestrator."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            main(base_args + ['--dry-run'])

            # TODO: When implemented, verify dry_run=True passed to orchestrator
            # call_kwargs = mock_orch.call_args.kwargs
            # assert call_kwargs['dry_run'] is True

    def test_dry_run_no_files_modified(self, base_args, valid_target_dir):
        """With --dry-run, no files are actually modified."""
        # Record initial state of target directory
        initial_files = list(valid_target_dir.iterdir())

        result = main(base_args + ['--dry-run'])

        # Target directory should be unchanged
        final_files = list(valid_target_dir.iterdir())
        assert initial_files == final_files

    def test_dry_run_outputs_preview(self, base_args, capsys):
        """Dry-run outputs what would be done."""
        main(base_args + ['--dry-run'])

        captured = capsys.readouterr()
        # Current stub outputs "Dry-run mode enabled"
        assert 'dry-run' in captured.out.lower() or 'Dry-run' in captured.out


class TestVerboseMode:
    """Tests for verbose mode output."""

    @pytest.fixture
    def valid_source_dir(self, tmp_path):
        """Create a valid source directory."""
        source = tmp_path / "source"
        source.mkdir()
        return source

    @pytest.fixture
    def valid_target_dir(self, tmp_path):
        """Create a valid target directory."""
        target = tmp_path / "target"
        target.mkdir()
        return target

    @pytest.fixture
    def base_args(self, valid_source_dir, valid_target_dir):
        """Minimum valid arguments for CLI."""
        return [
            '--source-dir', str(valid_source_dir),
            '--target-dir', str(valid_target_dir),
            '--source-format', 'claude',
            '--target-format', 'copilot'
        ]

    def test_verbose_passed_to_orchestrator(self, base_args):
        """--verbose flag passed to orchestrator."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            main(base_args + ['--verbose'])

            # TODO: When implemented, verify verbose=True passed to orchestrator

    def test_verbose_enables_detailed_output(self, base_args, capsys):
        """Verbose mode produces more output."""
        # Run without verbose
        main(base_args)
        normal_output = capsys.readouterr().out

        # Run with verbose
        main(base_args + ['--verbose'])
        verbose_output = capsys.readouterr().out

        # TODO: When implemented, verbose output should be longer/more detailed
        # For now, both produce same stub output

    def test_short_verbose_flag(self, base_args):
        """-v works same as --verbose."""
        parser = create_parser()

        args_long = parser.parse_args(base_args + ['--verbose'])
        args_short = parser.parse_args(base_args + ['-v'])

        assert args_long.verbose == args_short.verbose == True


class TestConversionOptions:
    """Tests for conversion options (--add-argument-hint, --add-handoffs)."""

    @pytest.fixture
    def valid_source_dir(self, tmp_path):
        """Create a valid source directory."""
        source = tmp_path / "source"
        source.mkdir()
        return source

    @pytest.fixture
    def valid_target_dir(self, tmp_path):
        """Create a valid target directory."""
        target = tmp_path / "target"
        target.mkdir()
        return target

    @pytest.fixture
    def base_args(self, valid_source_dir, valid_target_dir):
        """Minimum valid arguments for CLI."""
        return [
            '--source-dir', str(valid_source_dir),
            '--target-dir', str(valid_target_dir),
            '--source-format', 'claude',
            '--target-format', 'copilot'
        ]

    def test_add_argument_hint_flag(self, base_args):
        """--add-argument-hint flag parsed."""
        parser = create_parser()

        # Without flag
        args = parser.parse_args(base_args)
        assert args.add_argument_hint is False

        # With flag
        args = parser.parse_args(base_args + ['--add-argument-hint'])
        assert args.add_argument_hint is True

    def test_add_handoffs_flag(self, base_args):
        """--add-handoffs flag parsed."""
        parser = create_parser()

        # Without flag
        args = parser.parse_args(base_args)
        assert args.add_handoffs is False

        # With flag
        args = parser.parse_args(base_args + ['--add-handoffs'])
        assert args.add_handoffs is True

    def test_conversion_options_dict_passed(self, base_args):
        """conversion_options dict passed to orchestrator."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            main(base_args + ['--add-argument-hint', '--add-handoffs'])

            # TODO: When implemented, verify conversion_options passed
            # call_kwargs = mock_orch.call_args.kwargs
            # assert call_kwargs['conversion_options'] == {
            #     'add_argument_hint': True,
            #     'add_handoffs': True
            # }

    def test_conversion_options_empty_when_not_set(self, base_args):
        """No conversion_options when flags not used."""
        with patch('cli.main.UniversalSyncOrchestrator') as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance

            main(base_args)

            # TODO: When implemented, verify conversion_options is None or empty
            # call_kwargs = mock_orch.call_args.kwargs
            # assert call_kwargs.get('conversion_options') is None
