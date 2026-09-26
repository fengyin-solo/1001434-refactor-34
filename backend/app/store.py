"""内存数据仓库：给每个业务模块准备一份可筛选、可流转的示例数据。

真实项目里这里会换成数据库访问层；当前实现只依赖标准库，保证克隆下来就能起。
统计口径只有 app/metrics.py 一份：seed 加载时归一化派生标记，概览直接复用同一套汇总。
"""
from __future__ import annotations

from typing import Any

from app import metrics
from app.registry import MODULE_SPECS, get_spec
from app.seed import SEED_ROWS


class Store:
    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {}
        for name, rows in SEED_ROWS.items():
            spec = get_spec(name)
            self._tables[name] = [metrics.normalize_row(spec, dict(row)) for row in rows]

    def module_names(self) -> list[str]:
        return sorted(self._tables)

    def rows(self, module: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(module, [])

    def find(self, module: str, entry_id: int) -> dict[str, Any] | None:
        for row in self.rows(module):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None

    def module_summary(self, module: str) -> dict[str, object]:
        """单个模块的汇总，与概览用的是同一个函数，两处数字必然一致。"""
        return metrics.summarize(get_spec(module), self.rows(module))

    def overview(self) -> dict[str, object]:
        """运营概览：逐模块汇总；某个模块取不到数时实名标出，不悄悄按零计入。"""
        modules: list[dict[str, object]] = []
        missing: list[str] = []
        for spec in MODULE_SPECS:
            try:
                modules.append(metrics.summarize(spec, self.rows(spec.key)))
            except Exception as exc:  # noqa: BLE001 - 缺数模块要降级展示，不能拖垮整个概览
                missing.append(spec.label)
                modules.append({
                    "name": spec.key,
                    "label": spec.label,
                    "available": False,
                    "error": f"{spec.label}数据暂缺：{exc}",
                })
        available = [item for item in modules if item.get("available", True)]
        cards = [
            {"label": "业务模块", "value": len(available)},
            {"label": "今日新增", "value": sum(int(item["created"]) for item in available)},
            {"label": "待处理", "value": sum(int(item["pending"]) for item in available)},
            {"label": "异常量", "value": sum(int(item["abnormal"]) for item in available)},
        ]
        return {"cards": cards, "modules": modules, "missing": missing}


store = Store()
