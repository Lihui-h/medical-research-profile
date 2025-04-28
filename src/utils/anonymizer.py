# src/utils/anonymizer.py
import re
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

def anonymize_text(text: str) -> str:
    """使用微软Presidio进行敏感信息脱敏"""
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()
    
    # 定义中文实体识别
    results = analyzer.analyze(
        text=text,
        language="zh",
        entities=["PHONE_NUMBER", "PERSON", "LOCATION"]
    )
    
    # 执行脱敏（替换为[REDACTED]）
    anonymized = anonymizer.anonymize(text, results)
    return anonymized.text