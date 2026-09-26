"""统计口径：待处理与异常量的唯一算法，概览、模块统计、seed 归一化都走这里。

口径约定（由 registry 的模块规则推导，全平台一致）：
- 待处理 pending：记录状态不是终态（状态序列末位）；
- 异常量 abnormal：记录状态落在负向动作（作废、停用等）的目标状态集里。

记录上的 pending / abnormal 两个字段只是这份口径的缓存，由 normalize_row 统一写入，
任何入口都不许再手工赋值，避免模块页与概览页各算各的。
"""
from __future__ import annotations

from typing import Any, Iterable

from app.registry import ModuleSpec


def is_pending(spec: ModuleSpec, row: dict[str, Any]) -> bool:
    """待处理：状态不是终态即仍需跟进。"""
    return str(row.get("status") or "") != spec.terminal_status


def is_abnormal(spec: ModuleSpec, row: dict[str, Any]) -> bool:
    """异常：状态落在负向动作的目标状态集里（已作废、已停用等）。"""
    return str(row.get("status") or "") in spec.abnormal_statuses


def normalize_row(spec: ModuleSpec, row: dict[str, Any]) -> dict[str, Any]:
    """按口径回写记录的派生标记；seed 加载、登记、动作流转后都必须过这里。"""
    row["pending"] = is_pending(spec, row)
    row["abnormal"] = is_abnormal(spec, row)
    return row


def summarize(spec: ModuleSpec, rows: Iterable[dict[str, Any]]) -> dict[str, object]:
    """单个模块的汇总：概览卡片与模块页统计卡共用这一份结果。"""
    items = list(rows)
    return {
        "name": spec.key,
        "label": spec.label,
        "created": len(items),
        "pending": sum(1 for row in items if is_pending(spec, row)),
        "abnormal": sum(1 for row in items if is_abnormal(spec, row)),
    }
