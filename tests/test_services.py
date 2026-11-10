import importlib.util
import io
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from rich.console import Console

spec = importlib.util.spec_from_file_location('manager', Path(__file__).parents[1] / 'manage-services.tui.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class LaunchctlTests(unittest.TestCase):
    def test_boolean_overrides_are_parsed(self):
        names, states = m.parse_launchctl_print_output('disabled services = {\n "example.off" => true\n "example.on" => false\n}')
        self.assertEqual(states, {'example.off': 'disabled', 'example.on': 'enabled'})

    def test_discovery_uses_explicit_domains_without_database_phantoms(self):
        def run(cmd, **kwargs):
            domain = cmd[-1].rstrip('/')
            if cmd[-2] == 'print':
                output = {'system': 'services = {\n 123 0 example.daemon\n}',
                          'gui/502': 'services = {\n 456 0 example.agent\n}',
                          'user/502': 'services = {\n 789 0 example.background\n}'}.get(domain, '')
            elif cmd[-2] == 'print-disabled':
                output = 'disabled services = {\n "example.off" => disabled\n}' if domain == 'gui/502' else ''
            else:
                output = 'PID Status Label\n123 0 example.daemon\n'
            return subprocess.CompletedProcess(cmd, 0, output, '')
        with patch.object(m.subprocess, 'run', side_effect=run), patch.object(m, 'get_uid', return_value=502):
            data = m.get_live_services(Console(file=io.StringIO()))
        services = {name: info for group in data.values() for name, info in group.items()}
        self.assertEqual(set(services), {'example.daemon', 'example.agent', 'example.background', 'example.off'})
        self.assertEqual(services['example.agent']['domain'], 'gui/502')
        self.assertEqual(services['example.background']['domain'], 'user/502')
        self.assertEqual(services['example.agent']['status'], 'running')
        self.assertEqual(services['example.off']['status'], 'disabled')

    def test_disable_precedes_bootout_and_verifies_exact_target(self):
        calls = []
        def run(cmd, **kwargs):
            calls.append(cmd)
            if 'print-disabled' in cmd:
                return subprocess.CompletedProcess(cmd, 0, '"example.agent" => disabled', '')
            if 'print' in cmd:
                return subprocess.CompletedProcess(cmd, 113, '', 'Could not find service "example.agent" in domain for user gui: 502')
            if 'list' in cmd:
                return subprocess.CompletedProcess(cmd, 0, '123 0 example.agent.helper', '')
            return subprocess.CompletedProcess(cmd, 0, '', '')
        with patch.object(m.subprocess, 'run', side_effect=run):
            success, error = m.bootout_and_disable('example.agent', 502)
        self.assertTrue(success, error)
        actions = [cmd[-2] for cmd in calls if cmd[-2] in ('disable', 'bootout')]
        self.assertEqual(actions, ['disable', 'bootout'])
        self.assertIn(['launchctl', 'print', 'gui/502/example.agent'], calls)

    def test_failed_verification_cannot_report_success(self):
        def run(cmd, **kwargs):
            if 'print-disabled' in cmd:
                return subprocess.CompletedProcess(cmd, 0, '"example.agent" => disabled', '')
            if 'print' in cmd or 'list' in cmd:
                return subprocess.CompletedProcess(cmd, 1, '', 'Operation not permitted')
            return subprocess.CompletedProcess(cmd, 0, '', '')
        with patch.object(m.subprocess, 'run', side_effect=run):
            success, error = m.bootout_and_disable('example.agent', 502)
        self.assertFalse(success)
        self.assertIn('Operation not permitted', error)

    def test_running_but_disabled_service_can_be_reenabled(self):
        info = m.get_service_details('example.agent', 'agent', {'example.agent': 'disabled'}, {'example.agent': '123'})
        app = m.ServiceManagerTUI({'Test': {'example.agent': info}})
        app.view_mode = 'services'
        app.handle_input(' ')
        self.assertEqual(info['pending_status'], 'enabled')

    def test_apply_failure_keeps_observed_state_and_shows_error(self):
        info = {'type': 'agent', 'domain': 'user/502', 'label': 'example.background',
                'status': 'running', 'pending_status': 'disabled'}
        app = m.ServiceManagerTUI({'Test': {'example.background': info}})
        app.console = Console(file=io.StringIO())
        live = Mock()
        with patch.object(app, 'read_key', side_effect=['y', 'x']), \
             patch.object(m, 'set_service_enabled', return_value=(False, 'Operation not permitted')), \
             patch.object(m, 'get_live_services', return_value={'Test': {'example.background': {'status': 'running'}}}):
            app.confirm_and_apply(live)
        self.assertEqual(info['status'], 'running')
        self.assertIn('Operation not permitted', app.console.file.getvalue())
        self.assertEqual(app.services_data['Test']['example.background']['status'], 'running')


if __name__ == '__main__':
    unittest.main()
