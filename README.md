# Judge 合理性人工标注

用于审核 Haiku-train step159 实验中 Adversary 推测与 Judge 评分是否合理的中文标注网页。
本仓库不是编程题 HumanEval benchmark。

## 直接使用

下载本仓库，用浏览器打开
`report_figures/data/human_eval/web_app/human_eval_standalone.html`。
该文件内嵌全部任务数据，无需安装依赖或启动服务器，也可单独发给标注员。

填写标注员 ID，选择 EIL 或 MIU，加载任务后逐条标注。所有答案均为
`1 = 合理`、`0 = 不合理`，不要求重新打指标分数。
进度按“标注员 ID + 任务组”保存在当前浏览器中；请分别导出两组 JSON 结果回传。

- EIL：60 条，每条审核 Adversary 推测、Leakage 评分和 Utility 评分，共 180 个判断。
- MIU：60 条，每条审核 Faithfulness 状态与评分，共 60 个判断。
- 每组包含 3 个领域，每个领域 20 条；全部完成共 120 条、240 个二元判断。

## 本地服务器模式

在仓库根目录执行（仅需 Python 3 标准库）：

```bash
python3 report_figures/data/human_eval/web_app/server.py --host 127.0.0.1 --port 8765
```

浏览器访问 `http://127.0.0.1:8765/`。服务器模式自动保存到
`report_figures/data/human_eval/web_app/responses/`，也支持导出 JSON。
此服务没有身份认证，建议仅在本机或可信网络中使用。

## 文件与构建

- `report_figures/data/human_eval/web_app/index.html`：页面源码。
- `report_figures/data/human_eval/web_app/server.py`：本地服务端。
- `report_figures/data/human_eval/*_blinded_tasks.json`：已经抽样好的任务数据。
- `report_figures/data/human_eval/web_app/build_standalone.py`：将页面与 JSON 打包为单文件。

修改页面或任务 JSON 后，在仓库根目录重新生成单文件：

```bash
python3 report_figures/data/human_eval/web_app/build_standalone.py
```

`build_human_eval_tasks.py` 保留用于追溯抽样逻辑，需要原项目的实验原始文件及
`eil/data/dataset/EIL-v2/test.jsonl`、`miu/data/dataset/MIU-v2/test.jsonl`。
这些原始输入不包含在本仓库中；正常使用网页或重新打包单文件不需要它们。

## 来源

提取自 `Simona0212/loyal_agent_docker` 的提交 `9e5de93`
（2026-09-10），保留原有 `report_figures/data/human_eval/` 目录结构。
本仓库不包含原项目的环境变量、密钥、训练产物或已填写的标注结果。
