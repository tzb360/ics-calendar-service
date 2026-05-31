# 📅 ICS Calendar Service

一个基于 GitHub Actions + GitHub Pages 的 **ICS 日历订阅服务**，自动生成以下日历：

| 日历 | 内容 | 更新频率 | 订阅地址 |
|------|------|----------|----------|
| 🎉 中国法定节假日 | 春节/清明/劳动节/端午/中秋/国庆/元旦 + 调休上班 | 每天 08:00 | `holidays.ics` |
| ⚽ FIFA 世界杯赛程 | 小组赛 → 决赛完整赛程 | 每小时 | `worldcup.ics` |
| 🎮 CS2 顶级赛事 | Major/IEM/BLAST/ESL Pro League | 每小时 | `cs2.ics` |
| 📦 聚合日历 | 以上全部 | 自动聚合 | `all.ics` |

订阅地址格式：`https://<你的用户名>.github.io/<仓库名>/<文件名>.ics`

---

## ⚡ 快速开始

### 1. Fork 本仓库

点击右上角 Fork 按钮，将仓库 Fork 到你的 GitHub 账号下。

### 2. 启用 GitHub Actions

1. 进入你的 Fork 仓库 → **Settings** → **Actions** → **General**
2. 在 "Actions permissions" 中选择 **Allow all actions and reusable workflows**
3. 点击 **Save**

### 3. 启用 GitHub Pages

1. 进入 **Settings** → **Pages**
2. 在 "Build and deployment" → **Source** 中选择 **Deploy from a branch**
3. Branch 选择 **gh-pages** → **/(root)** → 点击 **Save**
4. 等待 1-2 分钟，GitHub Pages 会自动部署

> **注意**：gh-pages 分支会在第一次 Actions 运行后自动创建。你也可以手动触发一次 workflow：
> 进入 **Actions** → 选择任意 workflow → **Run workflow**

### 4. 手动触发首次构建

1. 进入 **Actions** 标签页
2. 选择 **Build All ICS (Aggregated)**
3. 点击 **Run workflow** → **Run workflow**
4. 等待构建完成（约 2-3 分钟）

### 5. 获取订阅地址

构建完成后，你的订阅地址为：

```
https://<你的用户名>.github.io/<仓库名>/holidays.ics
https://<你的用户名>.github.io/<仓库名>/worldcup.ics
https://<你的用户名>.github.io/<仓库名>/cs2.ics
https://<你的用户名>.github.io/<仓库名>/all.ics
```

---

## 📱 设备订阅教程

### iPhone / iPad / Mac (Apple Calendar)

**方法一：直接订阅（推荐）**

1. 打开 **设置** → **日历** → **账户** → **添加账户** → **其他** → **添加已订阅的日历**
2. 输入订阅地址（例如 `https://你的用户名.github.io/仓库名/holidays.ics`）
3. 点击 **下一步** → **存储**
4. 打开「日历」App 即可看到

**方法二：Safari 一键订阅**

1. 在 Safari 中打开订阅地址
2. 系统会自动弹出「订阅日历」提示
3. 点击 **订阅** 即可

### Android (Google Calendar)

> Google Calendar **不支持直接订阅 ICS 链接**，需要通过以下方式间接导入：

**方法一：Google Calendar 网页版订阅**

1. 在电脑浏览器打开 [calendar.google.com](https://calendar.google.com)
2. 左侧 **其他日历** → 点击 **+** → **通过网址添加**
3. 输入订阅地址 → 点击 **添加日历**
4. 日历会自动同步到你的 Android 设备

**方法二：使用第三方日历 App**

推荐以下支持 ICS 订阅的 Android 日历 App：

| App 名称 | 下载方式 |
|----------|----------|
| **ICSx⁵** | [Google Play](https://play.google.com/store/apps/details?id=at.bitfire.icsdroid) |
| **OneCalendar** | [Google Play](https://play.google.com/store/apps/details?id=com.xcritic.onecalendar) |
| **aCalendar** | [Google Play](https://play.google.com/store/apps/details?id=org.withouthat.acalendar) |

以 ICSx⁵ 为例：

1. 安装并打开 ICSx⁵
2. 点击 **+** → 输入订阅地址
3. 选择同步频率（建议每 6-12 小时）
4. 日历会自动出现在系统日历中

### Outlook (桌面版 & 网页版)

**Outlook 网页版 (outlook.live.com / outlook.office.com)：**

1. 打开 Outlook 日历
2. 左侧栏点击 **添加日历** → **从 Internet 订阅**
3. 输入订阅地址
4. 输入日历名称 → 点击 **导入**

**Outlook 桌面版 (Windows / Mac)：**

1. 打开 Outlook → 切换到日历视图
2. 点击 **文件** → **账户设置** → **账户设置**
3. 选择 **Internet 日历** 标签 → **新建**
4. 输入订阅地址 → **添加**
5. 设置更新频率（建议每次启动时更新）

### Thunderbird (桌面端)

1. 打开 Thunderbird → 切换到日历视图
2. 点击 **新建日历** → **在网络上**
3. 输入订阅地址
4. 选择 **离线支持** 和更新频率
5. 点击 **订阅**

---

## 🔧 自定义新增赛事

### 添加新的 CS2 赛事

编辑 `src/cs2_fetcher.py` 中的 `TARGET_EVENTS` 列表：

```python
TARGET_EVENTS = [
    {"keywords": ["major"], "name": "CS2 Major", "priority": 1},
    {"keywords": ["iem cologne"], "name": "IEM Cologne", "priority": 2},
    {"keywords": ["iem katowice"], "name": "IEM Katowice", "priority": 3},
    # 👇 在这里添加新赛事
    {"keywords": ["pgl"], "name": "PGL", "priority": 5},
    {"keywords": ["thunderpick"], "name": "Thunderpick World Championship", "priority": 7},
]
```

- `keywords`: 用于匹配 HLTV 赛事名称的关键词（不区分大小写）
- `name`: 在日历中显示的名称
- `priority`: 优先级（数字越小优先级越高）

### 添加全新的日历类型

1. 在 `src/` 下创建新的 fetcher 模块（参考 `holidays_fetcher.py`）

```python
# src/my_calendar_fetcher.py
from src.ics_generator import ICSEvent, ICSGenerator, generate_event_uid

def build_my_calendar_ics(output_path: str) -> str:
    events = []
    # ... 构建事件列表 ...
    generator = ICSGenerator("my_calendar")
    generator.add_events(events)
    generator.save(output_path)
    return output_path
```

2. 在 `main.py` 中注册新模块
3. 创建对应的 GitHub Actions workflow（`.github/workflows/my_calendar.yml`）
4. 在 `src/ics_generator.py` 的 `X_WR_CALNAME_MAP` 中添加日历名称

---

## 📁 项目结构

```
ics-calendar-service/
├── .github/
│   └── workflows/
│       ├── holidays.yml       # 节假日 (每天 08:00)
│       ├── worldcup.yml       # 世界杯 (每小时)
│       ├── cs2.yml            # CS2 赛事 (每小时)
│       └── build-all.yml      # 聚合构建
├── src/
│   ├── __init__.py
│   ├── ics_generator.py      # ICS 文件生成引擎
│   ├── holidays_fetcher.py   # 中国节假日数据抓取
│   ├── worldcup_fetcher.py   # FIFA 世界杯数据抓取
│   └── cs2_fetcher.py        # CS2 赛事数据抓取
├── output/                    # 生成的 .ics 文件 (不提交到 Git)
├── main.py                    # 主入口
├── requirements.txt           # Python 依赖
├── .gitignore
└── README.md
```

---

## 🛠 本地开发

```bash
# 克隆仓库
git clone <你的仓库地址>
cd ics-calendar-service

# 安装依赖
pip install -r requirements.txt --break-system-packages

# 生成节假日日历
python main.py holidays

# 生成世界杯赛程
python main.py worldcup

# 生成 CS2 赛事
python main.py cs2

# 生成全部 + 聚合版
python main.py all

# 生成的文件在 output/ 目录下
ls -la output/
```

---

## 📊 数据来源

| 日历 | 数据源 | 备用源 |
|------|--------|--------|
| 中国节假日 | `chinese-calendar` Python 包 | GitHub holiday-cn 仓库 |
| FIFA 世界杯 | FIFA 官方 API | FIFA 网站爬取 → 公开 API → 内置框架 |
| CS2 赛事 | HLTV.org 网站爬取 | HLTV 搜索接口 |

所有数据源均为**免费公开数据**，不依赖任何付费 API。

---

## 🔒 GitHub Pages 配置步骤

### 方法一：自动部署（推荐，已配置）

本仓库使用 `peaceiris/actions-gh-pages` 自动将 `output/` 目录部署到 `gh-pages` 分支。你只需要：

1. 确保 GitHub Pages Source 设置为 **Deploy from a branch** → **gh-pages** → **/(root)**
2. 首次手动触发一次 workflow

### 方法二：自定义域名

1. 在 `output/` 目录下创建 `CNAME` 文件：

```bash
echo "calendar.yourdomain.com" > output/CNAME
```

2. 在 DNS 服务商添加 CNAME 记录：
   - 类型：`CNAME`
   - 名称：`calendar`
   - 值：`你的用户名.github.io`

3. 在 GitHub Pages 设置中启用 **Enforce HTTPS**

---

## 📝 ICS 规范说明

生成的 `.ics` 文件完全符合 RFC 5545 标准：

- 使用 `VERSION:2.0`
- 包含 `VTIMEZONE` 定义 (Asia/Shanghai)
- 所有事件包含 `SUMMARY`、`DESCRIPTION`、`DTSTART`、`DTEND`、`UID`、`LAST-MODIFIED`
- `X-PUBLISHED-TTL:PT1H` 建议客户端每小时检查更新

兼容性：

- ✅ Apple Calendar (iOS / iPadOS / macOS)
- ✅ Google Calendar (网页版、Android 同步)
- ✅ Outlook (网页版、桌面版)
- ✅ Thunderbird
- ✅ 所有支持 ICS 订阅的日历应用

---

## ❓ 常见问题

**Q: 为什么 Google Calendar Android App 不能直接订阅？**

A: Google 在 Android 端不直接支持 ICS 订阅。请使用网页版 Google Calendar 订阅，或安装第三方日历 App（如 ICSx⁵）。

**Q: 日历多久更新一次？**

A: 节假日每天更新一次；世界杯和 CS2 赛事每小时更新一次。订阅客户端会按 `X-PUBLISHED-TTL` 建议的频率（每小时）刷新。

**Q: 如果数据源无法访问怎么办？**

A: 系统会自动尝试备用数据源。如果所有外部源都不可用，World Cup 使用内置占位框架（待数据恢复后自动更新），CS2 和 Holidays 会保留上次成功获取的数据。

**Q: 如何添加新的年限节假日？**

A: 无需手动操作。`chinese-calendar` 包每年会在国务院发布新安排后更新，系统每天自动检查，检测到新数据后会自动生成更新后的 ICS。

**Q: 如何知道数据是否更新了？**

A: 查看 GitHub Actions 运行历史（Actions 标签页），每次成功提交新 ICS 文件都意味着检测到了数据变化。

---

## 📄 License

MIT License - 自由使用、修改、分发。
