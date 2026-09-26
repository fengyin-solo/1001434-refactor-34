"""巡查任务业务规则：状态流转与字段校验在这里组合 registry 与 metrics 的共用口径。"""
from __future__ import annotations

from typing import Any

from app import metrics
from app.registry import get_spec
from app.store import store

SPEC = get_spec("patrol")
MODULE = SPEC.key


class PatrolService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("巡查单号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def stats(self) -> dict[str, object]:
        """模块统计卡：与运营概览共用同一份汇总口径。"""
        return store.module_summary(MODULE)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in SPEC.required_fields if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in SPEC.required_fields})
        entry["status"] = SPEC.status_order[0]
        metrics.normalize_row(SPEC, entry)
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"巡查单 {entry_id} 不存在或已归档"
        if action not in SPEC.action_rules:
            return None, f"动作「{action}」不属于巡查任务可执行范围"
        target = SPEC.action_rules[action]
        if target not in SPEC.status_order:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        metrics.normalize_row(SPEC, entry)
        return entry, f"巡查单已{action}"
