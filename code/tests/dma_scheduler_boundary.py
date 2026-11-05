"""Absent scheduler boundary for memory tests that never exercise DMA retirement.

Types are taken from production declarations. No successful stop/barrier is
fabricated: pointer() is null and drain() fails. Retirement tests use the real
modules, and production module-graph checks never call this helper.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def absent_scheduler():
    domain = (ROOT / 'kernel/sched/user_domain.dg').read_text(encoding='utf-8')
    domain = domain[:domain.index('// Optional trusted kernel observer.')]
    domain += '\npub unsafe fn drain(d:*Domain,cpu:usize)!bool{return error.State;}\n'
    bridge = (ROOT / 'kernel/sched/user_bridge.dg').read_text(encoding='utf-8')
    types = bridge[bridge.index('pub struct Pending'):bridge.index('pub struct Counts')]
    bridge = ('module sched.user_bridge;\nimport sched.user_domain as ud;\n' + types
              + '\npub fn pointer()*Bridge{return null;}\n')
    return {'sched.user_bridge': bridge, 'sched.user_domain': domain}
