# src/utils/data_filter.py
import re
from typing import Dict, Any

class MedicalContentFilter:
    def __init__(self):
        # 医疗核心关键词（动态加载示例）
        self.medical_keywords = [
            r'医院', r'医生', r'挂号', r'就诊', r'治疗', r'病人',
            r'病历', r'诊断', r'药品', r'检查', r'化验',
            r'\b门诊\b', r'手术', r'科室', r'医保',
            r'检查报告', r'处方', r'护士', r'病房'
        ]
        # 医生白名单（正则优化）
        self.doctor_pattern = re.compile(
            r'何强|高祥福|张弘|施翔|林胜友|黄抒伟|钱宇|夏永良|周秀扣'
        )
        
        # 构建复合正则表达式
        self.keyword_regex = re.compile(
            '|'.join(self.medical_keywords), 
            flags=re.IGNORECASE
        )

    def is_medical_related(self, item: Dict[str, Any]) -> bool:
        """内容医疗相关性检测"""
        text = f"{item.get('title', '')} {item.get('content', '')}"
        
        # 双重验证机制
        keyword_match = self.keyword_regex.search(text) 
        doctor_match = self.doctor_pattern.search(text)
        
        return keyword_match or doctor_match