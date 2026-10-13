#!/usr/bin/env python3
"""MicroSDD: validaciones locales sin dependencias. No ejecuta Claude ni autentica al humano."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
MEMORY = ROOT / '.microharness' / 'memory.json'
DOCS = ('AGENT.md', 'arquitectura.md', 'convenciones.md', 'especificaciones.md')
# Nombres antiguos (compatibilidad): init avisa y no duplica ni mueve archivos del usuario.
LEGACY_DOCS = {'convenciones.md': 'convensiones.md', 'especificaciones.md': 'specificaciones.md'}
TASK_FILES = ('spec.json', 'requerimientos.md', 'plan.md', 'tareas.md')
STATES = ('pendiente', 'proceso', 'terminado')
SLUG_RE = re.compile(r'^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$')
COMMIT_RE = re.compile(r'^(feat|fix|docs|test|refactor|perf|chore)(\([a-z0-9][a-z0-9-]*\))?(!)?: [^\n]{1,72}$')
__version__ = '1.1.3'
SUBJECT_RE = re.compile(r'^([a-z]+)(\([^)]*\))?(!)?: ')
FINAL_TAG_RE = re.compile(r'^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$')
LOCK_TIMEOUT = 10.0
DEFAULT_MODEL = 'claude-opus-5-5'
DEFAULT_EFFORT = 'medium'
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')
_LOCK_DEPTH = 0
# Resúmenes de runners: unittest, pytest, bun y Maven (se usa la última coincidencia de cada uno).
TEST_COUNT_RES = (
    re.compile(r'^Ran (\d+) tests? in', re.M),
    re.compile(r'\b(\d+) passed\b'),
    re.compile(r'^[ \t]*(\d+) pass\b', re.M),
    re.compile(r'Tests run: (\d+)'),
)
GO_OK_RE = re.compile(r'^ok[ \t]+\S+', re.M)
# Lista blanca de prefijos de argv para testing.commands y mutation.command (comparación exacta de tokens).
TEST_COMMANDS = (
    ('python', '-m', 'unittest'), ('python3', '-m', 'unittest'), ('python', '-m', 'pytest'),
    ('python3', '-m', 'pytest'), ('pytest',), ('npm', 'test'), ('pnpm', 'test'), ('yarn', 'test'),
    ('bun', 'test'), ('go', 'test'), ('cargo', 'test'), ('mvn', 'test'), ('./mvnw', 'test'),
    ('gradle', 'test'), ('./gradlew', 'test'), ('mutmut', 'run'),
)
# Campos vigilados de cada tarea abierta en HEAD y tipos de evento nuevo que justifican su cambio.
INTEGRITY_FIELDS = (
    (('approvals', 'spec'), ('aprobación_spec',)),
    (('approvals', 'close'), ('aprobación_close', 'aprobación_spec')),
    (('sealed_tests',), ('sellado_tests',)),
    (('review',), ('revisión', 'aprobación_spec')),
    (('review_fingerprint',), ('revisión', 'aprobación_spec')),
    (('iterations',), ('revisión', 'aprobación_spec')),
)


def _example_sdd_command(suffix: str) -> str:
    if os.name == 'nt':
        return f'python .microharness\\sdd.py {suffix}'
    return f'sh .microharness/python.sh .microharness/sdd.py {suffix}'


TRUNCATED_MARKER_REMOVE_ME