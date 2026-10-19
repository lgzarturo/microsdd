"""Telemetría opcional m1: esquema, agregación cruzada con CodeConductor y emit no-op."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / 'schemas' / 'harness-telemetry.v1.json'
EXPECTED_SCHEMA_SHA256 = (
    '3adfba482e42fb956d9486bf5e28ffb5818643c71372b0ce11c9be0e9fe44d5a'
)
METRICS_PATH = ROOT / '.microharness' / 'metrics.py'
SDD_PATH = ROOT / '.microharness' / 'sdd.py'
INSTALLER_PATH = ROOT / 'src' / 'microsdd' / 'installer.py'


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def cross_events():
    """Mismos eventos que aggregate-pricing.test.ts (sums model.call…)."""
    return [
        {
            'schema': 'harness-telemetry/v1',
            'ts': '2026-10-18T22:30:00-05:00',
            'harness': {'name': 'microsdd'},
            'runId': 'r1',
            'event': 'model.call',
            'taskId': 'T1',
            'agent': {'role': 'implementer', 'agentId': 'a1'},
            'usage': {
                'input': 100, 'output': 20, 'cacheRead': 50, 'cacheWrite': 10,
                'reasoning': None, 'calls': None, 'apiRetries': None,
            },
            'cost': {'usd': 0.01, 'basis': 'host-estimate', 'pricingVersion': None, 'isRealSpend': False},
        },
        {
            'schema': 'harness-telemetry/v1',
            'ts': '2026-10-18T22:30:01-05:00',
            'harness': {'name': 'microsdd'},
            'runId': 'r1',
            'event': 'model.call',
            'taskId': 'T1',
            'agent': {'role': 'implementer', 'agentId': 'a1'},
            'usage': {
                'input': 40, 'output': 10, 'cacheRead': None, 'cacheWrite': None,
                'reasoning': None, 'calls': None, 'apiRetries': None,
            },
            'cost': {'usd': 0.002, 'basis': 'host-estimate', 'pricingVersion': None, 'isRealSpend': False},
        },
        {
            'schema': 'harness-telemetry/v1',
            'ts': '2026-10-18T22:30:02-05:00',
            'harness': {'name': 'microsdd'},
            'runId': 'r1',
            'event': 'agent.end',
            'taskId': 'T1',
            'agent': {'role': 'implementer', 'agentId': 'a1'},
        },
        {
            'schema': 'harness-telemetry/v1',
            'ts': '2026-10-18T22:30:03-05:00',
            'harness': {'name': 'microsdd'},
            'runId': 'r1',
            'event': 'retry',
            'taskId': 'T1',
            'loop': {'iteration': 1, 'retryReason': 'fail', 'maxIterations': 3},
        },
        {
            'schema': 'harness-telemetry/v1',
            'ts': '2026-10-18T22:30:04-05:00',
            'harness': {'name': 'microsdd'},
            'runId': 'r1',
            'event': 'iteration',
            'taskId': 'T1',
            'loop': {'iteration': 2, 'retryReason': None, 'maxIterations': 3},
        },
        {
            'schema': 'harness-telemetry/v1',
            'ts': '2026-10-18T22:30:05-05:00',
            'harness': {'name': 'microsdd'},
            'runId': 'r1',
            'event': 'verification',
            'taskId': 'T1',
            'verification': {'gate': 'tests', 'passed': True, 'durationMs': 100},
        },
        {
            'schema': 'harness-telemetry/v1',
            'ts': '2026-10-18T22:30:06-05:00',
            'harness': {'name': 'microsdd'},
            'runId': 'r1',
            'event': 'task.end',
            'taskId': 'T1',
            'usage': {
                'input': 140, 'output': 30, 'cacheRead': 50, 'cacheWrite': 10,
                'reasoning': None, 'calls': None, 'apiRetries': None,
            },
            'cost': {'usd': 0.012, 'basis': 'host-estimate', 'pricingVersion': None, 'isRealSpend': False},
            'loop': {'iteration': 2, 'retryReason': None, 'maxIterations': 3},
        },
        {
            'schema': 'harness-telemetry/v1',
            'ts': '2026-10-18T22:30:07-05:00',
            'harness': {'name': 'microsdd'},
            'runId': 'r1',
            'event': 'run.end',
            'usage': {
                'input': 140, 'output': 30, 'cacheRead': 50, 'cacheWrite': 10,
                'reasoning': None, 'calls': None, 'apiRetries': None,
            },
            'cost': {'usd': 0.012, 'basis': 'host-estimate', 'pricingVersion': None, 'isRealSpend': False},
            'durationMs': 5000,
        },
    ]


def _state_env(state: Path) -> dict[str, str]:
    """Home de estado fuera del repo: XDG en Unix, LOCALAPPDATA en Windows (§4)."""
    if os.name == 'nt':
        return {'LOCALAPPDATA': str(state)}
    return {'XDG_STATE_HOME': str(state)}


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


class SchemaHashTests(unittest.TestCase):
    def test_schema_sha256_matches_codeconductor_m1(self):
        # Bytes reales del checkout; `.gitattributes` fuerza eol=lf (falla si deja de ser LF).
        raw = SCHEMA_PATH.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual(digest, EXPECTED_SCHEMA_SHA256)
        schema = json.loads(raw)
        self.assertEqual(schema['$schema'], 'https://json-schema.org/draft/2020-12/schema')
        self.assertEqual(schema['$id'], 'harness-telemetry/v1')
        self.assertEqual(schema['required'], ['schema', 'ts', 'harness', 'runId', 'event'])


@unittest.skipUnless(METRICS_PATH.is_file(), 'metrics.py no presente')
class AggregateCrossTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module('microsdd_metrics_under_test', METRICS_PATH)

    def test_metrics_py_line_budget(self):
        # Presupuesto §4: ≤ 400 líneas (equivalente a wc -l).
        text = METRICS_PATH.read_text(encoding='utf-8')
        self.assertLessEqual(text.count('\n'), 400)

    def test_cross_aggregate_matches_codeconductor_fixture(self):
        events = cross_events()
        specialists = self.m.aggregate_by_specialist(events)
        self.assertEqual(len(specialists), 1)
        self.assertEqual(specialists[0]['role'], 'implementer')
        self.assertEqual(specialists[0]['usage']['input'], 140)
        self.assertEqual(specialists[0]['usage']['cacheRead'], 50)
        self.assertEqual(specialists[0]['modelCalls'], 2)
        self.assertEqual(specialists[0]['agentEnds'], 1)

        tasks = self.m.aggregate_by_task(events)
        self.assertEqual(tasks[0]['retries'], 1)
        self.assertEqual(tasks[0]['iterations'], 2)
        self.assertEqual(tasks[0]['verifications']['tests']['passed'], 1)
        self.assertEqual(tasks[0]['usage']['input'], 140)

        runs = self.m.aggregate_by_run(events)
        self.assertEqual(runs[0]['costUsd'], 0.012)
        self.assertEqual(runs[0]['durationMs'], 5000)
        self.assertEqual(self.m.total_tokens(runs[0]['usage']), 140 + 50 + 10 + 30)

    def test_null_not_zero_when_folding_missing_usage(self):
        events = [{
            'schema': 'harness-telemetry/v1',
            'ts': '2026-10-18T22:30:00-05:00',
            'harness': {'name': 'microsdd'},
            'runId': 'r2',
            'event': 'agent.end',
            'taskId': 'T2',
            'agent': {'role': 'revisor', 'agentId': None},
        }]
        specialists = self.m.aggregate_by_specialist(events)
        self.assertIsNone(specialists[0]['usage']['input'])
        self.assertIsNone(specialists[0]['costUsd'])

    def test_emit_writes_outside_repo_by_default(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        state = Path(tmp.name) / 'state'
        with mock.patch.dict(os.environ, _state_env(state), clear=False):
            self.m.purge()
            self.m.emit('task.start', taskId='demo', runId='r-demo')
            path = self.m.runs_path()
            self.assertTrue(_under(path, state), f'{path} no está bajo {state}')
            self.assertTrue(path.is_file())
            line = json.loads(path.read_text(encoding='utf-8').splitlines()[0])
            self.assertEqual(line['schema'], 'harness-telemetry/v1')
            self.assertEqual(line['event'], 'task.start')
            self.m.purge()

    def test_hook_subagent_stop_emits_agent_end(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        state = Path(tmp.name) / 'state'
        with mock.patch.dict(os.environ, _state_env(state), clear=False):
            self.m.purge()
            self.m.handle_hook('SubagentStop', {
                'session_id': 'sess-1',
                'agent_type': 'implementador',
                'agent_id': 'ag-9',
            })
            lines = [json.loads(x) for x in self.m.runs_path().read_text(encoding='utf-8').splitlines() if x]
            self.assertEqual(lines[-1]['event'], 'agent.end')
            self.assertEqual(lines[-1]['agent']['role'], 'implementador')
            self.m.purge()


class EmitNoopWithoutModuleTests(unittest.TestCase):
    def test_sdd_emit_noop_and_config_metrics_without_module(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        mh = root / '.microharness'
        mh.mkdir()
        shutil.copyfile(SDD_PATH, mh / 'sdd.py')
        # Sin metrics.py junto a sdd → import falla y emit es no-op.
        (mh / 'memory.json').write_text(json.dumps({
            'schema_version': 1,
            'project': {'observations': [], 'decisions': [], 'progress': [], 'discoveries': []},
            'tasks': {},
        }), encoding='utf-8')
        (mh / 'config.json').write_text(json.dumps({
            'metrics': {'local_dir': True, 'privacy': 'strict'},
        }), encoding='utf-8')
        (root / 'docs').mkdir()
        for name in ('AGENT.md', 'arquitectura.md', 'convenciones.md', 'especificaciones.md'):
            (root / 'docs' / name).write_text('Pendiente de inspección.\n', encoding='utf-8')
        (root / 'spec').mkdir()
        (root / 'spec' / '.gitkeep').write_bytes(b'')
        sdd = load_module('sdd_cfg_metrics', mh / 'sdd.py')
        self.assertIsNone(sdd._metrics_mod)
        self.assertIsNone(sdd.emit('task.start', taskId='t'))
        cfg = sdd.config()
        self.assertEqual(cfg['metrics']['local_dir'], True)
        self.assertEqual(cfg['metrics']['privacy'], 'strict')


class InstallerMetricsFlagTests(unittest.TestCase):
    def setUp(self):
        self.installer = load_module('microsdd_installer_metrics', INSTALLER_PATH)
        temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.home = self.base / 'home'
        self.home.mkdir()
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        import subprocess
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)

    def test_without_flag_skips_metrics_and_hooks(self):
        code = self.installer.install(ROOT, self.repo, uv=[sys.executable, '-c', 'print("uv")'],
                                      home=self.home, with_metrics=False)
        self.assertEqual(code, 0)
        self.assertFalse((self.repo / '.microharness' / 'metrics.py').exists())
        self.assertFalse((self.repo / '.microharness' / 'pricing.json').exists())
        settings = json.loads((self.repo / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        self.assertNotIn('SubagentStop', settings.get('hooks', {}))
        self.assertNotIn('SessionEnd', settings.get('hooks', {}))

    @unittest.skipUnless(METRICS_PATH.is_file() and (ROOT / '.microharness' / 'pricing.json').is_file(),
                         'payload de métricas ausente')
    def test_with_metrics_installs_module_hooks_pricing_gitignore(self):
        code = self.installer.install(ROOT, self.repo, uv=[sys.executable, '-c', 'print("uv")'],
                                      home=self.home, with_metrics=True)
        self.assertEqual(code, 0)
        self.assertTrue((self.repo / '.microharness' / 'metrics.py').is_file())
        self.assertTrue((self.repo / '.microharness' / 'pricing.json').is_file())
        pricing = json.loads((self.repo / '.microharness' / 'pricing.json').read_text(encoding='utf-8'))
        self.assertEqual(pricing['version'], 'pricing/v1')
        self.assertTrue(any(e.get('input') is not None for e in pricing['entries']))
        settings = json.loads((self.repo / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        for event in ('SubagentStop', 'SessionEnd'):
            self.assertIn(event, settings['hooks'])
            hook = settings['hooks'][event][0]['hooks'][0]
            self.assertTrue(hook.get('async'))
            self.assertIn('metrics.py', ' '.join(hook.get('args') or []))
        ignore = (self.repo / '.gitignore').read_text(encoding='utf-8')
        self.assertIn('.microharness/metrics/', ignore)


if __name__ == '__main__':
    unittest.main()
