"""Opt-in macOS smoke check: only creates and changes its own disposable agent."""
import importlib.util
import os
import plistlib
import subprocess
import tempfile
from pathlib import Path
from rich.console import Console
from rich.table import Table

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('manager', root / 'manage-services.tui.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
uid = os.getuid()
domain = f'gui/{uid}'
label = 'dev.codex.macos-service-manager.smoke-test'
target = f'{domain}/{label}'
console = Console(record=True, width=100)
table = Table(title='Actual macOS launchctl smoke check')
table.add_column('Step')
table.add_column('Observed result')
def run(*args):
    return subprocess.run(['launchctl', *args], capture_output=True, text=True)
with tempfile.TemporaryDirectory(prefix='service-manager-') as folder:
    path = Path(folder) / f'{label}.plist'
    path.write_bytes(plistlib.dumps({'Label': label, 'ProgramArguments': ['/bin/sleep', '300'], 'RunAtLoad': True}))
    try:
        assert run('enable', target).returncode == 0
        started = run('bootstrap', domain, str(path))
        assert started.returncode == 0, started.stderr
        loaded = run('print', target)
        assert loaded.returncode == 0, loaded.stderr
        table.add_row('Before', 'Disposable agent loaded in ' + domain)
        success, error = m.set_service_enabled(label, domain, False)
        assert success, error
        unloaded = run('print', target)
        assert unloaded.returncode == 113, (unloaded.returncode, unloaded.stderr)
        table.add_row('Disable and stop', 'Verified disabled override; exact target absent (exit 113)')
        success, error = m.set_service_enabled(label, domain, True)
        assert success, error
        table.add_row('Enable', 'Verified enabled override')
        restarted = run('bootstrap', domain, str(path))
        assert restarted.returncode == 0, restarted.stderr
        table.add_row('Reload', 'Agent can be loaded again after enabling')
    finally:
        run('bootout', target)
        run('enable', target)
        table.add_row('Cleanup', 'Temporary job unloaded and plist removed; override left enabled')
console.print(table)
output = root / 'artifacts'
output.mkdir(exist_ok=True)
console.save_svg(str(output / 'launchctl-smoke-check.svg'), clear=False)
console.save_text(str(output / 'launchctl-smoke-check.txt'))
