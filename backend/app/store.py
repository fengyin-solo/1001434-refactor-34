"""内存数据仓库：给每个业务模块准备一份可筛选、可流转的示例数据。

真实项目里这里会换成数据库访问层；当前实现只依赖标准库，保证克隆下来就能起。
"""
from __future__ import annotations

from typing import Any

from app.seed import SEED_ROWS


class Store:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """恢复成初始示例数据；测试用例之间用它回到同一起点。"""
        self._tables: dict[str, list[dict[str, Any]]] = {
            name: [dict(row) for row in rows] for name, rows in SEED_ROWS.items()
        }

    def module_names(self) -> list[str]:
        return sorted(self._tables)

    def rows(self, module: str) -> list[dict[str, Any]]:
        # 服务层用于读写本模块数据；模块缺失时按空表初始化。
        return self._tables.setdefault(module, [])

    def table(self, module: str) -> list[dict[str, Any]]:
        # 汇总口径专用：模块数据根本没有生成时显式报缺数，
        # 不能让缺数的模块被静默当成“恰好零条”。
        if module not in self._tables:
            raise KeyError(module)
        return self._tables[module]

    def find(self, module: str, entry_id: int) -> dict[str, Any] | None:
        for row in self.rows(module):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None


store = Store()
