import logging
import re
import difflib
from typing import Dict, List, Tuple, Optional
import editdistance
from dataclasses import dataclass
import jieba
import math

# 导入WeTextProcessing TN模块
try:
    from .tn.chinese.normalizer import Normalizer as ZHNormalizer
    from .tn.english.normalizer import Normalizer as ENNormalizer
    TN_AVAILABLE = True
except ImportError:
    try:
        from backend.tn.chinese.normalizer import Normalizer as ZHNormalizer
        from backend.tn.english.normalizer import Normalizer as ENNormalizer
        TN_AVAILABLE = True
    except ImportError:
        print("Warning: WeTextProcessing TN module not available, falling back to basic normalization")
        TN_AVAILABLE = False

# 初始化TN标准化器
if TN_AVAILABLE:
    try:
        zhnormalizer = ZHNormalizer()
        ennormalizer = ENNormalizer()
    except Exception as e:
        print(f"Warning: Failed to initialize TN normalizers: {e}")
        TN_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
    """评测结果数据类"""
    original_text: str
    recognized_text: str
    cer: float  # Character Error Rate
    wer: float  # Word Error Rate
    similarity: float  # 相似度
    exact_match: bool  # 完全匹配
    char_insertions: int
    char_deletions: int
    char_substitutions: int
    word_insertions: int
    word_deletions: int
    word_substitutions: int
    diff_details: List[Dict]  # 详细差异信息

class CosyVoiceTextNormalizer:
    """基于CosyVoice的文本标准化器 - 更准确的文本处理"""
    
    def __init__(self):
        # 初始化jieba
        jieba.initialize()
        # 中文字符正则表达式
        self.chinese_char_pattern = re.compile(r'[\u4e00-\u9fff]+')
    
    def contains_chinese(self, text: str) -> bool:
        """检查是否包含中文字符"""
        return bool(self.chinese_char_pattern.search(text))
    
    def replace_corner_mark(self, text: str) -> str:
        """替换特殊符号"""
        text = text.replace('²', '平方')
        text = text.replace('³', '立方')
        return text
    
    def remove_bracket(self, text: str) -> str:
        """移除无意义符号"""
        text = text.replace('（', '').replace('）', '')
        text = text.replace('【', '').replace('】', '')
        text = text.replace('`', '').replace('`', '')
        text = text.replace("——", " ")
        return text
    
    def replace_blank(self, text: str) -> str:
        """移除中文字符间的空白"""
        out_str = []
        for i, c in enumerate(text):
            if c == " ":
                if i > 0 and i < len(text) - 1:
                    if ((text[i + 1].isascii() and text[i + 1] != " ") and
                            (text[i - 1].isascii() and text[i - 1] != " ")):
                        out_str.append(c)
                # 对于中文字符间的空格，不保留
            else:
                out_str.append(c)
        return "".join(out_str)
    
    def normalize(self, text: str) -> str:
        """
        标准化文本 - 使用WeTextProcessing进行更准确的标准化
        """
        if not text:
            return ""
        
        text = text.strip()
        
        # 如果TN模块可用，使用WeTextProcessing进行标准化
        if TN_AVAILABLE:
            try:
                if self.contains_chinese(text):
                    # 使用中文标准化器
                    text = zhnormalizer.normalize(text)
                else:
                    # 使用英文标准化器
                    text = ennormalizer.normalize(text)
            except Exception as e:
                logger.warning(f"TN normalization failed, falling back to basic normalization: {e}")
                # 降级到基础标准化
                return self._basic_normalize(text)
        else:
            # 使用基础标准化
            return self._basic_normalize(text)
        
        # 后续处理
        if self.contains_chinese(text):
            # 中文文本处理
            text = text.replace("\n", "")
            text = self.replace_blank(text)
            text = self.replace_corner_mark(text)
            text = text.replace(".", "。")
            text = text.replace(" - ", "，")
            text = self.remove_bracket(text)
            text = re.sub(r'[，,、]+$', '。', text)
            
            # 移除标点符号，只保留有意义字符
            text = re.sub(r'[^\u4e00-\u9fff\w]', '', text)
        else:
            # 英文文本处理
            text = text.lower()
            # 移除标点符号，只保留字母数字
            text = re.sub(r'[^\w\s]', '', text)
            text = re.sub(r'\s+', '', text)
        
        return text.strip()
    
    def _basic_normalize(self, text: str) -> str:
        """
        基础文本标准化（当TN模块不可用时的降级方案）
        """
        if self.contains_chinese(text):
            # 中文文本处理
            text = text.replace("\n", "")
            text = self.replace_blank(text)
            text = self.replace_corner_mark(text)
            text = text.replace(".", "。")
            text = text.replace(" - ", "，")
            text = self.remove_bracket(text)
            text = re.sub(r'[，,、]+$', '。', text)
            
            # 移除标点符号，只保留有意义字符
            text = re.sub(r'[^\u4e00-\u9fff\w]', '', text)
        else:
            # 英文文本处理
            text = text.lower()
            # 移除标点符号，只保留字母数字
            text = re.sub(r'[^\w\s]', '', text)
            text = re.sub(r'\s+', '', text)
        
        return text.strip()
    
    def segment_words(self, text: str) -> List[str]:
        """
        中文分词 - 改进版本
        """
        normalized_text = self.normalize(text)
        if not normalized_text:
            return []
        
        if self.contains_chinese(normalized_text):
            # 中文分词
            words = list(jieba.cut(normalized_text, cut_all=False))
        else:
            # 英文按字符分割（因为已经移除了空格）
            words = list(normalized_text)
        
        # 过滤空字符串
        words = [word.strip() for word in words if word.strip()]
        
        return words

# 保持兼容性的别名
TextNormalizer = CosyVoiceTextNormalizer

class TextComparator:
    """文本比对器"""
    
    def __init__(self):
        self.normalizer = TextNormalizer()
    
    def calculate_cer(self, reference: str, hypothesis: str) -> Tuple[float, Dict]:
        """
        计算字符错误率 (Character Error Rate)
        """
        ref_normalized = self.normalizer.normalize(reference)
        hyp_normalized = self.normalizer.normalize(hypothesis)
        
        ref_chars = list(ref_normalized)
        hyp_chars = list(hyp_normalized)
        
        logger.debug(f"CER calculation - Reference: '{reference}' -> '{ref_normalized}' ({len(ref_chars)} chars)")
        logger.debug(f"CER calculation - Hypothesis: '{hypothesis}' -> '{hyp_normalized}' ({len(hyp_chars)} chars)")
        
        if len(ref_chars) == 0:
            if len(hyp_chars) == 0:
                return 0.0, {"insertions": 0, "deletions": 0, "substitutions": 0}
            else:
                # 如果参考为空但识别有内容，错误率为1.0
                return 1.0, {"insertions": len(hyp_chars), "deletions": 0, "substitutions": 0}
        
        # 使用editdistance计算编辑距离
        distance = editdistance.eval(ref_chars, hyp_chars)
        cer = min(distance / len(ref_chars), 1.0)  # 限制CER不超过1.0
        
        # 计算详细的操作统计
        operations = self._get_edit_operations(ref_chars, hyp_chars)
        
        logger.debug(f"CER result: {cer:.3f}, distance: {distance}, ref_len: {len(ref_chars)}")
        
        return cer, operations
    
    def calculate_wer(self, reference: str, hypothesis: str) -> Tuple[float, Dict]:
        """
        计算词错误率 (Word Error Rate)
        """
        ref_words = self.normalizer.segment_words(reference)
        hyp_words = self.normalizer.segment_words(hypothesis)
        
        logger.debug(f"WER calculation - Reference words: {ref_words} ({len(ref_words)} words)")
        logger.debug(f"WER calculation - Hypothesis words: {hyp_words} ({len(hyp_words)} words)")
        
        if len(ref_words) == 0:
            if len(hyp_words) == 0:
                return 0.0, {"insertions": 0, "deletions": 0, "substitutions": 0}
            else:
                # 如果参考为空但识别有内容，错误率为1.0
                return 1.0, {"insertions": len(hyp_words), "deletions": 0, "substitutions": 0}
        
        # 使用editdistance计算编辑距离
        distance = editdistance.eval(ref_words, hyp_words)
        wer = min(distance / len(ref_words), 1.0)  # 限制WER不超过1.0
        
        # 计算详细的操作统计
        operations = self._get_edit_operations(ref_words, hyp_words)
        
        logger.debug(f"WER result: {wer:.3f}, distance: {distance}, ref_len: {len(ref_words)}")
        
        return wer, operations
    
    def _get_edit_operations(self, reference: List, hypothesis: List) -> Dict:
        """
        获取编辑操作的详细统计
        """
        # 使用difflib获取操作序列
        matcher = difflib.SequenceMatcher(None, reference, hypothesis)
        opcodes = matcher.get_opcodes()
        
        insertions = 0
        deletions = 0
        substitutions = 0
        
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'insert':
                insertions += j2 - j1
            elif tag == 'delete':
                deletions += i2 - i1
            elif tag == 'replace':
                substitutions += max(i2 - i1, j2 - j1)
        
        return {
            'insertions': insertions,
            'deletions': deletions,
            'substitutions': substitutions
        }
    
    def calculate_similarity(self, reference: str, hypothesis: str) -> float:
        """
        计算文本相似度 (基于编辑距离)
        """
        ref_normalized = self.normalizer.normalize(reference)
        hyp_normalized = self.normalizer.normalize(hypothesis)
        
        if not ref_normalized and not hyp_normalized:
            return 1.0
        
        if not ref_normalized or not hyp_normalized:
            return 0.0
        
        # 使用字符级编辑距离
        distance = editdistance.eval(ref_normalized, hyp_normalized)
        max_length = max(len(ref_normalized), len(hyp_normalized))
        
        similarity = 1.0 - (distance / max_length)
        return max(0.0, similarity)
    
    def get_diff_details(self, reference: str, hypothesis: str) -> List[Dict]:
        """
        获取详细的差异信息
        """
        ref_normalized = self.normalizer.normalize(reference)
        hyp_normalized = self.normalizer.normalize(hypothesis)
        
        matcher = difflib.SequenceMatcher(None, ref_normalized, hyp_normalized)
        opcodes = matcher.get_opcodes()
        
        diff_details = []
        
        for tag, i1, i2, j1, j2 in opcodes:
            detail = {
                'operation': tag,
                'reference_text': ref_normalized[i1:i2] if tag != 'insert' else '',
                'hypothesis_text': hyp_normalized[j1:j2] if tag != 'delete' else '',
                'reference_pos': (i1, i2),
                'hypothesis_pos': (j1, j2)
            }
            diff_details.append(detail)
        
        return diff_details

class TTSEvaluator:
    """TTS评测器"""
    
    def __init__(self):
        self.comparator = TextComparator()
    
    def evaluate_single(self, original_text: str, recognized_text: str) -> EvaluationResult:
        """
        评测单个样本
        """
        # 计算CER
        cer, char_ops = self.comparator.calculate_cer(original_text, recognized_text)
        
        # 计算WER
        wer, word_ops = self.comparator.calculate_wer(original_text, recognized_text)
        
        # 计算相似度
        similarity = self.comparator.calculate_similarity(original_text, recognized_text)
        
        # 判断是否完全匹配
        normalized_original = self.comparator.normalizer.normalize(original_text)
        normalized_recognized = self.comparator.normalizer.normalize(recognized_text)
        exact_match = normalized_original == normalized_recognized
        
        # 获取详细差异
        diff_details = self.comparator.get_diff_details(original_text, recognized_text)
        
        return EvaluationResult(
            original_text=original_text,
            recognized_text=recognized_text,
            cer=cer,
            wer=wer,
            similarity=similarity,
            exact_match=exact_match,
            char_insertions=char_ops.get('insertions', 0),
            char_deletions=char_ops.get('deletions', 0),
            char_substitutions=char_ops.get('substitutions', 0),
            word_insertions=word_ops.get('insertions', 0),
            word_deletions=word_ops.get('deletions', 0),
            word_substitutions=word_ops.get('substitutions', 0),
            diff_details=diff_details
        )
    
    def evaluate_batch(self, text_pairs: List[Tuple[str, str]]) -> List[EvaluationResult]:
        """
        批量评测
        """
        results = []
        
        for original, recognized in text_pairs:
            try:
                result = self.evaluate_single(original, recognized)
                results.append(result)
            except Exception as e:
                logger.error(f"Error evaluating text pair: {str(e)}")
                # 创建错误结果
                error_result = EvaluationResult(
                    original_text=original,
                    recognized_text=recognized,
                    cer=float('inf'),
                    wer=float('inf'),
                    similarity=0.0,
                    exact_match=False,
                    char_insertions=0,
                    char_deletions=0,
                    char_substitutions=0,
                    word_insertions=0,
                    word_deletions=0,
                    word_substitutions=0,
                    diff_details=[]
                )
                results.append(error_result)
        
        return results
    
    def calculate_summary_statistics(self, results: List[EvaluationResult]) -> Dict:
        """
        计算汇总统计信息
        """
        if not results:
            return {}
        
        valid_results = [r for r in results if not math.isinf(r.cer)]
        
        if not valid_results:
            return {}
        
        # 计算平均指标
        avg_cer = sum(r.cer for r in valid_results) / len(valid_results)
        avg_wer = sum(r.wer for r in valid_results) / len(valid_results)
        avg_similarity = sum(r.similarity for r in valid_results) / len(valid_results)
        
        # 完全匹配率
        exact_match_rate = sum(1 for r in valid_results if r.exact_match) / len(valid_results)
        
        # CER和WER分布
        cer_distribution = self._calculate_distribution([r.cer for r in valid_results])
        wer_distribution = self._calculate_distribution([r.wer for r in valid_results])
        
        return {
            'total_samples': len(results),
            'valid_samples': len(valid_results),
            'avg_cer': avg_cer,
            'avg_wer': avg_wer,
            'avg_similarity': avg_similarity,
            'exact_match_rate': exact_match_rate,
            'cer_distribution': cer_distribution,
            'wer_distribution': wer_distribution
        }
    
    def _calculate_distribution(self, values: List[float]) -> Dict:
        """
        计算数值分布
        """
        if not values:
            return {}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            'min': sorted_values[0],
            'max': sorted_values[-1],
            'median': sorted_values[n // 2],
            'q1': sorted_values[n // 4],
            'q3': sorted_values[3 * n // 4],
            'mean': sum(values) / len(values),
            'std': math.sqrt(sum((x - sum(values) / len(values)) ** 2 for x in values) / len(values))
        }
