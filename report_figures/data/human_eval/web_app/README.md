# Judge 合理性人工标注网页

任务数据来自 Haiku-train step19：EIL 与 MIU 各固定抽取 60 个 source sample，
每个 family domain 各 20 个。标注员直接查看已有 judge 分数或状态，只填写
`1 = 合理`、`0 = 不合理`，不重新填写四级指标分数。

- EIL：每条审核 Adversary 推测、Leakage judge 原始逐 protected-slot 分数、
  Utility judge 分数，共三个 0/1。
- MIU：每条查看 Agent Reason、Clean evidence、Faithfulness judge 状态与分数，
  填写一个 0/1。

## 无服务器单文件（推荐分发）

直接把 `human_eval_standalone.html` 发给标注员。浏览器会按“标注员 ID + 任务组”
自动保存进度，完成后点击“导出结果”回传 JSON。

重新生成数据及单文件（从仓库根目录开始；重新抽样需要原项目的原始输入，
本独立仓库不包含这些输入，仅重新打包时跳过 `build_human_eval_tasks.py`）：

```bash
cd report_figures/data/human_eval
python3 build_human_eval_tasks.py
python3 web_app/build_standalone.py
```

## 本地服务器模式

```bash
cd report_figures/data/human_eval
python3 web_app/server.py --host 0.0.0.0 --port 8765
```

访问 `http://服务器地址:8765/`。服务器模式将结果自动保存到
`web_app/responses/`，也支持手动导出。
