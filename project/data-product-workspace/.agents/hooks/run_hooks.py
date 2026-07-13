#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hook统一调用入口
Coordinator在任务生命周期关键点调用此脚本，自动运行对应触发点的所有Hook
用法:
    python run_hooks.py pre_task "任务描述"
    python run_hooks.py post_execution "结果内容"
    python run_hooks.py post_task "任务产出路径"
"""
import sys
import json
import subprocess
from pathlib import Path

HOOKS_DIR = Path(__file__).parent
CONFIG_PATH = HOOKS_DIR / "hooks_config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def run_hook(hook_name, input_content):
    """运行单个Hook，返回 (success: bool, output: str)"""
    hook_script = HOOKS_DIR / f"{hook_name}.py"
    if not hook_script.exists():
        return True, f"Hook {hook_name} not found, skip"
    
    try:
        result = subprocess.run(
            [sys.executable, str(hook_script), input_content],
            capture_output=True,
            text=True,
            cwd=HOOKS_DIR.parent.parent
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output.strip()
    except Exception as e:
        return False, f"Hook {hook_name} run error: {str(e)}"

def run_trigger_point(trigger_point, input_content):
    """运行指定触发点的所有已启用Hook"""
    config = load_config()
    enabled = config.get("enabled_hooks", [])
    point_hooks = config.get("trigger_points", {}).get(trigger_point, [])
    
    print(f"=== 运行 {trigger_point} 阶段Hook ===")
    print(f"输入: {input_content[:100]}..." if len(input_content) > 100 else f"输入: {input_content}")
    print()
    
    all_passed = True
    for hook in point_hooks:
        if hook not in enabled:
            continue
        print(f"--- 运行 {hook} ---")
        success, output = run_hook(hook, input_content)
        print(output)
        print()
        if not success:
            all_passed = False
    
    print(f"=== {trigger_point} 阶段Hook执行完成 ===")
    if all_passed:
        print("✅ 所有Hook通过，可以继续执行")
        return 0
    else:
        print("❌ 部分Hook不通过，任务阻断")
        return 1

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        print("\n支持的触发点: pre_task / pre_dispatch / post_execution / post_task")
        sys.exit(1)
    
    trigger_point = sys.argv[1]
    input_content = sys.argv[2]
    
    exit_code = run_trigger_point(trigger_point, input_content)
    sys.exit(exit_code)
