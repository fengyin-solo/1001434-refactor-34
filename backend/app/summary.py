"""运营汇总的唯一口径：各模块列表与运营概览共用这一份统计逻辑。

待处理 / 异常量不落在单行数据上，也不允许各模块自己维护布尔标记，
统一由各服务声明的状态序列（STATUS_ORDER）与这里的状态归类推导：

- 待处理（pending）：流程尚未走完、仍需继续办理的状态；
- 异常量（abnormal）：业务或设施本身出现异常、需要关注的状态
  （如堵塞待修、缺亮待修、需返工、已超支、重点观测等）。
- 作废 / 取消 / 报废 / 停用这类业务退出态既不算待处理也不算异常，
  它们是正常的业务结局，而不是需要盯办的例外。

新增模块或调整口径时只改 MODULE_RULES 一处；模块加载时会校验
归类的状态是否都在该服务的 STATUS_ORDER 里，写错状态名直接启动失败，
避免概览与模块页各算各的。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.services import (
    accept as service_accept,
    archive as service_archive,
    assess as service_assess,
    bridge as service_bridge,
    complaint as service_complaint,
    crack as service_crack,
    disease as service_disease,
    drain as service_drain,
    equip as service_equip,
    fund as service_fund,
    light as service_light,
    material as service_material,
    patrol as service_patrol,
    plan as service_plan,
    pothole as service_pothole,
    road as service_road,
    tunnel as service_tunnel,
    work as service_work,
)
from app.store import store


@dataclass(frozen=True)
class ModuleRule:
    label: str
    pending_statuses: frozenset[str]
    abnormal_statuses: frozenset[str]
    status_order: tuple[str, ...]


# 顺序即概览表的展示顺序，与侧边导航保持一致。
MODULE_RULES: dict[str, ModuleRule] = {
    "road": ModuleRule(
        "道路设施", frozenset({"待移交"}), frozenset({"重点观测", "封闭施工"}),
        tuple(service_road.STATUS_ORDER),
    ),
    "bridge": ModuleRule(
        "桥梁档案", frozenset({"待移交"}), frozenset({"限载通行", "封闭施工"}),
        tuple(service_bridge.STATUS_ORDER),
    ),
    "tunnel": ModuleRule(
        "隧道设施", frozenset({"待移交"}), frozenset({"检修封闭"}),
        tuple(service_tunnel.STATUS_ORDER),
    ),
    "patrol": ModuleRule(
        "巡查任务", frozenset({"待派发", "巡查中"}), frozenset(),
        tuple(service_patrol.STATUS_ORDER),
    ),
    "disease": ModuleRule(
        "病害登记", frozenset({"待定级", "已定级", "处置中"}), frozenset({"已挂起"}),
        tuple(service_disease.STATUS_ORDER),
    ),
    "assess": ModuleRule(
        "技术评定", frozenset({"待评定", "评定中"}), frozenset(),
        tuple(service_assess.STATUS_ORDER),
    ),
    "plan": ModuleRule(
        "养护计划", frozenset({"待编制", "待审批"}), frozenset(),
        tuple(service_plan.STATUS_ORDER),
    ),
    "work": ModuleRule(
        "养护施工", frozenset({"待开工", "施工中", "待验收"}), frozenset(),
        tuple(service_work.STATUS_ORDER),
    ),
    "accept": ModuleRule(
        "竣工验收", frozenset({"待验收", "验收中", "需返工"}), frozenset({"需返工"}),
        tuple(service_accept.STATUS_ORDER),
    ),
    "pothole": ModuleRule(
        "坑槽修补", frozenset({"待安排", "修补中"}), frozenset(),
        tuple(service_pothole.STATUS_ORDER),
    ),
    "crack": ModuleRule(
        "裂缝处置", frozenset({"待安排", "处置中"}), frozenset(),
        tuple(service_crack.STATUS_ORDER),
    ),
    "drain": ModuleRule(
        "排水设施", frozenset({"待清疏", "堵塞待修"}), frozenset({"堵塞待修"}),
        tuple(service_drain.STATUS_ORDER),
    ),
    "light": ModuleRule(
        "照明设施", frozenset({"待检修", "缺亮待修"}), frozenset({"缺亮待修"}),
        tuple(service_light.STATUS_ORDER),
    ),
    "material": ModuleRule(
        "养护材料", frozenset({"临近不足"}), frozenset({"临近不足", "已冻结", "已耗尽"}),
        tuple(service_material.STATUS_ORDER),
    ),
    "equip": ModuleRule(
        "养护机械", frozenset({"待保养", "保养中"}), frozenset(),
        tuple(service_equip.STATUS_ORDER),
    ),
    "fund": ModuleRule(
        "养护资金", frozenset({"待审批"}), frozenset({"已超支"}),
        tuple(service_fund.STATUS_ORDER),
    ),
    "complaint": ModuleRule(
        "公众诉求", frozenset({"待受理", "办理中"}), frozenset(),
        tuple(service_complaint.STATUS_ORDER),
    ),
    "archive": ModuleRule(
        "设施档案", frozenset({"待归档", "待补充"}), frozenset({"待补充"}),
        tuple(service_archive.STATUS_ORDER),
    ),
}


def _validate_rules() -> None:
    for module, rule in MODULE_RULES.items():
        known = set(rule.status_order)
        unknown = (rule.pending_statuses | rule.abnormal_statuses) - known
        if unknown:
            raise RuntimeError(
                f"模块 {module} 的待处理/异常状态 {sorted(unknown)} 不在状态序列 "
                f"{list(rule.status_order)} 内，请同步修改 summary 的统计口径"
            )


_validate_rules()


def rule_for(module: str) -> ModuleRule:
    rule = MODULE_RULES.get(module)
    if rule is None:
        raise KeyError(f"未登记的业务模块：{module}")
    return rule


def summarize_rows(module: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """按统一口径统计一个模块的记录总数、待处理与异常量。"""
    rule = rule_for(module)
    pending = sum(1 for row in rows if row.get("status") in rule.pending_statuses)
    abnormal = sum(1 for row in rows if row.get("status") in rule.abnormal_statuses)
    return {
        "name": module,
        "label": rule.label,
        "total": len(rows),
        "pending": pending,
        "abnormal": abnormal,
        "missing": False,
    }


def summarize_module(module: str) -> dict[str, Any]:
    """供各模块的 /summary 接口使用：未登记模块或数据取不到时抛 KeyError，
    由路由层转成 503 并说明是哪一块缺数，不按零兜底。
    """
    return summarize_rows(module, store.table(module))


def build_overview(get_rows: Callable[[str], list[dict[str, Any]]]) -> dict[str, Any]:
    """汇总全部模块；某个模块数据取不到时标记缺数，绝不悄悄计零。"""
    modules: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    for module, rule in MODULE_RULES.items():
        try:
            rows = get_rows(module)
        except KeyError:
            reason = f"{rule.label}（{module}）的示例数据未生成，汇总未计入该模块"
            missing.append({"name": module, "label": rule.label, "reason": reason})
            modules.append({
                "name": module,
                "label": rule.label,
                "total": None,
                "pending": None,
                "abnormal": None,
                "missing": True,
                "reason": reason,
            })
            continue
        modules.append(summarize_rows(module, rows))

    cards = [
        {"label": "业务模块", "value": len(MODULE_RULES)},
        {"label": "记录总数", "value": sum(int(item["total"]) for item in modules if not item.get("missing"))},
        {"label": "待处理", "value": sum(int(item["pending"]) for item in modules if not item.get("missing"))},
        {"label": "异常量", "value": sum(int(item["abnormal"]) for item in modules if not item.get("missing"))},
    ]
    return {"cards": cards, "modules": modules, "missing": missing}
