# 论文查重程序（Paper Plagiarism Checking）

软件工程作业 —— 基于 TF-IDF + 余弦相似度的论文查重程序。

## 📁 项目结构

- [`3124004255/`](./3124004255/) —— 学号文件夹，包含完整代码、单元测试与项目说明
- [`PSP.md`](./PSP.md) —— PSP 时间记录表

## 🚀 快速开始

```bash
git clone https://github.com/MWQ111/paper-check.git
cd paper-check/3124004255
python main.py tests/test_data/orig.txt tests/test_data/orig_add.txt ans.txt
```

运行后输出：

```text
重复率: 0.67
```

同时生成 `ans.txt`，内容为 `0.67`。

> 本项目仅使用 Python 3 标准库，无需安装任何第三方依赖。

## 📖 详细文档

完整项目说明见 [`3124004255/README.md`](./3124004255/README.md)。
