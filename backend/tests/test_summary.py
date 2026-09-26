"""运营汇总口径的回归测试。

直接调用 FastAPI 应用（TestClient 需 httpx，这里只测函数与路由返回值，
不依赖额外三方包）：运行方式 `python -m unittest discover backend/tests`
或直接 `python backend/tests/test_summary.py`。

守住的约定：
1. 模块列表按状态重算的待处理/异常量 == 模块 /summary == 概览行；
2. 概览卡片合计 == 各模块行之和；
3. 某模块数据取不到时 /summary 返回 503，概览标记 missing，绝不计零；
4. 状态流转后三处数字一起变；既有接口路径保持可用。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.store import store  # noqa: E402
from app.summary import MODULE_RULES, build_overview  # noqa: E402

client = TestClient(app)


class SummaryCaliberTest(unittest.TestCase):
    def setUp(self) -> None:
        # 每个用例从全新的示例数据开始，避免动作流转互相干扰
        store.reset()

    def _three_sources(self) -> tuple[dict, dict, dict]:
        overview = {m["name"]: m for m in client.get("/api/overview").json()["modules"]}
        per_module: dict[str, dict] = {}
        from_list: dict[str, tuple[int, int, int]] = {}
        for name, rule in MODULE_RULES.items():
            per_module[name] = client.get(f"/api/{name}/summary").json()
            items = client.get(f"/api/{name}", params={"size": 200}).json()["items"]
            from_list[name] = (
                len(items),
                sum(1 for r in items if r["status"] in rule.pending_statuses),
                sum(1 for r in items if r["status"] in rule.abnormal_statuses),
            )
        return overview, per_module, from_list

    def test_list_summary_overview_agree(self) -> None:
        overview, per_module, from_list = self._three_sources()
        for name in MODULE_RULES:
            self.assertEqual(
                (overview[name]["total"], overview[name]["pending"], overview[name]["abnormal"]),
                (per_module[name]["total"], per_module[name]["pending"], per_module[name]["abnormal"]),
            )
            self.assertEqual(
                (per_module[name]["total"], per_module[name]["pending"], per_module[name]["abnormal"]),
                from_list[name],
            )

    def test_card_totals_close(self) -> None:
        payload = client.get("/api/overview").json()
        cards = {c["label"]: c["value"] for c in payload["cards"]}
        self.assertEqual(cards["记录总数"], sum(m["total"] for m in payload["modules"]))
        self.assertEqual(cards["待处理"], sum(m["pending"] for m in payload["modules"]))
        self.assertEqual(cards["异常量"], sum(m["abnormal"] for m in payload["modules"]))

    def test_missing_module_is_not_counted_as_zero(self) -> None:
        store._tables.pop("fund", None)
        response = client.get("/api/fund/summary")
        self.assertEqual(response.status_code, 503)
        self.assertIn("养护资金", response.json()["detail"])

        payload = client.get("/api/overview").json()
        fund = next(m for m in payload["modules"] if m["name"] == "fund")
        self.assertTrue(fund["missing"])
        self.assertIsNone(fund["pending"])
        self.assertIsNone(fund["abnormal"])
        self.assertTrue(any(m["name"] == "fund" for m in payload["missing"]))

        # 缺数的模块不进合计：其余 17 个模块之和即为卡片值
        available = [m for m in payload["modules"] if not m["missing"]]
        cards = {c["label"]: c["value"] for c in payload["cards"]}
        self.assertEqual(len(available), len(MODULE_RULES) - 1)
        self.assertEqual(cards["待处理"], sum(m["pending"] for m in available))
        self.assertEqual(cards["异常量"], sum(m["abnormal"] for m in available))

    def test_overview_marks_keyerror_source(self) -> None:
        def boom(module: str) -> list:
            raise KeyError(module)

        result = build_overview(boom)
        self.assertEqual(len(result["missing"]), len(MODULE_RULES))
        self.assertTrue(all(m["missing"] for m in result["modules"]))
        self.assertTrue(all(c["value"] == 0 or c["label"] == "业务模块" for c in result["cards"]))

    def test_action_flow_keeps_three_sources_in_sync(self) -> None:
        before = client.get("/api/road/summary").json()
        result = client.post(
            "/api/road/1/actions", json={"values": {"action": "办理移交"}}
        ).json()
        self.assertTrue(result["ok"])

        overview, per_module, from_list = self._three_sources()
        self.assertEqual(per_module["road"]["pending"], before["pending"] - 1)
        self.assertEqual(overview["road"]["pending"], per_module["road"]["pending"])
        self.assertEqual(from_list["road"][1], per_module["road"]["pending"])

    def test_legacy_paths_unchanged(self) -> None:
        for path in (
            "/api/health",
            "/api/overview",
            "/api/road",
            "/api/road/2",
            "/api/road/export",
            "/api/bridge/summary",
        ):
            self.assertEqual(client.get(path).status_code, 200, path)

    def test_create_lands_in_pending_bucket(self) -> None:
        response = client.post(
            "/api/road",
            json={"values": {"设施编码": "ROAD-NEW", "道路名称": "新建路", "道路等级": "主干路"}},
        )
        self.assertTrue(response.json()["ok"])
        overview, per_module, from_list = self._three_sources()
        self.assertEqual(overview["road"]["pending"], per_module["road"]["pending"])
        self.assertEqual(overview["road"]["pending"], from_list["road"][1])


if __name__ == "__main__":
    unittest.main()
