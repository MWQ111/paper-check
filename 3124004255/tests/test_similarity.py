#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""论文查重核心功能的单元测试。

运行方式（在项目根目录下）::

    python -m unittest discover -s tests -v

或直接运行本文件::

    python tests/test_similarity.py
"""

import io
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout

# 将项目根目录加入模块搜索路径，保证从任意工作目录运行测试都能导入 main 模块
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import main  # noqa: E402  pylint: disable=wrong-import-position

TEST_DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'test_data'
)

# 题目给定的样例文本
SAMPLE_ORIG = '今天是星期天，天气晴，今天晚上我要去看电影。'
SAMPLE_COPY = '今天是周天，天气晴朗，我晚上要去看电影。'

# 样例文本的预期重复率
SAMPLE_EXPECTED = 0.67


class TestCleanText(unittest.TestCase):
    """测试文本清洗功能。"""

    def test_clean_text_removes_punctuation(self):
        """中文标点与英文标点都应被去除。"""
        result = main.clean_text('你好，世界！Hello, World? (test)')
        self.assertEqual(result, '你好世界hello world test')

    def test_clean_text_keeps_alphanumeric_and_lowercases(self):
        """字母、数字应保留，且英文字母统一转为小写。"""
        result = main.clean_text('ABCabc123')
        self.assertEqual(result, 'abcabc123')

    def test_clean_text_keeps_whitespace_as_word_boundary(self):
        """空白必须保留，否则英文单词会被错误合并。"""
        result = main.clean_text('hello world')
        self.assertEqual(result, 'hello world')

    def test_clean_text_on_empty_string(self):
        """空字符串清洗后仍为空字符串。"""
        self.assertEqual(main.clean_text(''), '')


class TestTokenize(unittest.TestCase):
    """测试分词策略。"""

    def test_tokenize_chinese_contains_single_chars_and_bigrams(self):
        """中文分词应同时包含单字与相邻两字的 2-gram。"""
        tokens = list(main.tokenize(main.clean_text('今天是')))
        for expected in ('今', '天', '是', '今天', '天是'):
            self.assertIn(expected, tokens)

    def test_tokenize_chinese_bigram_count(self):
        """n 个连续中文字符应产出 n 个单字与 n-1 个 2-gram。"""
        tokens = list(main.tokenize('今天是星期天'))
        chinese_count = 6
        expected_total = chinese_count + (chinese_count - 1)
        self.assertEqual(len(tokens), expected_total)

    def test_tokenize_english_words(self):
        """英文应按空格划分的完整单词切分。"""
        cleaned = main.clean_text('Hello, World! I am here.')
        tokens = list(main.tokenize(cleaned))
        self.assertEqual(tokens, ['hello', 'world', 'i', 'am', 'here'])

    def test_tokenize_numbers(self):
        """连续数字应作为一个整体词元。"""
        tokens = list(main.tokenize(main.clean_text('2024 年 8 月')))
        self.assertIn('2024', tokens)
        self.assertIn('8', tokens)

    def test_tokenize_returns_generator(self):
        """tokenize 必须是生成器函数，以实现惰性求值。"""
        generator = main.tokenize('今天天气好')
        self.assertTrue(hasattr(generator, '__next__'))
        self.assertTrue(hasattr(generator, '__iter__'))

    def test_tokenize_empty_text(self):
        """空文本不产生任何词元。"""
        self.assertEqual(list(main.tokenize('')), [])


class TestCalculateSimilarity(unittest.TestCase):
    """测试重复率计算。"""

    def test_identical_text_similarity_is_one(self):
        """完全相同的文本，重复率应为 1.0。"""
        similarity = main.calculate_similarity(SAMPLE_ORIG, SAMPLE_ORIG)
        self.assertAlmostEqual(similarity, 1.0, places=9)

    def test_english_identical_text_similarity_is_one(self):
        """完全相同的英文文本，重复率应为 1.0。"""
        text = 'machine learning is a branch of artificial intelligence'
        similarity = main.calculate_similarity(text, text)
        self.assertAlmostEqual(similarity, 1.0, places=9)

    def test_completely_different_text_below_threshold(self):
        """完全不相关的文本，重复率应小于 0.3。"""
        similarity = main.calculate_similarity(
            '苹果香蕉橘子西瓜', '电脑手机键盘鼠标'
        )
        self.assertLess(similarity, 0.3)

    def test_empty_original_text_returns_zero(self):
        """原文为空时重复率应为 0.0。"""
        self.assertEqual(main.calculate_similarity('', SAMPLE_COPY), 0.0)

    def test_empty_copy_text_returns_zero(self):
        """抄袭版为空时重复率应为 0.0。"""
        self.assertEqual(main.calculate_similarity(SAMPLE_ORIG, ''), 0.0)

    def test_both_empty_text_returns_zero(self):
        """两篇文档均为空时重复率应为 0.0。"""
        self.assertEqual(main.calculate_similarity('', ''), 0.0)

    def test_punctuation_only_text_returns_zero(self):
        """仅含标点的文本清洗后无有效词元，重复率应为 0.0。"""
        self.assertEqual(main.calculate_similarity('！！！？？？', '。。。，。'), 0.0)

    def test_sample_sentences_partial_similarity(self):
        """样例句属于部分相似，重复率应接近 0.67 且严格介于 0 与 1 之间。"""
        similarity = main.calculate_similarity(SAMPLE_ORIG, SAMPLE_COPY)
        self.assertAlmostEqual(similarity, SAMPLE_EXPECTED, delta=0.05)
        self.assertGreater(similarity, 0.0)
        self.assertLess(similarity, 1.0)

    def test_similarity_is_symmetric(self):
        """余弦相似度具有对称性，交换两篇文档结果应一致。"""
        forward = main.calculate_similarity(SAMPLE_ORIG, SAMPLE_COPY)
        backward = main.calculate_similarity(SAMPLE_COPY, SAMPLE_ORIG)
        self.assertAlmostEqual(forward, backward, places=12)

    def test_english_similar_text_scores_higher_than_different_text(self):
        """英文近似文本的重复率应显著高于不相关文本。"""
        similar = main.calculate_similarity(
            'the quick brown fox jumps over the lazy dog',
            'the quick brown fox jumps over the lazy cat',
        )
        different = main.calculate_similarity(
            'the quick brown fox jumps over the lazy dog',
            'banana apple orange grape lemon',
        )
        self.assertGreater(similar, 0.5)
        self.assertLess(different, 0.3)

    def test_numeric_text(self):
        """纯数字文本应能被正确处理。"""
        self.assertAlmostEqual(
            main.calculate_similarity('1234567890', '1234567890'),
            1.0,
            places=9,
        )
        self.assertEqual(
            main.calculate_similarity('1234567890', '0987654321'), 0.0
        )

    def test_similarity_is_within_valid_range(self):
        """重复率必须落在 [0.0, 1.0] 区间内。"""
        for orig, copy in (
            (SAMPLE_ORIG, SAMPLE_COPY),
            (SAMPLE_ORIG, SAMPLE_ORIG),
            ('中文abc123', '不同的文本xyz789'),
            ('一段较长的中文文本用于测试取值范围', '另一段完全不同的中文内容'),
        ):
            similarity = main.calculate_similarity(orig, copy)
            self.assertGreaterEqual(similarity, 0.0)
            self.assertLessEqual(similarity, 1.0)


class TestCosineSimilarity(unittest.TestCase):
    """测试余弦相似度函数本身。"""

    def test_cosine_similarity_with_empty_vectors(self):
        """两个空向量的相似度应为 0.0。"""
        self.assertEqual(main.cosine_similarity({}, {}), 0.0)

    def test_cosine_similarity_with_one_empty_vector(self):
        """任一向量为空时相似度应为 0.0。"""
        self.assertEqual(main.cosine_similarity({'a': 1.0}, {}), 0.0)
        self.assertEqual(main.cosine_similarity({}, {'a': 1.0}), 0.0)

    def test_cosine_similarity_identical_vectors(self):
        """相同向量的相似度应为 1.0。"""
        vector = {'a': 1.0, 'b': 2.0, 'c': 3.0}
        similarity = main.cosine_similarity(vector, vector)
        self.assertAlmostEqual(similarity, 1.0, places=9)

    def test_cosine_similarity_orthogonal_vectors(self):
        """无交集的正交向量相似度应为 0.0。"""
        self.assertEqual(
            main.cosine_similarity({'a': 1.0}, {'b': 1.0}), 0.0
        )

    def test_cosine_similarity_known_value(self):
        """与已知解析解比对，验证公式实现正确。"""
        # (1,0) 与 (1,1) 的夹角为 45 度，余弦值为 sqrt(2)/2
        similarity = main.cosine_similarity({'a': 1.0}, {'a': 1.0, 'b': 1.0})
        self.assertAlmostEqual(similarity, 2 ** 0.5 / 2, places=12)


class TestBuildTfidfVector(unittest.TestCase):
    """测试 TF-IDF 向量构建。"""

    def test_build_tfidf_vector_returns_empty_dict_for_no_tokens(self):
        """无词元时应返回空字典。"""
        self.assertEqual(main.build_tfidf_vector([], {'a': 1.0}), {})

    def test_build_tfidf_vector_applies_idf_weight(self):
        """词频应乘以对应的 IDF 权重。"""
        vector = main.build_tfidf_vector(['a', 'a', 'b'], {'a': 2.0, 'b': 1.0})
        self.assertAlmostEqual(vector['a'], (2 / 3) * 2.0, places=12)
        self.assertAlmostEqual(vector['b'], (1 / 3) * 1.0, places=12)


class TestReadFile(unittest.TestCase):
    """测试文件读取与异常处理。"""

    def test_read_file_missing_file_raises_error(self):
        """读取不存在的文件应抛出 FileNotFoundError。"""
        missing = os.path.join(TEST_DATA_DIR, '不存在的文件.txt')
        with self.assertRaises(FileNotFoundError):
            main.read_file(missing)

    def test_read_file_utf8(self):
        """UTF-8 编码文件应能正常读取。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, 'utf8.txt')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(SAMPLE_ORIG)
            self.assertEqual(main.read_file(path), SAMPLE_ORIG)

    def test_read_file_falls_back_to_gbk(self):
        """UTF-8 解码失败时应自动回退到 GBK 解码。"""
        content = '今天是星期天，天气晴，编码回退测试。'
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, 'gbk.txt')
            with open(path, 'wb') as handle:
                handle.write(content.encode('gbk'))
            self.assertEqual(main.read_file(path), content)


class TestWriteAnswer(unittest.TestCase):
    """测试答案文件写出。"""

    def test_write_answer_uses_two_decimals(self):
        """答案必须以两位小数的格式写出。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, 'ans.txt')
            main.write_answer(path, 0.6695)
            with open(path, 'r', encoding='utf-8') as handle:
                self.assertEqual(handle.read(), '0.67')

    def test_write_answer_rounds_up_correctly(self):
        """第三位小数大于等于 5 时应进位。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, 'ans.txt')
            main.write_answer(path, 0.675)
            with open(path, 'r', encoding='utf-8') as handle:
                self.assertEqual(handle.read(), '0.68')

    def test_write_answer_zero_and_one(self):
        """边界值 0 与 1 应分别写出 0.00 与 1.00。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            zero_path = os.path.join(temp_dir, 'zero.txt')
            one_path = os.path.join(temp_dir, 'one.txt')
            main.write_answer(zero_path, 0.0)
            main.write_answer(one_path, 1.0)
            with open(zero_path, 'r', encoding='utf-8') as handle:
                self.assertEqual(handle.read(), '0.00')
            with open(one_path, 'r', encoding='utf-8') as handle:
                self.assertEqual(handle.read(), '1.00')


class TestMainCommandLine(unittest.TestCase):
    """测试命令行参数处理与整体流程。"""

    def test_main_with_wrong_argument_count(self):
        """参数数量不是 3 个时应返回退出码 2，并打印用法提示。"""
        captured = io.StringIO()
        with redirect_stdout(captured):
            results = [
                main.main([]),
                main.main(['only_one.txt']),
                main.main(['a.txt', 'b.txt']),
                main.main(['a.txt', 'b.txt', 'c.txt', 'd.txt']),
            ]
        self.assertEqual(results, [2, 2, 2, 2])
        self.assertIn('用法', captured.getvalue())

    def test_main_with_missing_file_returns_error(self):
        """输入文件不存在时应返回退出码 1，而不是抛出异常。"""
        missing = os.path.join(TEST_DATA_DIR, '不存在的文件.txt')
        with tempfile.TemporaryDirectory() as temp_dir:
            answer = os.path.join(temp_dir, 'ans.txt')
            captured = io.StringIO()
            with redirect_stdout(captured):
                exit_code = main.main([missing, missing, answer])
            self.assertEqual(exit_code, 1)
            self.assertFalse(os.path.exists(answer))
        self.assertIn('文件不存在', captured.getvalue())

    def test_main_end_to_end_with_test_data(self):
        """使用 tests/test_data 下的样例文件完成端到端验证。"""
        orig_path = os.path.join(TEST_DATA_DIR, 'orig.txt')
        copy_path = os.path.join(TEST_DATA_DIR, 'orig_add.txt')
        self.assertTrue(os.path.exists(orig_path), '缺少测试数据 orig.txt')
        self.assertTrue(os.path.exists(copy_path), '缺少测试数据 orig_add.txt')

        with tempfile.TemporaryDirectory() as temp_dir:
            answer = os.path.join(temp_dir, 'ans.txt')
            with redirect_stdout(io.StringIO()):
                exit_code = main.main([orig_path, copy_path, answer])
            self.assertEqual(exit_code, 0)
            with open(answer, 'r', encoding='utf-8') as handle:
                content = handle.read()

        self.assertRegex(content, r'^\d+\.\d{2}$')
        self.assertEqual(content, '0.67')


class TestPerformance(unittest.TestCase):
    """测试性能约束。"""

    def test_long_text_completes_within_time_limit(self):
        """两篇 10000 次重复的长文本应在 5 秒内完成计算。"""
        long_orig = SAMPLE_ORIG * 10000
        long_copy = SAMPLE_COPY * 10000

        start = time.perf_counter()
        similarity = main.calculate_similarity(long_orig, long_copy)
        elapsed = time.perf_counter() - start

        self.assertLess(
            elapsed, 5.0,
            '长文本计算耗时 {0:.3f} 秒，超出 5 秒限制'.format(elapsed),
        )
        self.assertGreaterEqual(similarity, 0.0)
        self.assertLessEqual(similarity, 1.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
