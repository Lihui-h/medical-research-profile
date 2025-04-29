# src/utils/data_cleaner.py
def doctor_mention_filter(text):
    """医生提及关联性验证"""
    doctor_names = ["何强", "高祥福", "张弘", "施翔", "林胜友", 
                   "黄抒伟", "钱宇", "夏永良", "周秀扣"]
    hospital_terms = ["省中", "中医院", "浙江"]
    
    has_doctor = any(name in text for name in doctor_names)
    has_hospital = any(term in text for term in hospital_terms)
    
    return has_doctor and has_hospital  # 必须同时满足

# 在保存前调用
cleaned_data = [post for post in raw_data if doctor_mention_filter(post['content'])]