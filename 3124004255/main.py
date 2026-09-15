#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""论文查重程序入口。

采用 TF-IDF 与余弦相似度算法，比较原文与抄袭版论文的重复率，
并将结果以两位小数的形式写入答案文件。

命令行用法::

    python main.py <原文文件> <抄袭版论文文件> <答案文件>

示例（原文与抄袭版论文分别位于 orig.txt 与 copy.txt）::

    python main.py orig.txt copy.txt ans.txt
"""

import math
import re
import sys
from collections import Counter

# 清洗规则：保留中文字符、英文字母、数字与空白，其余（标点、符号等）全部去除。
# 空白必须保留：英文依赖空格划分单词边界，若一并去除，
# "hello world" 会被合并为 "helloworld" 而无法按单词切分。
CLEAN_PATTERN = re.compile(r'[^一-鿿a-zA-Z0-9\s]')

# 英文单词与数字串：按整词切分
WORD_PATTERN = re.compile(r'[a-z]+|[0-9]+')

# 中文字符：逐字切分
CHINESE_PATTERN = re.compile(r'[一-鿿]')

# 参与比较的文档数量，用于计算 IDF
DOCUMENT_COUNT = 2

# 参数数量错误时的退出码
EXIT_ARGUMENT_ERROR = 2


def read_file(file_path):
    """读取文本文件内容，编码错误时回退到 GBK 重试。

    Args:
        file_path: 待读取文件的路径。

    Returns:
        str: 文件解码后的文本内容。

    Raises:
        FileNotFoundError: 文件不存在。
        PermissionError: 没有读取权限。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as handle:
            return handle.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='gbk') as handle:
            return handle.read()


def clean_text(text):
    """清洗文本，去除标点与符号，只保留中文、英文字母、数字和空白。

    英文字母统一转为小写。空白字符予以保留，因为英文依赖空格划分单词边界；
    中文分词基于正则提取，空白会被自然忽略，因此保留空白不影响中文切分。

    Args:
        text: 原始文本。

    Returns:
        str: 去除标点后的文本，英文字母已统一转为小写。
    """
    return CLEAN_PATTERN.sub('', text).lower()


def tokenize(text):
    """将已清洗的文本切分为词元序列。

    切分策略：

    1. 英文与数字按整词切分；
    2. 中文按单字切分；
    3. 中文补充相邻两字的 2-gram，以提升中文短语的区分能力。

    全部词元通过生成器惰性产出，无需一次性构造中间列表，
    在长文本场景下可显著降低内存占用。

    Args:
        text: 已清洗的文本。

    Yields:
        str: 切分后的词元。
    """
    for word in WORD_PATTERN.findall(text):
        yield word

    previous_char = None
    for match in CHINESE_PATTERN.finditer(text):
        char = match.group()
        yield char
        if previous_char is not None:
            yield previous_char + char
        previous_char = char


def build_tfidf_vector(tokens, idf):
    """构建单篇文档的 TF-IDF 向量。

    词频采用归一化词频（词出现次数 / 文档词元总数），
    IDF 由参与比较的两篇文档共同计算后传入。

    Args:
        tokens: 单篇文档的词元可迭代对象。
        idf: 词元到 IDF 值的映射。

    Returns:
        dict: 词元到 TF-IDF 权重的映射；文档无有效词元时返回空字典。
    """
    counts = Counter(tokens)
    total_count = sum(counts.values())
    if total_count == 0:
        return {}
    return {
        token: (count / total_count) * idf.get(token, 0.0)
        for token, count in counts.items()
    }


def cosine_similarity(vector_a, vector_b):
    """计算两个 TF-IDF 向量的余弦相似度。

    相似度定义为 ``dot / (|A| * |B|)``。

    Args:
        vector_a: 第一个向量，词元到权重的映射。
        vector_b: 第二个向量，词元到权重的映射。

    Returns:
        float: 余弦相似度，取值区间为 [0.0, 1.0]；任一向量为空时返回 0.0。
    """
    if not vector_a or not vector_b:
        return 0.0

    # 余弦相似度具有对称性，遍历较短向量可减少查表次数
    if len(vector_a) > len(vector_b):
        vector_a, vector_b = vector_b, vector_a

    dot_product = sum(
        weight * vector_b.get(token, 0.0)
        for token, weight in vector_a.items()
    )
    if dot_product == 0.0:
        return 0.0

    norm_a = math.sqrt(sum(weight * weight for weight in vector_a.values()))
    norm_b = math.sqrt(sum(weight * weight for weight in vector_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def calculate_similarity(orig_text, copy_text):
    """计算原文与抄袭版论文之间的重复率。

    Args:
        orig_text: 原文内容。
        copy_text: 抄袭版论文内容。

    Returns:
        float: 重复率，取值区间为 [0.0, 1.0]。
    """
    orig_tokens = list(tokenize(clean_text(orig_text)))
    copy_tokens = list(tokenize(clean_text(copy_text)))

    # 双文档 IDF：对词频做平滑，避免两篇文档共有的词元权重被归零
    document_frequency = Counter(set(orig_tokens))
    document_frequency.update(set(copy_tokens))
    idf = {
        token: math.log((DOCUMENT_COUNT + 1) / (frequency + 1)) + 1.0
        for token, frequency in document_frequency.items()
    }

    orig_vector = build_tfidf_vector(orig_tokens, idf)
    copy_vector = build_tfidf_vector(copy_tokens, idf)
    return cosine_similarity(orig_vector, copy_vector)


def write_answer(file_path, similarity):
    """将重复率以两位小数的格式写入答案文件。

    Args:
        file_path: 答案文件路径。
        similarity: 重复率，取值区间为 [0.0, 1.0]。

    Raises:
        PermissionError: 没有写入权限。
    """
    with open(file_path, 'w', encoding='utf-8') as handle:
        handle.write('{0:.2f}'.format(similarity))


def main(argv=None):
    """程序入口：解析命令行参数，计算重复率并写入答案文件。

    Args:
        argv: 命令行参数列表（不含程序名），默认取 ``sys.argv[1:]``。

    Returns:
        int: 进程退出码。0 表示成功，1 表示运行错误，2 表示参数数量错误。
    """
    arguments = sys.argv[1:] if argv is None else list(argv)
    if len(arguments) != 3:
        print('用法: python main.py <原文文件> <抄袭版论文文件> <答案文件>')
        print('参数数量错误: 需要 3 个参数，实际收到 {0} 个。'.format(len(arguments)))
        return EXIT_ARGUMENT_ERROR

    orig_path, copy_path, answer_path = arguments
    try:
        orig_text = read_file(orig_path)
        copy_text = read_file(copy_path)
        similarity = calculate_similarity(orig_text, copy_text)
        write_answer(answer_path, similarity)
    except FileNotFoundError as error:
        print('错误: 文件不存在 - {0}'.format(error.filename))
        return 1
    except PermissionError as error:
        print('错误: 没有读写权限 - {0}'.format(error.filename))
        return 1
    except (UnicodeDecodeError, OSError) as error:
        print('错误: 文件读写失败 - {0}'.format(error))
        return 1

    print('重复率: {0:.2f}'.format(similarity))
    return 0


if __name__ == '__main__':
    sys.exit(main())
