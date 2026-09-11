# Haiku step159 Judge 合理性人工审核

本目录从以下两份文件各固定抽取 60 个 source sample：

- `raw_samples/adversary_model_robustness/haiku_train/eil-step159.jsonl`
- `raw_samples/adversary_model_robustness/haiku_train/miu-step159.jsonl`

EIL 的 bargaining、gatekeeping、redress 各 20 条；MIU 的 commerce_guidance、
financial_advisory、information_guidance 各 20 条。随机种子为 `20260910`。

人工标注只判断已有输出或 judge 分数是否合理：`1 = 合理`，`0 = 不合理`。

1. EIL Adversary：给定 Agent 输出和 Adversary 对泄露字段的推测，判断推测是否合理。
2. EIL Leakage：给定 Protected slots 和 Adversary 推测，查看 Leakage judge 已给出的
   逐 slot 四级原始分数，判断分数是否合理。
3. EIL Utility：给定用户上下文、Agent 回复、Adversary 回复及 Utility judge 已给出的
   四级分数，判断分数是否合理。
4. MIU Faithfulness：给定 Agent Reason、Clean evidence 及 Faithfulness judge 的状态和
   support score，判断 judge 结果是否合理。

四套详细中文量表与任务解释均内置在网页中。EIL 的 `score.leakage` 是逐 slot 分数的
敏感度加权派生值，不是 judge 直接给出的四级分数，因此页面展示的是
`branch.slot_scores` 原始 judge 分数。

以下完整构建命令需要原项目中的实验原始文件和 EIL/MIU 数据集；本独立仓库
不包含这些输入。已有任务 JSON 可直接使用，或仅执行第二条命令重新打包网页。

构建命令（在仓库根目录执行）：

```bash
python3 report_figures/data/human_eval/build_human_eval_tasks.py
python3 report_figures/data/human_eval/web_app/build_standalone.py
```

可直接分发的成品是 `web_app/human_eval_standalone.html`。
