import importlib.util
import io
import plistlib
import tempfile
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


class AccuracyTests(unittest.TestCase):
    def test_cancelled_toggle_retains_running_icon(self):
        info = m.get_service_details('example.running', 'agent', {'example.running': 'enabled'}, {'example.running': '123'})
        app = m.ServiceManagerTUI({'Test': {'example.running': info}})
        app.view_mode = 'services'
        app.handle_input(' ')
        app.handle_input(' ')
        output = io.StringIO()
        Console(file=output, width=90).print(app.draw_service_list())
        self.assertIn('🟢', output.getvalue())
        self.assertNotIn('🟡', output.getvalue())

    def test_scrolled_selection_remains_visible_inside_panel_borders(self):
        entries = {f'example.{i:03}': {'status': 'loaded'} for i in range(80)}
        app = m.ServiceManagerTUI({'Test': entries})
        output = io.StringIO()
        app.console = Console(file=output, width=110, height=30)
        app.view_mode = 'services'
        app.active_service_index = 79
        app._adjust_viewport('service')
        # Render only the list at the height available after outer/header/footer.
        app.console.print(app.draw_service_list(), height=22)
        self.assertIn('example.079', output.getvalue())

    def test_parser_ignores_non_service_tables_and_preserves_full_labels(self):
        output = """gui/502 = {
 services = {
  123 - application.org.example.Editor.42
  0 0 example:worker
 }
 endpoints = {
  555 0 fake.endpoint
 }
 disabled services = {
  "example.off" => true
 }
}"""
        names, states = m.parse_launchctl_print_output(output)
        self.assertEqual(names, {'application.org.example.Editor.42', 'example:worker', 'example.off'})
        self.assertEqual(states, {'example.off': 'disabled'})

    def test_idle_loaded_job_is_not_reported_as_running_or_enabled(self):
        info = m.get_service_details('example.idle', 'agent', {}, {}, loaded=True)
        self.assertEqual(info['status'], 'loaded')

    def test_definition_disabled_default_and_override_precedence(self):
        info = m.get_service_details('example.job', 'agent', {}, {}, default_disabled=True)
        self.assertEqual(info['enabled_status'], 'disabled')
        info = m.get_service_details('example.job', 'agent', {'example.job': 'enabled'}, {}, default_disabled=True)
        self.assertEqual(info['enabled_status'], 'enabled')

    def test_unreadable_overrides_do_not_invent_enabled_state(self):
        info = m.get_service_details('example.job', 'agent', {}, {}, overrides_known=False)
        self.assertEqual(info['enabled_status'], 'unknown')

    def test_override_without_loaded_job_is_identified(self):
        info = m.get_service_details('example.old', 'agent', {'example.old': 'enabled'}, {}, loaded=False)
        self.assertEqual(info['status'], 'not loaded')
        self.assertFalse(info['loaded'])

    def test_application_job_is_not_assigned_to_apple_from_embedded_substring(self):
        self.assertEqual(m.categorize_service('org.example.com.apple.helper'), '🧩 Third-Party')
        self.assertEqual(m.categorize_service('application.com.apple.Unknown.42'), '❓ Undocumented')

    def test_definitions_use_label_not_filename_and_reject_invalid_plists(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'arbitrary.plist').write_bytes(plistlib.dumps({'Label': 'example.real', 'Disabled': True, 'Program': '/bin/true'}))
            (root / 'bad.plist').write_text('broken')
            (root / 'malformed.plist').write_text('<?xml version=broken?><plist>')
            definitions = m.read_service_definitions([root])
        self.assertEqual(set(definitions), {'example.real'})
        self.assertTrue(definitions['example.real']['default_disabled'])
        self.assertEqual(definitions['example.real']['program'], '/bin/true')

    def test_details_explain_override_only_and_unverified_metadata(self):
        info = m.get_service_details('com.apple.triald', 'agent', {'com.apple.triald': 'disabled'}, {}, loaded=False)
        info.update(domain='gui/502', label='com.apple.triald')
        app = m.ServiceManagerTUI({'Test': {'com.apple.triald': info}})
        app.view_mode = 'services'
        output = io.StringIO()
        Console(file=output, width=110).print(app.draw_details_view())
        rendered = output.getvalue()
        self.assertIn('gui/502', rendered)
        self.assertIn('Override only', rendered)
        self.assertIn('Source:', rendered)
        self.assertNotIn('trial periods', rendered)


if __name__ == '__main__':
    unittest.main()
