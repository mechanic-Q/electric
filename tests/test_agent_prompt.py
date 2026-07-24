"""Agent _SYSTEM_PROMPT 静态契约测试。

覆盖 D-003@v1: today guard。
"""


def test_system_prompt_contains_today_guard():
    from ellectric.llm.agent import _SYSTEM_PROMPT

    assert "2026-01-14" in _SYSTEM_PROMPT, "应提及数据集最新可用日"
    assert "今天" in _SYSTEM_PROMPT, "应提及'今天'规则"
    assert "实时" in _SYSTEM_PROMPT or "当前" in _SYSTEM_PROMPT, "应提及实时/当前规则"
    assert "历史" in _SYSTEM_PROMPT, "应说明数据是历史的"


def test_system_prompt_contains_thousands_separator_rule():
    from ellectric.llm.agent import _SYSTEM_PROMPT

    assert "编造" in _SYSTEM_PROMPT or "不编造" in _SYSTEM_PROMPT


def test_system_prompt_prioritizes_replay_context_and_preserves_domain_boundary():
    from ellectric.llm.agent import _SYSTEM_PROMPT

    for term in (
        "30天历史回放",
        "模拟价差值",
        "还原持仓",
        "当日回测基准价",
        "106天样本外稳定性评估",
        "Showcase Explainer",
    ):
        assert term in _SYSTEM_PROMPT
    assert "不得用离线报告替换" in _SYSTEM_PROMPT
    assert "人民币利润" in _SYSTEM_PROMPT
    assert "不提供投资或交易建议" in _SYSTEM_PROMPT
