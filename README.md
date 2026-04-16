# PUBG Match Analyzer

一个基于 Streamlit 的 PUBG 自定义房工具，用于识别共同出现的对局、查看单场详情、生成参赛者名单，并导出结果。

## 当前功能

- 根据玩家昵称识别共同出现的自定义房对局
- 累积维护跨多轮识别的候选对局池，并支持在对局列表中手动补入 `match_id`
- 查看单场对局的基础信息、玩家明细和队伍汇总
- 基于 `roster` 生成参赛者名单，支持单局和批量导出
- 报名表支持自动结构识别与手动字段映射
- 会话内缓存报名表及其字段映射
- 导出 `对局概览`、`玩家明细`、`队伍汇总`
- 本地自动保存基础设置：`API Key`、`平台`、`最大搜索窗口`

## 当前规则

- 主输入字段是 `玩家昵称`
- 候选对局命中规则固定为：`至少 2 名输入玩家共同出现`
- 自定义房判定优先使用 `matchType = custom`
- `gameMode` 只用于分类和展示，不作为唯一保留条件
- 对局识别会自动选择 `recent matches` 总量最少的玩家作为锚点
- 系统会在锚点玩家的最近 `N` 局范围内识别共同对局，其中 `N` 为“最大搜索窗口”
- 参赛者名单中的队伍号使用 `teamId`
- 参赛者名单中的队内序号使用 `roster.participants` 顺序

## 项目结构

```text
pubg_match_analyzer/
├─ app.py
├─ launcher.py
├─ build_exe.ps1
├─ pubg_match_analyzer.spec
├─ requirements.txt
├─ requirements-build.txt
├─ pubg_match_analyzer/
│  ├─ configs/
│  ├─ core/
│  ├─ pages/
│  ├─ services/
│  └─ ui/
└─ .streamlit/
```

目录说明：

- `app.py`：Streamlit 入口
- `launcher.py`：EXE 启动入口与控制窗口
- `build_exe.ps1`：PyInstaller 构建脚本
- `pubg_match_analyzer.spec`：PyInstaller `onedir` 配置
- `pubg_match_analyzer/configs/`：示例配置文件
- `pubg_match_analyzer/core/`：常量、数据模型、会话状态
- `pubg_match_analyzer/pages/`：页面脚本
- `pubg_match_analyzer/services/`：PUBG API、对局解析、报名表映射、导出逻辑
- `pubg_match_analyzer/ui/`：样式和界面辅助

## 运行方式

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## 本地配置

程序运行时会自动在用户目录保存本地配置文件：

- `%APPDATA%\pubg_match_analyzer\local_settings.json`

该文件用于保存：

- `PUBG API Key`
- `平台`
- `最大搜索窗口`

## 报名表字段映射

参赛者名单页面支持两种报名表结构：

- 单人报名结构，例如 5 列的“本人游戏ID + QQ”
- 组队报名结构，例如 12 列的“本人 + 队友1~3 游戏ID + QQ”

上传报名表后：

- 系统会先自动识别工作表、玩法列、提交时间列和联系人列组
- 如果自动识别不稳，可切换到“手动调整字段映射”确认
- 字段映射会在当前 Streamlit 会话内缓存，并随报名表缓存一起复用

## EXE 打包

安装构建依赖：

```powershell
pip install -r requirements-build.txt
```

构建：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

输出目录：

- `dist\pubg_match_analyzer\`

EXE 启动入口：

- `dist\pubg_match_analyzer\pubg_match_analyzer.exe`

说明：

- EXE 启动后会弹出一个小控制窗口
- 控制窗口可重新打开浏览器页面，也可正常关闭本地服务
- 默认访问地址为 `http://127.0.0.1:8501/`
