// Temporary build script consumed by cloud agent; removed before merge.
export function patch(s) {
  const once = (src, old, neu, label) => {
    const c = src.split(old).length - 1;
    if (c !== 1) throw new Error(label + ' count=' + c);
    // Escape $ for String.replace
    return src.replace(old, neu.replace(/\$/g, '$$$$'));
  };
  s = once(s, "__version__ = '1.1.3'", "__version__ = '1.2.0'", 'v');
  s = once(s,
    "EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')\n_LOCK_DEPTH = 0\n",
    "EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')\nNOTE_EVIDENCE_MAX_AGE_S = 1800\nNOTE_REF_RE = re.compile(r'^@note:([a-zA-Z0-9_-]+)$')\nNOTE_IN_CMD_RE = re.compile(r'@note:[a-zA-Z0-9_-]+')\nNOTE_PHASES = ('spec', 'close', 'seal', 'allow-test')\n_LOCK_DEPTH = 0\n",
    'c');
  s = once(s,
    "cfg = {'model': DEFAULT_MODEL, 'effort': DEFAULT_EFFORT}",
    "cfg = {'model': DEFAULT_MODEL, 'effort': DEFAULT_EFFORT, 'agent_may_approve': True}",
    'cfg');
  s = once(s,
    "raise ValueError(f'.microharness/config.json: effort debe ser uno de: {\", \".join(EFFORTS)}')\n    cfg.update(data)",
    "raise ValueError(f'.microharness/config.json: effort debe ser uno de: {\", \".join(EFFORTS)}')\n    if 'agent_may_approve' in data and not isinstance(data['agent_may_approve'], bool):\n        raise ValueError('.microharness/config.json: agent_may_approve debe ser un booleano')\n    cfg.update(data)",
    'val');
  return s;
}
