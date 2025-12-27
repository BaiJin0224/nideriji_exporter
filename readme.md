
# Nideriji Diary Exporter（你的日记导出工具）

一个用于 **登录 nideriji.cn**，批量导出你的日记正文与图片，并生成可离线浏览的 **HTML（日历导航 + 图文混排）** 的小工具。

> ✅ 目标：把账号内的日记数据备份到本地（`dairies.txt` / `recovery_images/` / `dairies.html`）  
> ⚠️ 说明：本项目仅用于导出你自己账号的数据，请遵守网站服务条款与当地法律法规。

---

## 功能

- **自动登录**获取 token，并从 `/api/v2/sync/` 获取：
  - 全部日记 ID 列表
  - 全部图片 ID 列表
- **导出日记正文**到 `dairies.txt`
  - 每条日记带 `DiaryID / Date / TS`
- **下载图片**到 `images/`
  - 根据响应头尽量判断扩展名
  - 未知类型会保存为 `.bin`
- **恢复图片格式**
  - 将 `images/*.bin` 通过 magic number 识别为真实格式，输出到 `recovery_images/`
  - 无法识别或疑似错误页的文件会放到 `recovery_images/_non_image/`
- **生成离线 HTML**
  - 从 `dairies.txt` 解析正文
  - 将正文中的 `[图123]` 替换为对应图片
  - 未找到图片则显示“图片已丢失（图123）”
  - 日记内容居中排版 + 时间戳“胶囊标签”
  - 右下角悬浮日历：有日记的日期变色可点击跳转

---

## 目录结构

建议将项目放到一个独立目录中运行：

````
.
├── main.py
├── fetch_data.py
├── recovery_image_ext.py
├── export_as_html.py
（以下为运行后生成）
├── dairies.txt
├── dairies.html
├── images/
└── recovery_images/
    └── _non_image/

````

---

## 环境要求

- Python **3.11+**（因为我只测试了这个版本）
- 依赖库：仅 `requests`

安装依赖：

```bash
  pip install requests
````

---

## 配置账号密码（两种方式）

### 方式 A：使用环境变量（推荐）

#### Windows（PowerShell 或 CMD）

```bat
setx NIDERIJI_EMAIL "your@email.com"
setx NIDERIJI_PASSWORD "your_password"
```

> `setx` 写入后需要 **重新打开终端** 才会生效。

然后运行：

```bash
    python main.py
```

### 方式 B：在 `main.py` 中写全局变量（不推荐）

打开 `main.py`，修改：

```python
EMAIL = "your@email.com"
PASSWORD = "your_password"
```

如果 `EMAIL/PASSWORD` 在代码里有值，则不会再读取环境变量。

> 注意：不要把真实账号密码提交到公开仓库。

---

## 一键运行

```bash
    python main.py
```

运行完成后会生成：

* `dairies.txt`：全部日记正文
* `images/`：下载的原始图片（可能包含 `.bin`）
* `recovery_images/`：识别后的图片（jpg/png/webp/...）
* `dairies.html`：离线可浏览页面（含悬浮日历导航）

---

## 输出说明

### 1) `dairies.txt` 格式

每条日记以 header 开头：

```
=== DiaryID: 33420496 | Date: 2024-12-04 | TS: 1733306007 ===
Title: （可选）
正文...
[图373]
...
```

其中正文引用图片的格式为：

* `[图123]`：表示图片 ID 为 123

### 2) 图片恢复规则

* 若图片是 `.bin`，`recovery_image_ext.py` 会读取文件开头 bytes 并识别：

  * jpg/png/webp/gif/bmp/tiff/ico
* 如果识别失败或看起来像 HTML/JSON 错误页：

  * 会被归类到 `recovery_images/_non_image/` 方便你排查。

### 3) `dairies.html`

* 将正文中的 `[图123]` 替换为图片展示
* 若缺图：显示“图片已丢失（图123）”
* 右下角悬浮日历：

  * 有日记的日期标红可点击
  * 点击跳转到对应日期的第一篇日记并高亮

---

## 常见问题（FAQ）

### Q1：为什么有些图片下载下来是 `.bin`？

服务端可能没有返回明确的 `Content-Type`，或者返回了通用类型。
工具会先保存为 `.bin`，再通过 magic number 恢复真实格式。

### Q2：为什么有些 `.bin` 识别失败？

可能是：

* 不是图片（例如接口错误页/鉴权失败返回的 HTML 或 JSON）
* 文件损坏/下载不完整

这些文件会被归类到 `recovery_images/_non_image/` 方便你排查。

### Q3：日记接口看起来每次只返回一条？

`/api/diary/all_by_ids/{userid}/` 在某些情况下可能不支持一次请求多个 `diary_ids`。
工具会自动探测，如果不支持则自动降级为逐条抓取。

---

## 免责声明

* 本项目仅用于导出 **你本人账号** 的数据备份。
* 请遵守 nideriji.cn 的服务条款与相关法律法规。
* 请勿将你的 token / 密码 / 导出的隐私内容上传到公开仓库或公开分享。

---

## License

MIT License.
