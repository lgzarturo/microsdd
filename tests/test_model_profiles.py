"""Perfiles de modelo: config.json como fuente de verdad (MicroSDD 1.4.0)."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SDD_PATH = REPO / '.microharness' / 'sdd.py'
INSTALLER_PATH = REPO / 'src' / 'microsdd' / 'installer.py'

spec = importlib.util.spec_from_file_location('sdd_model_profiles', SDD_PATH)
sdd = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(sdd)

ispec = importlib.util.spec_from_file_location('installer_model_profiles', INSTALLER_PATH)
installer = importlib.util.module_from_spec(ispec)
assert ispec.loader is not None
ispec.loader.exec_module(installer)

FAKE_UV = ['uv']


def write_harness(root: Path, model: str = 'claude-opus-5-5', effort: str = 'medium') -> None:
    settings = {
        'agent': 'lider',
        'model': model,
        'effortLevel': effort,
        'hooks': {'PreToolUse': []},
    }
    (root / '.claude').mkdir(parents=True, exist_ok=True)
    (root / '.claude' / 'settings.json').write_text(
        json.dumps(settings, indent=2) + '\n', encoding='utf-8')
    agents = root / '.claude' / 'agents'
    agents.mkdir(parents=True, exist_ok=True)
    for name in sdd.AGENT_NAMES:
        (agents / f'{name}.md').write_text(
            f'---\nname: {name}\ndescription: test\nmodel: {model}\neffort: {effort}\n---\nBody.\n',
            encoding='utf-8')


class ModelProfilesConfigTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.old_root, self.old_memory = sdd.ROOT, sdd.MEMORY
        sdd.ROOT = Path(self.temporary.name)
        sdd.MEMORY = sdd.ROOT / '.microharness' / 'memory.json'
        self.addCleanup(self._restore)
        sdd.MEMORY.parent.mkdir(parents=True)
        sdd.dump(sdd.MEMORY, json.loads(json.dumps(sdd.EMPTY_MEMORY)))

    def _restore(self):
        sdd.ROOT, sdd.MEMORY = self.old_root, self.old_memory

    def _write_config(self, data: dict | str) -> None:
        text = data if isinstance(data, str) else json.dumps(data)
        (sdd.MEMORY.parent / 'config.json').write_text(text, encoding='utf-8')

    def test_default_profile_is_probado(self):
        cfg = sdd.config()
        self.assertEqual(cfg['model'], 'claude-opus-5-5')
        self.assertEqual(cfg['effort'], 'medium')
        self.assertEqual(cfg['profile'], 'opus-5-5-medium')
        self.assertEqual(cfg['profile_status'], 'probado')
        self.assertEqual(cfg['profiles']['opus-5-5-medium']['status'], 'probado')

    def test_custom_model_is_experimental(self):
        self._write_config({'model': 'claude-prueba-1', 'effort': 'high'})
        cfg = sdd.config()
        self.assertEqual(cfg['profile_status'], 'experimental')
        with contextlib.redirect_stdout(io.StringIO()):
            sdd.new('tarea-exp')
        spec_data = sdd.load(sdd.ROOT / 'spec' / 'tarea-exp' / 'spec.json')
        self.assertEqual(spec_data['model'], 'claude-prueba-1')
        self.assertEqual(spec_data['effort'], 'high')
        self.assertEqual(spec_data.get('profile_status'), 'experimental')

    def test_probado_profile_omits_profile_status_in_new(self):
        with contextlib.redirect_stdout(io.StringIO()):
            sdd.new('tarea-ok')
        spec_data = sdd.load(sdd.ROOT / 'spec' / 'tarea-ok' / 'spec.json')
        self.assertNotIn('profile_status', spec_data)

    def test_user_profile_experimental(self):
        self._write_config({
            'profile': 'custom',
            'profiles': {
                'custom': {
                    'status': 'experimental',
                    'model': 'claude-prueba-1',
                    'effort': 'low',
                }
            },
        })
        cfg = sdd.config()
        self.assertEqual(cfg['model'], 'claude-prueba-1')
        self.assertEqual(cfg['effort'], 'low')
        self.assertEqual(cfg['profile_status'], 'experimental')

    def test_invalid_profile_status_rejected(self):
        self._write_config({
            'profiles': {
                'x': {'status': 'beta', 'model': 'm', 'effort': 'medium'},
            },
        })
        with self.assertRaises(ValueError) as ctx:
            sdd.config()
        self.assertIn('status', str(ctx.exception))

    def test_alignment_reports_settings_and_agents(self):
        write_harness(sdd.ROOT, model='claude-opus-5-5', effort='medium')
        self._write_config({'model': 'claude-prueba-1', 'effort': 'high'})
        errors = sdd.runtime_alignment_errors()
        joined = '\n'.join(errors)
        self.assertIn('.claude/settings.json', joined)
        self.assertIn('claude-prueba-1', joined)
        self.assertIn('lider.md', joined)
        self.assertTrue(any('effortLevel' in e for e in errors))

    def test_alignment_ok_when_matching(self):
        write_harness(sdd.ROOT)
        self.assertEqual(sdd.runtime_alignment_errors(), [])

    def test_alignment_skipped_without_harness(self):
        self.assertEqual(sdd.runtime_alignment_errors(), [])

    def test_frontmatter_roundtrip(self):
        text = '---\nname: lider\nmodel: old\neffort: low\n---\nBody\n'
        out = sdd.apply_frontmatter_fields(text, {'model': 'claude-opus-5-5', 'effort': 'medium'})
        fields = sdd.parse_frontmatter(out)
        self.assertEqual(fields['model'], 'claude-opus-5-5')
        self.assertEqual(fields['effort'], 'medium')
        self.assertEqual(fields['name'], 'lider')
        self.assertIn('Body', out)


class InstallerRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / 'home'
        self.home.mkdir()
        self.repo = Path(self.temporary.name) / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q'], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 't@e.com'], cwd=self.repo, check=True,
                       capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'T'], cwd=self.repo, check=True,
                       capture_output=True)

    def test_target_runtime_from_config(self):
        mh = self.repo / '.microharness'
        mh.mkdir(parents=True)
        (mh / 'config.json').write_text(
            json.dumps({'model': 'claude-prueba-1', 'effort': 'high'}), encoding='utf-8')
        self.assertEqual(installer.target_runtime(self.repo), ('claude-prueba-1', 'high'))

    def test_install_applies_config_to_settings_and_agents(self):
        mh = self.repo / '.microharness'
        mh.mkdir(parents=True)
        (mh / 'config.json').write_text(
            json.dumps({'model': 'claude-prueba-1', 'effort': 'high'}), encoding='utf-8')
        with mock.patch.object(installer, 'check_uv', return_value=None), \
                mock.patch('sys.stdin', mock.Mock(isatty=lambda: True)), \
                mock.patch.dict('os.environ', {}, clear=False):
            # stdin TTY not required for install itself
            code = installer.install(REPO, self.repo, uv=FAKE_UV, home=self.home, force=True)
        self.assertEqual(code, 0, 'install should succeed')
        settings = json.loads((self.repo / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        self.assertEqual(settings['model'], 'claude-prueba-1')
        self.assertEqual(settings['effortLevel'], 'high')
        for name in ('lider', 'autor', 'implementador', 'revisor'):
            text = (self.repo / '.claude' / 'agents' / f'{name}.md').read_text(encoding='utf-8')
            fields = sdd.parse_frontmatter(text)
            self.assertEqual(fields.get('model'), 'claude-prueba-1', name)
            self.assertEqual(fields.get('effort'), 'high', name)

    def test_install_defaults_without_config(self):
        with mock.patch.object(installer, 'check_uv', return_value=None):
            code = installer.install(REPO, self.repo, uv=FAKE_UV, home=self.home, force=True)
        self.assertEqual(code, 0)
        settings = json.loads((self.repo / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        self.assertEqual(settings['model'], 'claude-opus-5-5')
        self.assertEqual(settings['effortLevel'], 'medium')


class VersionBumpTests(unittest.TestCase):
    def test_version_is_1_4_0(self):
        self.assertEqual(sdd.__version__, '1.4.0')
        pyproject = (REPO / 'pyproject.toml').read_text(encoding='utf-8')
        self.assertIn('version = "1.4.0"', pyproject)


if __name__ == '__main__':
    unittest.main()
