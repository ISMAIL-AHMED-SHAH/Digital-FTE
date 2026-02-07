"""Integration Tests for Watchdog Process (T071).

Tests for:
- Process crash detection
- Auto-restart behavior
- Max restart limits
- Alert generation
"""

import asyncio
import json
import os
import pytest
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestWatchdogProcessMonitoring:
    """Tests for watchdog process monitoring."""

    @pytest.mark.asyncio
    async def test_detect_process_crash(self):
        """Test detecting when a monitored process crashes."""
        from orchestrator.watchdog import Watchdog, ProcessConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            watchdog = Watchdog(
                state_dir=Path(tmpdir),
                check_interval=0.1
            )

            # Register a mock process that will "crash"
            config = ProcessConfig(
                name="test_process",
                command="echo test",
                restart_on_crash=True,
                max_restarts=3
            )
            watchdog.register_process(config)

            # Simulate process running then crashing
            watchdog._processes["test_process"] = {
                "pid": 99999,  # Non-existent PID
                "status": "running",
                "restarts": 0
            }

            # Check should detect the "crashed" process
            crashed = await watchdog.check_processes()

            assert "test_process" in crashed

    @pytest.mark.asyncio
    async def test_auto_restart_crashed_process(self):
        """Test automatic restart of crashed process."""
        from orchestrator.watchdog import Watchdog, ProcessConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            watchdog = Watchdog(
                state_dir=Path(tmpdir),
                check_interval=0.1
            )

            restart_count = 0

            async def mock_start_process(name, command):
                nonlocal restart_count
                restart_count += 1
                return {"pid": 12345 + restart_count, "status": "running"}

            watchdog._start_process = mock_start_process

            config = ProcessConfig(
                name="test_process",
                command="echo test",
                restart_on_crash=True,
                max_restarts=5
            )
            watchdog.register_process(config)

            # Trigger restart
            await watchdog.restart_process("test_process", reason="Test crash")

            assert restart_count == 1
            assert watchdog._processes["test_process"]["restarts"] == 1

    @pytest.mark.asyncio
    async def test_max_restarts_limit(self):
        """Test process isn't restarted beyond max limit."""
        from orchestrator.watchdog import Watchdog, ProcessConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            watchdog = Watchdog(
                state_dir=Path(tmpdir),
                check_interval=0.1
            )

            config = ProcessConfig(
                name="test_process",
                command="echo test",
                restart_on_crash=True,
                max_restarts=2
            )
            watchdog.register_process(config)

            # Set restarts to max
            watchdog._processes["test_process"]["restarts"] = 2

            # Should not restart
            result = await watchdog.restart_process("test_process", reason="Test")

            assert not result.success
            assert "max restarts" in result.message.lower()

    @pytest.mark.asyncio
    async def test_restart_cooldown(self):
        """Test cooldown between restarts."""
        from orchestrator.watchdog import Watchdog, ProcessConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            watchdog = Watchdog(
                state_dir=Path(tmpdir),
                check_interval=0.1
            )

            config = ProcessConfig(
                name="test_process",
                command="echo test",
                restart_on_crash=True,
                max_restarts=5,
                restart_cooldown=1.0  # 1 second cooldown
            )
            watchdog.register_process(config)

            # First restart should work
            async def mock_start_process(name, command):
                return {"pid": 12345, "status": "running"}

            watchdog._start_process = mock_start_process

            result1 = await watchdog.restart_process("test_process", reason="Test")
            assert result1.success

            # Immediate second restart should be blocked by cooldown
            result2 = await watchdog.restart_process("test_process", reason="Test")
            assert not result2.success
            assert "cooldown" in result2.message.lower()


class TestWatchdogAlerts:
    """Tests for watchdog alerting."""

    @pytest.mark.asyncio
    async def test_alert_on_restart(self):
        """Test alert generated when process restarts."""
        from orchestrator.watchdog import Watchdog, ProcessConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            alert_dir = Path(tmpdir) / "Alerts"

            watchdog = Watchdog(
                state_dir=Path(tmpdir),
                check_interval=0.1,
                alert_directory=alert_dir
            )

            config = ProcessConfig(
                name="test_process",
                command="echo test",
                restart_on_crash=True,
                max_restarts=5,
                alert_on_restart=True
            )
            watchdog.register_process(config)

            async def mock_start_process(name, command):
                return {"pid": 12345, "status": "running"}

            watchdog._start_process = mock_start_process

            await watchdog.restart_process("test_process", reason="Crash detected")

            # Check alert was created
            assert alert_dir.exists()
            alerts = list(alert_dir.glob("*.md"))
            assert len(alerts) >= 1

            alert_content = alerts[0].read_text()
            assert "test_process" in alert_content
            assert "restart" in alert_content.lower()

    @pytest.mark.asyncio
    async def test_alert_on_max_restarts_reached(self):
        """Test alert when max restarts exceeded."""
        from orchestrator.watchdog import Watchdog, ProcessConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            alert_dir = Path(tmpdir) / "Alerts"

            watchdog = Watchdog(
                state_dir=Path(tmpdir),
                check_interval=0.1,
                alert_directory=alert_dir
            )

            config = ProcessConfig(
                name="critical_process",
                command="echo test",
                restart_on_crash=True,
                max_restarts=3,
                alert_on_max_restarts=True
            )
            watchdog.register_process(config)
            watchdog._processes["critical_process"]["restarts"] = 3

            await watchdog.restart_process("critical_process", reason="Test")

            # Check critical alert was created
            assert alert_dir.exists()
            alerts = list(alert_dir.glob("*critical*.md"))
            assert len(alerts) >= 1


class TestWatchdogState:
    """Tests for watchdog state persistence."""

    def test_save_and_load_state(self):
        """Test state persistence across restarts."""
        from orchestrator.watchdog import Watchdog, ProcessConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)

            # Create watchdog and register process
            watchdog1 = Watchdog(state_dir=state_dir, check_interval=0.1)
            config = ProcessConfig(
                name="persistent_process",
                command="echo test",
                restart_on_crash=True,
                max_restarts=5
            )
            watchdog1.register_process(config)
            watchdog1._processes["persistent_process"]["restarts"] = 2
            watchdog1._processes["persistent_process"]["pid"] = 12345
            watchdog1.save_state()

            # Create new watchdog instance - should load state
            watchdog2 = Watchdog(state_dir=state_dir, check_interval=0.1)
            watchdog2.register_process(config)
            watchdog2.load_state()

            assert watchdog2._processes["persistent_process"]["restarts"] == 2

    def test_state_includes_restart_history(self):
        """Test state includes restart history."""
        from orchestrator.watchdog import Watchdog, ProcessConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)

            watchdog = Watchdog(state_dir=state_dir, check_interval=0.1)
            config = ProcessConfig(
                name="test_process",
                command="echo test",
                restart_on_crash=True,
                max_restarts=5
            )
            watchdog.register_process(config)

            # Record restart events
            watchdog.record_restart_event("test_process", "Crash", success=True)
            watchdog.record_restart_event("test_process", "Another crash", success=True)

            watchdog.save_state()

            # Check state file
            state_file = state_dir / "watchdog_state.json"
            assert state_file.exists()

            state = json.loads(state_file.read_text())
            assert "restart_history" in state
            assert len(state["restart_history"]["test_process"]) == 2


class TestWatchdogHealthCheck:
    """Tests for watchdog health checking."""

    @pytest.mark.asyncio
    async def test_health_check_all_processes(self):
        """Test health check reports all process statuses."""
        from orchestrator.watchdog import Watchdog, ProcessConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            watchdog = Watchdog(
                state_dir=Path(tmpdir),
                check_interval=0.1
            )

            for name in ["process_a", "process_b", "process_c"]:
                config = ProcessConfig(
                    name=name,
                    command=f"echo {name}",
                    restart_on_crash=True,
                    max_restarts=3
                )
                watchdog.register_process(config)
                watchdog._processes[name] = {
                    "pid": 12345,
                    "status": "running" if name != "process_b" else "stopped",
                    "restarts": 0
                }

            health = await watchdog.health_check()

            assert health["process_a"]["status"] == "running"
            assert health["process_b"]["status"] == "stopped"
            assert health["process_c"]["status"] == "running"
            assert "healthy" in health or len(health) == 3

    @pytest.mark.asyncio
    async def test_health_check_returns_restart_counts(self):
        """Test health check includes restart counts."""
        from orchestrator.watchdog import Watchdog, ProcessConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            watchdog = Watchdog(
                state_dir=Path(tmpdir),
                check_interval=0.1
            )

            config = ProcessConfig(
                name="flaky_process",
                command="echo flaky",
                restart_on_crash=True,
                max_restarts=5
            )
            watchdog.register_process(config)
            watchdog._processes["flaky_process"] = {
                "pid": 12345,
                "status": "running",
                "restarts": 3
            }

            health = await watchdog.health_check()

            assert health["flaky_process"]["restarts"] == 3


class TestWatchdogPM2Integration:
    """Tests for PM2 integration."""

    @pytest.mark.asyncio
    async def test_pm2_process_status(self):
        """Test getting process status from PM2."""
        from orchestrator.watchdog import Watchdog, ProcessConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            watchdog = Watchdog(
                state_dir=Path(tmpdir),
                check_interval=0.1,
                use_pm2=True
            )

            # Mock PM2 jlist output
            pm2_output = json.dumps([
                {
                    "name": "file_watcher",
                    "pm_id": 0,
                    "pid": 12345,
                    "pm2_env": {"status": "online"}
                },
                {
                    "name": "orchestrator",
                    "pm_id": 1,
                    "pid": 12346,
                    "pm2_env": {"status": "online"}
                }
            ])

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout=pm2_output
                )

                status = await watchdog.get_pm2_status()

            assert "file_watcher" in status
            assert status["file_watcher"]["status"] == "online"

    @pytest.mark.asyncio
    async def test_pm2_restart_process(self):
        """Test restarting process via PM2."""
        from orchestrator.watchdog import Watchdog

        with tempfile.TemporaryDirectory() as tmpdir:
            watchdog = Watchdog(
                state_dir=Path(tmpdir),
                check_interval=0.1,
                use_pm2=True
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)

                result = await watchdog.pm2_restart("file_watcher")

            assert result.success
            mock_run.assert_called()
            call_args = mock_run.call_args
            assert "pm2" in str(call_args)
            assert "restart" in str(call_args)


class TestWatchdogLoop:
    """Tests for watchdog main loop."""

    @pytest.mark.asyncio
    async def test_watchdog_loop_iteration(self):
        """Test single watchdog loop iteration."""
        from orchestrator.watchdog import Watchdog, ProcessConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            watchdog = Watchdog(
                state_dir=Path(tmpdir),
                check_interval=0.1
            )

            config = ProcessConfig(
                name="test_process",
                command="echo test",
                restart_on_crash=True,
                max_restarts=5
            )
            watchdog.register_process(config)

            check_count = 0
            original_check = watchdog.check_processes

            async def mock_check():
                nonlocal check_count
                check_count += 1
                if check_count >= 2:
                    watchdog._running = False
                return []

            watchdog.check_processes = mock_check
            watchdog._running = True

            await watchdog.run_once()

            assert check_count >= 1

    @pytest.mark.asyncio
    async def test_watchdog_graceful_shutdown(self):
        """Test watchdog handles shutdown gracefully."""
        from orchestrator.watchdog import Watchdog

        with tempfile.TemporaryDirectory() as tmpdir:
            watchdog = Watchdog(
                state_dir=Path(tmpdir),
                check_interval=0.1
            )

            # Start and then stop
            watchdog._running = True

            async def stop_after_delay():
                await asyncio.sleep(0.05)
                await watchdog.stop()

            asyncio.create_task(stop_after_delay())

            # Should complete without hanging
            try:
                await asyncio.wait_for(watchdog.run_once(), timeout=1.0)
            except asyncio.TimeoutError:
                pytest.fail("Watchdog did not shutdown gracefully")

            assert not watchdog._running
