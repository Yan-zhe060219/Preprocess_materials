# AI 辅助学习资料预处理工具

这是一个面向 AI 阅读与资料整理场景的本地预处理工具，用于优化 PDF 和图片的读取效果。你可以在把学习资料交给大模型、OCR 工具或知识库系统之前，先完成压缩、增强和拆分处理，减少无效信息干扰，提升后续识别与阅读体验。

## 功能简介

### 1. 图片转 WebP

将常见图片格式批量转换为 WebP，在尽量保留清晰度的前提下减小文件体积，方便归档、传输和交给 AI 工具处理。

### 2. OCR 图像增强

对图片执行灰度化、降噪、对比度增强和二值化等预处理，提高扫描件、截图和拍照资料的 OCR 识别效果。

### 3. PDF 拆分与转图

- 按页数拆分长 PDF，便于分段处理和上传。
- 将 PDF 页面导出为图片。
- 支持按批次拼接成长图，方便连续阅读和内容整理。

## 新特性：settings.json 配置文件

项目已加入同级目录下的 `settings.json` 配置文件，支持在不修改代码的情况下直接调整核心参数。

你可以在 `settings.json` 中自定义以下配置：

```json
{
    "WEBP_QUALITY": 85,
    "SPLIT_MAX_PAGES": 10,
    "PDF_DPI": 200,
    "JOIN_CHUNK_SIZE": 10
}
```

这些参数分别用于控制：

- `WEBP_QUALITY`：图片转 WebP 时的压缩质量
- `SPLIT_MAX_PAGES`：PDF 拆分时每个文件的最大页数
- `PDF_DPI`：PDF 转图片时的导出 DPI
- `JOIN_CHUNK_SIZE`：拼接长图时每张图最多包含的页数

程序启动时会自动加载该配置文件；如果文件不存在、内容损坏或参数不合法，脚本会自动重建默认配置，因此日常使用时无需手动改动源码。

## 运行指南

### 1. 环境要求

建议使用 Python 3.10 及以上版本。

### 2. 安装依赖

在项目目录中执行：

```bash
pip install -r requirements.txt
```

### 3. 启动脚本

执行以下命令启动工具：

```bash
python preprocess_materials.py
```

### 4. 按菜单选择功能

脚本启动后会进入交互式终端菜单，你可以根据提示选择对应功能并输入路径、输出目录或参数：

```text
1. 批量转换图片为 WebP
2. 批量增强图片 (OCR 预处理)
3. 拆分长 PDF
4. PDF 转图片 (并可选拼接长图)
0. 退出
```

## Windows 打包说明

如果你准备把脚本打包为 Windows 单文件 `.exe`，建议使用 PyInstaller，并保留控制台窗口，因为当前工具依赖交互式菜单、`input()`、日志输出和 `tqdm` 进度条。

### 1. 安装 PyInstaller

```bash
pip install pyinstaller
```

### 2. 快速验证打包命令

如果你已经准备好了自定义图标文件，例如 `app.ico`，可以在项目目录执行：

```powershell
pyinstaller --noconfirm --clean --onefile --console --name preprocess_materials --icon .\app.ico --collect-all cv2 --collect-all fitz .\preprocess_materials.py
```

打包完成后，生成的 EXE 位于：

```text
dist\preprocess_materials.exe
```

### 3. 推荐的正式打包方式

项目中已经提供了 `preprocess_materials.spec`，其中包含了 `cv2` 和 `fitz` 的依赖收集规则。正式构建建议直接执行：

```powershell
pyinstaller --noconfirm --clean .\preprocess_materials.spec
```

如果项目目录下存在 `app.ico`，该图标会自动用于 EXE；如果暂时没有图标文件，`.spec` 也能正常构建，只是不会替换程序图标。

### 4. 常见坑点与处理方法

- `ImportError: DLL load failed while importing cv2`
  说明 OpenCV 的动态库没有被完整收集。当前 `.spec` 已通过 `collect_all("cv2")` 处理这一问题。
- `ModuleNotFoundError: No module named 'fitz'`
  说明 PyMuPDF 的隐藏依赖或二进制文件没有被打进去。当前 `.spec` 已通过 `collect_all("fitz")` 处理。
- EXE 双击后闪退
  不要使用 `--windowed` 或 `--noconsole`，本项目必须保留 `--console`。
- `settings.json` 或 `app.log` 没有出现在 EXE 同级目录
  本项目已兼容 PyInstaller 冻结环境，打包后的配置文件和日志会优先使用 EXE 所在目录。
- 修改 `.spec` 后重新打包没有生效
  重新构建时保留 `--clean`；必要时手动删除 `build/` 和 `dist/` 后再打包。
- 图标没有生效
  请确认图标文件是标准 `.ico` 格式，并命名为 `app.ico` 或同步修改命令中的图标路径。

## 项目说明

- `settings.json` 位于脚本同级目录，用于统一管理默认参数。
- `test/` 用于存放开发阶段测试素材，已在 `.gitignore` 中忽略。
- 运行后生成的 `webp_output/`、`ocr_enhanced/`、`pdf_split/`、`pdf_images/` 也已默认忽略。
- 打包后的 `settings.json` 和 `app.log` 会优先写入 EXE 所在目录，方便直接修改配置和查看日志。

## GitHub 上传说明

当前仓库已经调整为适合上传“源代码 + 已打包 EXE”的形式：

- 会保留源码文件，例如 `preprocess_materials.py`、`preprocess_materials.spec`、`requirements.txt`、`README.md`、`.gitignore`、`settings.json`
- 会保留 `dist/` 目录中的 `.exe` 文件
- 会忽略打包中间产物和运行产生的临时文件，例如 `build/`、`__pycache__/`、`test/`、日志文件、处理输出目录，以及 `dist/` 中除 `.exe` 以外的其他文件

如果你之前已经把日志文件提交过，提交前可以执行：

```bash
git rm --cached app.log
```

如果 `dist/` 里已经生成了新的可执行文件，提交时确认把它一起加入版本控制即可，例如：

```bash
git add preprocess_materials.py preprocess_materials.spec settings.json requirements.txt README.md .gitignore dist\preprocess_materials.exe
```
