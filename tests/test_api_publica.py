import importlib.util
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
DOC = SOURCE / 'assets' / 'proceso-versionado.md'
SDD = SOURCE / '.microharness' / 'sdd.py'
INSTALLER = SOURCE / 'src' / 'microsdd' / 'installer.py'

spec = importlib.util.spec_from_file_location('microsdd_installer_api', INSTALLER)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

OPTION = re.compile(r'--[a-z][a-z-]*')


def between(text, start, end):
    """Texto entre el encabezado `start` y el siguiente `end`."""
    i = text.index(start) + len(start)
    j = text.find(end, i)
    return text[i:] if j < 0 else text[i:j]


def help_text(*args):
    # En Windows la tubería usa la página de códigos ANSI salvo que se pida UTF-8.
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    out = subprocess.run([sys.executable, str(SDD), *args, '--help'],
                         capture_output=True, text=True, encoding='utf-8', check=True, env=env)
    return out.stdout


def choices(text):
    return re.search(r'\{([^}]*)\}', text).group(1).split(',')


def options(text):
    return set(OPTION.findall(text)) - {'--help'}


def missing(section, names):
    return sorted(n for n in names if f'`{n}`' not in section)


class ApiPublicaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = DOC.read_text(encoding='utf-8')
        cls.api = between(text, '## API pública', '\n## ')
        cls.incluido = between(text, '### Incluido', '### Excluido')
        cls.top = help_text()
        cls.subcommands = choices(cls.top)
        cls.actions = choices(help_text('release'))

    # AC-01
    def test_subcomandos_acciones_y_version_documentados(self):
        names = set(self.subcommands) | set(self.actions) | options(self.top)
        self.assertIn('--version', names)
        self.assertEqual(missing(self.api, names), [],
                         'subcomandos, acciones u opciones globales sin documentar en «API pública»')

    # AC-02
    def test_opciones_largas_de_subcomandos_documentadas(self):
        names = set()
        for sub in self.subcommands:
            names |= options(help_text(sub))
        for action in self.actions:
            names |= options(help_text('release', action))
        self.assertEqual(missing(self.api, names), [],
                         'opciones largas sin documentar en «API pública»')

    # AC-03
    def test_rutas_instaladas_en_incluido(self):
        paths = (set(installer.MANIFEST) | set(installer.MANIFEST.values()) | set(installer.INIT_FILES)
                 | {installer.INSTALL_RECORD})
        self.assertEqual(missing(self.incluido, paths), [],
                         'rutas instaladas ausentes de «Instalación / Incluido»')

    # AC-04
    def test_incluido_solo_lista_rutas_instaladas(self):
        installed = (set(installer.MANIFEST) | set(installer.MANIFEST.values())
                     | set(installer.INIT_FILES) | {installer.INSTALL_RECORD, 'spec/'})
        listed = [m.group(1) for m in re.finditer(r'^- `([^`]+)`', self.incluido, re.M)]
        self.assertTrue(listed, '«Incluido» no contiene elementos de lista con ruta')
        self.assertEqual(sorted(p for p in listed if p not in installed), [],
                         'rutas listadas en «Incluido» que el instalador no instala')


if __name__ == '__main__':
    unittest.main()
