def require_human_terminal(action: str) -> None:
    """approve/seal/allow-test-command solo en terminal interactiva fuera de Claude Code."""
    if 'CLAUDECODE' in os.environ or sys.stdin is None or not sys.stdin.isatty():
        if action == 'seal':
            suffix = 'seal <slug> --by <nombre> --evidence <texto|@note:id>'
        elif action == 'approve':
            suffix = 'approve <slug> spec --by <nombre> --evidence <texto|@note:id>'
        elif action == 'allow-test-command':
            suffix = 'allow-test-command <token>... --evidence @note:<id>'
        else:
            suffix = '<subcomando>'
        hint = _example_sdd_command(suffix)
        raise ValueError(f'{action} es una decisión humana: ejecútalo tú en una terminal '
                         f'interactiva, fuera de Claude Code (p. ej. {hint}).')


def note_ref_id(evidence: str) -> str | None:
    m = NOTE_REF_RE.fullmatch((evidence or '').strip())
    return m.group(1) if m else None


def agent_may_approve_enabled() -> bool:
    return bool(config().get('agent_may_approve', True))


def maybe_require_human_terminal(action: str, evidence: str) -> None:
    if agent_may_approve_enabled() and note_ref_id(evidence):
        return
    require_human_terminal(action)


def next_note_id(observations: list) -> str:
    max_n = 0
    for obs in observations:
        if not isinstance(obs, dict):
            continue
        oid = obs.get('id')
        if isinstance(oid, str) and re.fullmatch(r'n[1-9][0-9]*', oid):
            max_n = max(max_n, int(oid[1:]))
    return f'n{max_n + 1}'


def consume_note(memory: dict, note_id: str, for_phase: str, for_task: str | None = None) -> dict:
    project = memory.get('project', {})
    observations = project.get('observations', []) if isinstance(project, dict) else []
    if not isinstance(observations, list):
        raise ValueError(f'Nota {note_id} no existe.')
    target = None
    for obs in observations:
        if isinstance(obs, dict) and obs.get('id') == note_id:
            target = obs
            break
    if target is None:
        raise ValueError(f'Nota {note_id} no existe.')
    if target.get('used_at') is not None:
        raise ValueError(f'Nota {note_id} ya fue consumida.')
    if target.get('for_phase') != for_phase:
        raise ValueError(f'Nota {note_id} no corresponde a la fase {for_phase}.')
    if for_task is not None and target.get('for_task') != for_task:
        raise ValueError(f'Nota {note_id} no corresponde a la tarea {for_task}.')
    try:
        created = datetime.fromisoformat(target['at'])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f'Nota {note_id} sin marca de tiempo válida.') from None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - created).total_seconds()
    if age > NOTE_EVIDENCE_MAX_AGE_S:
        raise ValueError(f'Nota {note_id} expirada (máx. {NOTE_EVIDENCE_MAX_AGE_S} s).')
    target['used_at'] = now()
    return target


def _reject_if_memory_corrupt() -> None:
    """No mutar memory si la integridad vs HEAD ya falla (H2)."""
    if not MEMORY.is_file():
        return
    try:
        memory = load(MEMORY)
    except (OSError, ValueError):
        return
    errors = memory_integrity(memory)
    if errors:
        raise ValueError('Memoria corrupta o alterada; no se escribe: ' + '; '.join(errors))


@memory_lock()
def approve(slug: str, phase: str, by: str, evidence: str) -> None:
    # Se registra una declaración, no una identidad autenticada. Requiere decisión humana explícita.
    maybe_require_human_terminal('approve', evidence)
    _reject_if_memory_corrupt()
    path, spec, memory = task_files(slug)
    if not by.strip() or not evidence.strip():
        raise ValueError('Se requiere autor de aprobación y texto de evidencia explícita.')
    if phase == 'spec':
        if spec['state'] == 'terminado':
            raise ValueError('La tarea terminó; inicia una nueva spec para otro cambio.')
        failures = [e for e in validate(slug, scope=False)
                    if 'Especificación alterada después de aprobación' not in e]
        if failures:
            raise ValueError('La spec no es válida: ' + '; '.join(failures))
    if phase == 'close':
        if spec['state'] != 'proceso':
            raise ValueError('Solo puede cerrarse una tarea en proceso.')
        if memory['tasks'][slug].get('review') != 'APROBADO':
            raise ValueError('Falta revisión independiente APROBADO registrada.')
        expected = memory['tasks'][slug].get('review_fingerprint')
        if expected != code_fingerprint(spec['scope']['allowed_paths']):
            raise ValueError('El código cambió después de la revisión: requiere otra revisión.')
        failures = validate(slug, run=True)
        if failures:
            raise ValueError('Puerta de calidad fallida: ' + '; '.join(failures))
    note_id = note_ref_id(evidence)
    if note_id and agent_may_approve_enabled():
        consume_note(memory, note_id, for_phase=phase, for_task=slug)
    memory['tasks'][slug]['approvals'][phase] = {'by': by, 'evidence': evidence, 'at': now()}
    if phase == 'spec':
        memory['tasks'][slug]['approvals'][phase]['fingerprint'] = spec_fingerprint(path, spec)
        memory['tasks'][slug]['approvals']['close'] = None
        memory['tasks'][slug]['review'] = None
        memory['tasks'][slug]['review_fingerprint'] = None
        memory['tasks'][slug]['iterations'] = 0
    memory['tasks'][slug]['events'].append({'at': now(), 'event': f'aprobación_{phase}', 'by': by})
    if phase == 'spec':
        spec['state'] = 'proceso'
    else:
        spec['state'] = 'terminado'
    dump(MEMORY, memory)
    dump(path / 'spec.json', spec)
    print(f'Aprobación declarada registrada ({phase}). No es una firma ni autentica al usuario.')


@memory_lock()
def review(slug: str, verdict: str, evidence: str) -> None:
    _reject_if_memory_corrupt()
    path, spec, memory = task_files(slug)
    if spec['state'] != 'proceso' or not memory['tasks'][slug]['approvals']['spec']:
        raise ValueError('La tarea no está en proceso con spec aprobada.')
    if not evidence.strip():
        raise ValueError('Registra evidencia concreta del dictamen.')
    task = memory['tasks'][slug]
    task['iterations'] += 1
    if task['iterations'] > spec['max_iterations']:
        raise ValueError('Se agotó max_iterations; requiere intervención humana.')
    task['review'] = verdict
    task['review_fingerprint'] = code_fingerprint(spec['scope']['allowed_paths']) if verdict == 'APROBADO' else None
    task['events'].append({'at': now(), 'event': 'revisión', 'verdict': verdict, 'evidence': evidence})
    if verdict == 'RECHAZADO' and task['iterations'] >= spec['max_iterations']:
        spec['state'] = 'pendiente'
        task['events'].append({'at': now(), 'event': 'escalado', 'reason': 'Intentos agotados'})
    dump(path / 'spec.json', spec)
    dump(MEMORY, memory)
    print('Revisión registrada.', 'Escalada al humano.' if spec['state'] == 'pendiente' else '')


@memory_lock()
def note(fact: str | None, decision: str | None, by: str | None, evidence: str,
         for_task: str | None = None, for_phase: str | None = None) -> None:
    # Se registra una declaración, no una identidad autenticada.
    _reject_if_memory_corrupt()
    if (fact is None) == (decision is None):
        raise ValueError('Indica exactamente uno de --fact o --decision.')
    if decision is not None and by is None:
        raise ValueError('--decision requiere --by.')
    if fact is not None and by is not None:
        raise ValueError('--by solo se admite con --decision.')
    if (for_task is None) != (for_phase is None):
        raise ValueError('Indica --for-task y --for-phase juntos, o ninguno.')
    if for_phase is not None and for_phase not in NOTE_PHASES:
        raise ValueError(f'for_phase debe ser uno de: {", ".join(NOTE_PHASES)}')
    if for_task is not None:
        if fact is None:
            raise ValueError('--for-task/--for-phase solo se admiten con --fact.')
        if not SLUG_RE.fullmatch(for_task):
            raise ValueError('Slug inválido: usa minúsculas, números y guiones; empieza con letra.')
    if any(not text.strip() for text in (fact, decision, by, evidence) if text is not None):
        raise ValueError('Los textos de la nota no pueden estar vacíos.')
    if not MEMORY.exists():
        ensure_init()
    memory = load(MEMORY)
    project = memory.setdefault('project', {})
    if fact is not None:
        observations = project.setdefault('observations', [])
        entry = {'at': now(), 'fact': fact, 'evidence': evidence}
        if for_task is not None:
            note_id = next_note_id(observations)
            entry.update({'id': note_id, 'for_task': for_task, 'for_phase': for_phase, 'used_at': None})
            observations.append(entry)
            dump(MEMORY, memory)
            print(f'Nota registrada: {note_id}')
            return
        observations.append(entry)
    else:
        project.setdefault('decisions', []).append({'at': now(), 'by': by, 'decision': decision, 'evidence': evidence})
    dump(MEMORY, memory)
    print('Nota registrada en memory.json.' if fact is not None
          else 'Decisión declarada registrada. No es una firma ni autentica al usuario.')


@memory_lock()
def seal(slug: str, by: str, evidence: str) -> None:
    maybe_require_human_terminal('seal', evidence)
    _reject_if_memory_corrupt()
    _, spec, memory = task_files(slug)
    tests = spec['testing']['protected_tests']
    if not tests:
        raise ValueError('No hay testing.protected_tests; selecciona pruebas concretas.')
    if not by.strip() or not evidence.strip():
        raise ValueError('Se requiere identificación declarada y texto de evidencia explícita.')
    note_id = note_ref_id(evidence)
    if note_id and agent_may_approve_enabled():
        consume_note(memory, note_id, for_phase='seal', for_task=slug)
    hashes: dict[str, str] = {}
    for test in tests:
        relative = normalized_rel(test)
        target = ROOT / relative
        if not target.is_file() or not target.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError(f'No existe test seguro: {relative}')
        hashes[relative] = hash_file(target)
    memory['tasks'][slug]['sealed_tests'] = hashes
    memory['tasks'][slug]['events'].append(
        {'at': now(), 'event': 'sellado_tests', 'by': by, 'evidence': evidence, 'files': list(hashes)})
    dump(MEMORY, memory)
    print(f'{len(hashes)} pruebas selladas. Versiona memory.json y conserva baseline Git protegido.')


@memory_lock()
def allow_test_command(tokens: list[str], evidence: str) -> None:
    maybe_require_human_terminal('allow-test-command', evidence)
    _reject_if_memory_corrupt()
    if not tokens or any(not isinstance(t, str) or not t.strip() for t in tokens):
        raise ValueError('Se requiere al menos un token no vacío.')
    if not MEMORY.exists():
        ensure_init()
    memory = load(MEMORY)
    note_id = note_ref_id(evidence)
    if note_id and agent_may_approve_enabled():
        consume_note(memory, note_id, for_phase='allow-test', for_task=None)
    project = memory.setdefault('project', {})
    allowed = project.setdefault('allowed_test_commands', [])
    if not isinstance(allowed, list):
        raise ValueError('project.allowed_test_commands inválido')
    allowed.append([t.strip() for t in tokens])
    dump(MEMORY, memory)
    print(f'Prefijo autorizado en allowed_test_commands: {[t.strip() for t in tokens]}')


def commit_check(message: str) -> None:
    if not COMMIT_RE.fullmatch(message):
        raise ValueError('Commit no convencional. Ej.: fix(auth): valida expiración del token')
    print('Mensaje Conventional Commit válido (validación sintáctica básica).')


def git(*args: str) -> str:
    result = subprocess.run(['git', '-c', 'core.quotePath=false', *args], cwd=ROOT, capture_output=True,
                            text=True, encoding='utf-8', check=False)
    if result.returncode != 0:
        raise ValueError(f'git {" ".join(args)} falló: {result.stderr.strip()}')
    return result.stdout


def release_propose() -> None:
    if git('branch', '--show-current').strip() != 'main':
        raise ValueError('release propose exige la rama main.')
    busy = [p.parent.name for p in sorted((ROOT / 'spec').glob('*/spec.json')) if load(p).get('state') == 'proceso']
    if busy:
        raise ValueError(f'Hay tareas en proceso: {", ".join(busy)}.')
    records, changed = iter(git('status', '--porcelain', '-z', '--untracked-files=all').split('\0')), []
    for record in records:
        if record:
            changed.append(record[3:])
            if 'R' in record[:2] or 'C' in record[:2]: changed.append(next(records))  # ruta de origen
    outside = [p for p in changed if not p.startswith('spec/') and p not in ('.microharness/memory.json', '.microharness/memory.lock')]
    if outside:
        raise ValueError(f'Árbol con cambios fuera de spec/ y .microharness/memory.json: {", ".join(outside)}')
    tags = [t for t in git('tag', '--merged', 'HEAD', '--list', 'v*').split() if FINAL_TAG_RE.match(t)]
    base = max(tags, key=lambda t: tuple(map(int, FINAL_TAG_RE.match(t).groups())), default=None)
    subjects = git('log', '--reverse', '--format=%s', f'{base}..HEAD' if base else 'HEAD').splitlines()
    level, lines = 0, []  # 3 incompatible, 2 añadido, 1 corregido, 0 sin incremento
    for subject in subjects:
        m = SUBJECT_RE.match(subject)
        if m and m.group(3): group, rank = 'Incompatible', 3
        elif m and m.group(1) == 'feat': group, rank = 'Añadido', 2
        elif m and m.group(1) in ('fix', 'perf'): group, rank = 'Corregido', 1
        else: group, rank = 'Otros', 0
        lines.append(f'{group}: {subject}')
        level = max(level, rank)
    if not level:
        raise ValueError('Commits sin incremento; no se publica versión.')
    if base:
        x, y, z = map(int, FINAL_TAG_RE.match(base).groups())
        if x == 0:
            level = 2 if level == 3 else 1
        version = {3: f'{x + 1}.0.0', 2: f'{x}.{y + 1}.0', 1: f'{x}.{y}.{z + 1}'}[level]
    else:
        m = re.search(r"^__version__ = '([^']*)'", (ROOT / '.microharness' / 'sdd.py').read_text(encoding='utf-8'), re.M)
        if not m:
            raise ValueError('No se encontró __version__ en .microharness/sdd.py.')
        version = re.sub(r'-rc\.[0-9]+$', '', m.group(1))
    print(f'Último tag: {base or "(ninguno)"}')
    for line in lines: print(line)
    print(f'Versión propuesta: {version}')


def main() -> int:
    p = argparse.ArgumentParser(description='MicroSDD · validación y memoria, no orquestación LLM')
    p.add_argument('--version', action='version', version=f'MicroSDD {__version__}')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('new').add_argument('slug')
    check = sub.add_parser('check'); check.add_argument('slug'); check.add_argument('--run', action='store_true'); check.add_argument('--no-scope', action='store_true')
    ap = sub.add_parser('approve'); ap.add_argument('slug'); ap.add_argument('phase', choices=('spec', 'close')); ap.add_argument('--by', required=True); ap.add_argument('--evidence', required=True)
    rev = sub.add_parser('review'); rev.add_argument('slug'); rev.add_argument('verdict', choices=('APROBADO', 'RECHAZADO')); rev.add_argument('--evidence', required=True)
    se = sub.add_parser('seal'); se.add_argument('slug'); se.add_argument('--by', required=True); se.add_argument('--evidence', required=True)
    no = sub.add_parser('note'); no.add_argument('--fact'); no.add_argument('--decision'); no.add_argument('--by'); no.add_argument('--evidence', required=True); no.add_argument('--for-task'); no.add_argument('--for-phase', choices=NOTE_PHASES)
    atc = sub.add_parser('allow-test-command'); atc.add_argument('tokens', nargs='+'); atc.add_argument('--evidence', required=True)
    sub.add_parser('commit-check').add_argument('message')
    rel = sub.add_parser('release')
    rel.add_subparsers(dest='action', required=True).add_parser('propose')
    args = p.parse_args()
    try:
        if args.command in ('approve', 'seal', 'allow-test-command'):
            maybe_require_human_terminal(args.command, getattr(args, 'evidence', '') or '')
        if args.command == 'init': ensure_init()
        elif args.command == 'new': new(args.slug)
        elif args.command == 'check':
            failures = validate(args.slug, run=args.run, scope=not args.no_scope)
            if failures:
                for failure in failures: print('ERROR:', failure, file=sys.stderr)
                return 1
            print('OK: spec, alcance, hashes y' + (' ejecución de pruebas.' if args.run else ' estructura.'))
        elif args.command == 'approve': approve(args.slug, args.phase, args.by, args.evidence)
        elif args.command == 'review': review(args.slug, args.verdict, args.evidence)
        elif args.command == 'seal': seal(args.slug, args.by, args.evidence)
        elif args.command == 'note': note(args.fact, args.decision, args.by, args.evidence, args.for_task, args.for_phase)
        elif args.command == 'allow-test-command': allow_test_command(args.tokens, args.evidence)
        elif args.command == 'commit-check': commit_check(args.message)
        elif args.command == 'release': release_propose()
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        print('ERROR:', e, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
