"""Archive full compiler output; assemble reachable native bodies verbatim.

All exported functions and function addresses in static data are roots. Follow
every symbolic reference, including callback addresses, not just direct calls.
Unreachable entry points trap rather than simulating successful execution.
"""
import json
import re


def write_native(directory, assembly):
    (directory / 'full-probe.asm').write_text(assembly)
    cut = assembly.index('\nsection .rodata')
    code, data = assembly[:cut], assembly[cut:]
    starts = list(re.finditer(r'(?m)^align 16\n\$(\w+):\n', code))
    if not starts:
        raise AssertionError('missing generated function boundaries')
    bodies = {m[1]: code[m.start():starts[i + 1].start() if i + 1 < len(starts) else len(code)]
              for i, m in enumerate(starts)}

    def refs(text):
        return set(re.findall(r'\$(\w+)', text)) & bodies.keys()

    exports = set(re.findall(r'(?m)^global \$(\w+)\s*$', code)) & bodies.keys()
    if not exports:
        raise AssertionError('native probe must export its C entry points')
    keep = exports | refs(data)
    pending = list(keep)
    while pending:
        more = refs(bodies[pending.pop()]) - keep
        keep.update(more)
        pending.extend(more)
    result = code[:starts[0].start()] + ''.join(
        body if name in keep else 'align 16\n$' + name + ':\n    ud2\n'
        for name, body in bodies.items()) + data
    (directory / 'reachability.json').write_text(json.dumps(
        dict(exports=sorted(exports), kept=sorted(keep), trapped=sorted(bodies.keys() - keep)), indent=2))
    target = directory / 'probe.asm'
    target.write_text(result)
    return target
