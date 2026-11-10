"""Read-only launchd inventory acceptance check; never changes service state."""
import importlib.util
import io
import platform
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('manager', root / 'manage-services.tui.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def main():
    captured = {}
    original_run = subprocess.run

    def record(cmd, **kwargs):
        # Guard this acceptance check against accidentally mutating launchd.
        assert cmd[0] == 'launchctl' and cmd[1] in ('print', 'print-disabled'), cmd
        result = original_run(cmd, **kwargs)
        captured[(cmd[1], cmd[2])] = result
        return result

    log = io.StringIO()
    with patch.object(m.subprocess, 'run', side_effect=record):
        data = m.get_live_services(Console(file=log))
    assert not log.getvalue(), log.getvalue()
    all_info = [info for group in data.values() for info in group.values()]
    report = [f'Read-only inventory verification — {datetime.now(timezone.utc).isoformat()}',
              f'macOS {platform.mac_ver()[0]}', 'No enable, disable, bootstrap, bootout, or kickstart commands executed.']
    for domain in ('system', f'gui/{m.get_uid()}', f'user/{m.get_uid()}'):
        result = captured[('print', domain)]
        assert result.returncode == 0, result.stderr
        # Independently compare loaded entries with launchd's own service count.
        count = int(re.search(r'^\s*service count = (\d+)', result.stdout, re.MULTILINE).group(1))
        infos = [i for i in all_info if i['domain'] == domain]
        loaded = [i for i in infos if i['loaded']]
        assert len(loaded) == count, (domain, len(loaded), count)
        overrides = dict(re.findall(r'"([^"\n]+)"\s*=>\s*(enabled|disabled)', captured[('print-disabled', domain)].stdout))
        by_label = {i['label']: i for i in infos}
        for label, state in overrides.items():
            assert by_label[label]['enabled_status'] == state, (domain, label)
        for info in loaded:
            assert (info['status'] == 'running') == bool(info['pid']), (domain, info['label'])
        report.append(f'{domain}: {count} loaded jobs match launchd count; {len(overrides)} overrides match; {len(infos) - count} override-only entries.')
    report.append(f'{len(all_info)} domain-specific entries across {len(data)} categories.')
    report.append('Observed list states: ' + ', '.join(f'{key}={value}' for key, value in sorted(Counter(i['status'] for i in all_info).items())))
    report.append('All running states have a positive launchd PID; saved override values match launchctl.')

    artifacts = root / 'artifacts'
    for label, filename, width, height, paged in [
        ('com.apple.triald', 'service-details-trial', 160, 52, False),
        ('com.apple.Finder', 'service-details-running', 160, 52, False),
        ('com.apple.triald', 'service-details-80x24', 80, 24, True),
        ('com.apple.triald', 'service-details-110x30', 110, 30, True),
    ]:
        category = next(cat for cat, group in data.items() if any(i['label'] == label for i in group.values()))
        key = next(key for key, info in data[category].items() if info['label'] == label)
        app = m.ServiceManagerTUI(data)
        screen = Console(file=io.StringIO(), record=True, width=width, height=height, force_terminal=True, color_system='truecolor')
        app.console = screen
        app.view_mode = 'services'
        app.active_category_index = app.categories.index(category)
        app.active_service_index = app.get_current_services().index(key)
        app._adjust_viewport('service')
        if paged:
            app.handle_input('page_down')
            app.handle_input('page_down')
            app.handle_input('page_down')
        screen.print(app.draw_layout())
        if paged:
            assert 'Impact of Disabling' in screen.export_text(clear=False)

        screen.save_svg(str(artifacts / f'{filename}.svg'), title='macOS Service Manager — live read-only inventory', clear=False)
        screen.save_text(str(artifacts / f'{filename}.txt'), clear=False)
        report.append(f'Rendered actual TUI layout for {label} from this live inventory: {filename}.svg')
    text = '\n'.join(report) + '\n'
    (artifacts / 'service-inventory-check.txt').write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
