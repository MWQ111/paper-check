# PSP 时间记录表

**项目**：论文查重程序
**姓名/学号**：马文青3124004255
**日期**：2026.9.14

---

## 一、预估时间表

| 阶段 | 预估耗时(min) |
| --- | ---: |
| **Planning** | |
| &nbsp;&nbsp;&nbsp;&nbsp;Estimate（需求理解与规模估算） | 20 |
| **Development** | |
| &nbsp;&nbsp;&nbsp;&nbsp;Analysis（需求分析） | 30 |
| &nbsp;&nbsp;&nbsp;&nbsp;Design Spec（设计规格说明） | 30 |
| &nbsp;&nbsp;&nbsp;&nbsp;Design Review（设计评审） | 20 |
| &nbsp;&nbsp;&nbsp;&nbsp;Coding Standard（编码规范确定） | 15 |
| &nbsp;&nbsp;&nbsp;&nbsp;Design（算法与模块设计） | 40 |
| &nbsp;&nbsp;&nbsp;&nbsp;Coding（编码实现） | 90 |
| &nbsp;&nbsp;&nbsp;&nbsp;Code Review（代码评审） | 30 |
| &nbsp;&nbsp;&nbsp;&nbsp;Test（单元测试与功能验证） | 40 |
| **Reporting** | |
| &nbsp;&nbsp;&nbsp;&nbsp;Test Report（测试报告） | 25 |
| &nbsp;&nbsp;&nbsp;&nbsp;Size Measurement（规模度量） | 15 |
| &nbsp;&nbsp;&nbsp;&nbsp;Postmortem（项目总结） | 25 |
| **合计** | **380** |

---

## 二、实际时间表

| 阶段 | 实际耗时(min) |
| --- | ---: |
| **Planning** | |
| &nbsp;&nbsp;&nbsp;&nbsp;Estimate（需求理解与规模估算） | 18 |
| **Development** | |
| &nbsp;&nbsp;&nbsp;&nbsp;Analysis（需求分析） | 28 |
| &nbsp;&nbsp;&nbsp;&nbsp;Design Spec（设计规格说明） | 32 |
| &nbsp;&nbsp;&nbsp;&nbsp;Design Review（设计评审） | 18 |
| &nbsp;&nbsp;&nbsp;&nbsp;Coding Standard（编码规范确定） | 12 |
| &nbsp;&nbsp;&nbsp;&nbsp;Design（算法与模块设计） | 45 |
| &nbsp;&nbsp;&nbsp;&nbsp;Coding（编码实现） | 100 |
| &nbsp;&nbsp;&nbsp;&nbsp;Code Review（代码评审） | 25 |
| &nbsp;&nbsp;&nbsp;&nbsp;Test（单元测试与功能验证） | 45 |
| **Reporting** | |
| &nbsp;&nbsp;&nbsp;&nbsp;Test Report（测试报告） | 28 |
| &nbsp;&nbsp;&nbsp;&nbsp;Size Measurement（规模度量） | 12 |
| &nbsp;&nbsp;&nbsp;&nbsp;Postmortem（项目总结） | 22 |
| **合计** | **385** |

---

## 三、预估与实际对比

| 阶段 | 预估耗时(min) | 实际耗时(min) | 偏差(min) |
| --- | ---: | ---: | ---: |
| Estimate | 20 | 18 | -2 |
| Analysis | 30 | 28 | -2 |
| Design Spec | 30 | 32 | +2 |
| Design Review | 20 | 18 | -2 |
| Coding Standard | 15 | 12 | -3 |
| Design | 40 | 45 | +5 |
| Coding | 90 | 100 | +10 |
| Code Review | 30 | 25 | -5 |
| Test | 40 | 45 | +5 |
| Test Report | 25 | 28 | +3 |
| Size Measurement | 15 | 12 | -3 |
| Postmortem | 25 | 22 | -3 |
| **合计** | **380** | **385** | **+5** |

---

## 四、规模度量（Size Measurement）

| 文件 | 总行数 | 有效代码行数 |
| --- | ---: | ---: |
| main.py | 239 | 178 |
| tests/test_similarity.py | 358 | 285 |
| **合计** | **597** | **463** |

其它交付物：README.md（218 行）、requirements.txt（12 行）、.gitignore（15 行）。

| 度量项 | 数值 |
| --- | ---: |
| 核心函数数量 | 8 个 |
| 单元测试用例数量 | 39 个 |
| 单元测试全部通过耗时 | 0.14 秒 |
| 长文本（10000 次重复）计算耗时 | 约 0.13 秒（限制 5 秒） |
| 样例重复率输出 | 0.67 |

---

## 五、项目总结（Postmortem）

### 做得好的地方

1. **算法选型合理**：TF-IDF + 余弦相似度在无需外部词库的前提下即可识别
   「星期天 → 周天」这类同义改写，中文 2-gram 显著提升了区分能力。
2. **性能远超要求**：长文本（22 万字符）计算仅需约 0.13 秒，远低于 5 秒上限；
   分词使用生成器惰性求值，内存占用很低。
3. **异常处理完备**：文件不存在、无权限、编码错误（UTF-8 回退 GBK）、
   参数数量错误均有明确处理，且不会向用户抛出未捕获的堆栈。
4. **测试覆盖充分**：39 个用例覆盖了清洗、分词、相似度边界、异常与性能，
   并包含基于真实样例文件的端到端验证。

### 遇到的问题与解决

1. **清洗与英文分词的冲突**：需求要求「清洗去除空白」，
   但英文依赖空格划分单词边界，若去除空白，`hello world` 会被合并为
   `helloworld`，无法按单词切分。
   **解决**：清洗阶段保留空白，仅去除标点；中文分词基于正则提取，
   空白会被自然忽略，不受影响。

2. **两文档 IDF 归零**：若使用未平滑的 `ln(N / df)`，
   两篇文档共有的词元因 `df = 2`、`N = 2` 会得到 `ln(1) = 0` 的权重，
   导致相似文本被误判为完全不相似。
   **解决**：改用平滑公式 `ln((N + 1) / (df + 1)) + 1`，
   共有词元权重为 1.0，独有词元权重约 1.41，区分度恢复正常。

3. **浮点精度**：完全相同文本的余弦相似度可能得到 `0.9999999999999999`
   而非精确的 `1.0`。**解决**：测试中使用 `assertAlmostEqual` 比较；
   输出格式化后为 `1.00`，不影响最终结果。

### 后续可改进的方向

1. 引入同义词词典，进一步提升同义改写的召回率。
2. 支持段落级/句子级定位，指出具体重复位置而非仅给出整体重复率。
3. 支持 PDF、DOCX 等格式的自动文本抽取。

---

