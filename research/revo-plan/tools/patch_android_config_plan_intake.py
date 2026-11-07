#!/usr/bin/env python3
"""Opt-in support for validated offline plans in the existing v0.2.9 Android Wails adapter."""
import argparse
import hashlib
from pathlib import Path

CONFIG_START = '''  function buildEngineConfig(account) {
'''
RESEARCH_HELPER = '''  // Experimental overlay; never silently enables a new native movement routine.
  function withResearchPlan(config) {
    const raw = localStorage.getItem('revo.research.actionPlanV1');
    if (raw === null || raw === '') return config;
    let record;
    try { record = JSON.parse(raw); } catch (e) {
      throw new Error('[research-plan] invalid saved JSON: ' + String(e));
    }
    if (!record || record.enabled !== true) return config;
    const plan = record.plan;
    if (!plan || plan.schema !== 'revo.action-plan.v1' ||
        plan.dryRunOnly !== true || !Array.isArray(plan.actions) ||
        plan.pattern !== config.patternName || !config.patternName ||
        !Number.isFinite(plan.movementMsPerStud)) {
      throw new Error('[research-plan] plan schema, mode, or selected Gather pattern mismatch');
    }
    // The native gather adapter falls back to 62.5 ms/stud when the override is zero.
    const effectiveMsPerStud = config.msPerStud > 0 ? config.msPerStud : 62.5;
    if (Math.abs(plan.movementMsPerStud - effectiveMsPerStud) > 0.00001) {
      throw new Error('[research-plan] movement calibration mismatch');
    }
    return {...config, actionPlan: plan, enablePlannedExecution: true};
  }

'''
EARLY_RETURN = """      return { routine: 'gather', account: String(account || 'Default'), patternName: '', requireRobloxForeground: true };"""
LATE_START = """    return {
      routine: 'gather',
      account: String(account || 'Default'),"""
LATE_END = """      requireRobloxForeground: true
    };
  }

  function pinVersion()"""
NATIVE_RESULT = """        console.log('[android-engine] configured', JSON.stringify(cfg), JSON.stringify(state));"""
CATCH = """        console.error('[android-engine] configure failed', String(e));
      }
      return originalStart(account);"""

def replace_once(src, old, new, label):
    if src.count(old) != 1:
        raise ValueError(f'expected exactly one {label} anchor; refusing patch')
    return src.replace(old, new, 1)

def patch(source):
    result = replace_once(source, CONFIG_START, RESEARCH_HELPER + CONFIG_START, 'helper')
    result = replace_once(result, EARLY_RETURN,
        """      return withResearchPlan({ routine: 'gather', account: String(account || 'Default'), patternName: '', requireRobloxForeground: true });""",
        'empty selected Gather pattern')
    result = replace_once(result, LATE_START, """    return withResearchPlan({
      routine: 'gather',
      account: String(account || 'Default'),""", 'main config')
    result = replace_once(result, LATE_END, """      requireRobloxForeground: true
    });
  }

  function pinVersion()""", 'main config end')
    result = replace_once(result, NATIVE_RESULT,
        """        if (cfg.enablePlannedExecution &&
            (state.lastDecision === 'configure-error' || !(Number(state.patternStepCount) > 0))) {
          throw new Error('[research-plan] native Android plan intake refused');
        }
        console.log('[android-engine] configured', JSON.stringify(cfg), JSON.stringify(state));""",
        'native acceptance')
    result = replace_once(result, CATCH,
        """        console.error('[android-engine] configure failed', String(e));
        if (cfg.enablePlannedExecution) throw e; // No Roblox launch after rejected plan.
      }
      return originalStart(account);""",
        'native failure guard')
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source', required=True)
    ap.add_argument('--output', required=True)
    args=ap.parse_args()
    source=Path(args.source)
    output=Path(args.output)
    if source.resolve()==output.resolve():
        raise SystemExit('refusing to overwrite the original backend overlay')
    original=source.read_text(encoding='utf-8')
    result=patch(original)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result,encoding='utf-8',newline='\n')
    print('RESEARCH_FRONTEND_PLAN_PATCH_OK',
          'input_sha256='+hashlib.sha256(original.encode()).hexdigest(),
          'output_sha256='+hashlib.sha256(result.encode()).hexdigest())

if __name__=='__main__':
    main()
