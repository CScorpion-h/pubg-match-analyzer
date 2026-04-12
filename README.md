# PUBG Match Analyzer

一个基于 Streamlit 的 PUBG 对局分析工具，用于识别共同对局、查看对局详情，并导出对局结果。

## 当前功能

- 根据玩家昵称识别共同出现的自定义房对局
- 查看单场对局的基础信息、玩家明细和队伍汇总
- 导出 `MatchOverview`、`PlayerStats`、`TeamSummary`
- 本地保存基础设置：`API Key`、`平台`、`最近对局窗口`

## 当前规则

- 主输入字段是 `玩家昵称`
- 候选对局命中规则固定为：`至少 2 名输入玩家共同出现`
- 自定义房判定优先使用 `matchType = custom`
- `gameMode` 只用于分类和展示，不作为唯一保留条件

## 项目结构

```text
pubg_match_analyzer/
├─ app.py
├─ pubg_match_analyzer/
│  ├─ configs/
│  ├─ core/
│  ├─ pages/
│  ├─ services/
│  └─ ui/
├─ .streamlit/
├─ README.md
├─ GITHUB_UPLOAD_GUIDE.md
└─ requirements.txt
```

目录说明：

- `app.py`：Streamlit 入口
- `pubg_match_analyzer/configs/`：本地配置示例
- `pubg_match_analyzer/core/`：常量、数据模型、会话状态
- `pubg_match_analyzer/pages/`：页面脚本
- `pubg_match_analyzer/services/`：PUBG API 读取、match 解析、导出逻辑
- `pubg_match_analyzer/ui/`：样式和界面辅助

## 运行方式

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## 本地配置

程序运行时会自动生成本地配置文件：

- `pubg_match_analyzer/configs/local_settings.json`



本地配置文件用于保存：

- `PUBG API Key`
- `平台`
- `最近对局窗口`


