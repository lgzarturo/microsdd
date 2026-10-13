"""Pruebas de la guardia fail-closed para agentes no reconocidos (spec hook-fail-closed)."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / '.claude' / 'hooks' / 'pretool.py'
GUARDED = ('Write', 'Edit', 'MultiEdit', 'NotebookEdit', 'Bash', 'PowerShell')
MISSING = object()
UNKNOWN_AGENTS = (MISSING, '', None, 'general-purpose', 'Explore', 'Lider', ' lider')
HINT = 'claude --agent lider'


def load_hook():
    spec = importlib.util.spec_from_file_location('micro_hook_fail_closed', HOOK_PATH)
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    return hook


def make_event(agent, tool, cwd):
    if tool in ('Write', 'Edit', 'MultiEdit'):
        inputs = {'file_path': str(Path(cwd) / 'src' / 'modulo.py')}
    elif tool == 'NotebookEdit':
        inputs = {'notebook_path': str(Path(cwd) / 'cuaderno.ipynb')}
    elif tool in ('Bash', 'PowerShell'):
        inputs = {'command': 'git status'}
    else:
        inputs = {}
    event = {'cwd': str(cwd), 'tool_input': inputs}
    if tool is not None:
        event['tool_name'] = tool
    if agent is not MISSING:
        event['agent_type'] = agent
    return event


class HookFailClosedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = load_hook()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = Path(self.tmp.name).resolve()

    def test_unknown_agent_denied_on_guarded_tools(self):
        # AC-01: toda herramienta vigilada se deniega con la indicación de lanzar el líder.
        for agent in UNKNOWN_AGENTS:
            for tool in GUARDED:
                label = 'ausente' if agent is MISSING else repr(agent)
                with self.subTest(agent_type=label, tool=tool):
                    reason = self.hook.run(make_event(agent, tool, self.cwd))
                    self.assertIsInstance(reason, str)
                    self.assertIn(HINT, reason)

    def test_unknown_agent_allowed_on_other_tools(self):
        # AC-02: herramientas fuera del matcher (o sin tool_name) siguen permitidas.
        for agent in (MISSING, 'general-purpose'):
            for tool in ('Read', 'Grep', 'Glob', 'WebFetch', None):
                label = 'ausente' if agent is MISSING else repr(agent)
                with self.subTest(agent_type=label, tool=tool):
                    self.assertIsNone(self.hook.run(make_event(agent, tool, self.cwd)))

    def test_known_roles_unchanged(self):
        # AC-03: los cuatro roles conservan su comportamiento.
        for agent in ('lider', 'autor', 'implementador'):
            with self.subTest(agent_type=agent):
                self.assertIsNone(self.hook.run(make_event(agent, 'Bash', self.cwd)))
        reason = self.hook.run(make_event('revisor', 'Edit', self.cwd))
        self.assertIsNotNone(reason)
        self.assertIn('solo lectura', reason)
        self.assertNotIn(HINT, reason)


class HookFailClosedScriptTests(unittest.TestCase):
    def run_hook(self, event):
        return subprocess.run([sys.executable, str(HOOK_PATH)], input=json.dumps(event),
                              capture_output=True, text=True, encoding='utf-8', timeout=30)

    def test_script_denies_event_without_agent(self):
        # AC-04: JSON deny con el motivo y código 0.
        result = self.run_hook({'tool_name': 'Write', 'tool_input': {'file_path': 'x'}})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip(), 'stdout vacío: la guardia permitió el evento')
        output = json.loads(result.stdout)['hookSpecificOutput']
        self.assertEqual(output['hookEventName'], 'PreToolUse')
        self.assertEqual(output['permissionDecision'], 'deny')
        self.assertIn(HINT, output['permissionDecisionReason'])

    def test_script_allows_lider_bash(self):
        # AC-04: el líder con un comando inocuo no recibe salida.
        result = self.run_hook({'agent_type': 'lider', 'tool_name': 'Bash',
                                'tool_input': {'command': 'git status'}})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
