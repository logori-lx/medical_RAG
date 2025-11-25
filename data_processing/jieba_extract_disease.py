import pandas as pd
import jieba
import os

JIEBA_DICT_PATH = "./jieba_dict.txt"

class DiseaseExtractor:
    def __init__(self, disease_dict_csv):
        """
        初始化疾病提取器，加载疾病名称构建Jieba自定义词典。

        :param disease_dict_csv: 含疾病名称的CSV路径（如你的disease_names_processed.csv）
        """
        if not os.path.exists(JIEBA_DICT_PATH):
            print("正在加载疾病名称并构建Jieba词典...")
            # 读取疾病CSV（假设疾病名称在"disease_name"列，若列名不同需修改）
            disease_df = pd.read_csv(disease_dict_csv, encoding="utf-8-sig")
            # 提取不重复的疾病名称（去重，避免词典冗余）
            disease_names = disease_df["disease_name"].dropna().str.strip().unique().tolist()
            
            # 生成Jieba自定义词典（格式：词语 频率 词性，频率设为1000确保优先分词）
            jieba_dict_content = "\n".join([f"{name} 1000 disease" for name in disease_names])
            # 临时保存词典文件（Jieba需通过文件加载）
            
            with open(JIEBA_DICT_PATH, "w", encoding="utf-8") as f:
                f.write(jieba_dict_content)
            print(f"已生成Jieba词典，包含 {len(disease_names)} 个疾病名称")
        else:
            # 如果词典文件已存在，直接读取疾病名称列表以初始化集合
            disease_df = pd.read_csv(disease_dict_csv, encoding="utf-8-sig")
            disease_names = disease_df["disease_name"].dropna().str.strip().unique().tolist()
        
        # 加载自定义词典（覆盖Jieba默认分词，确保疾病名称被正确拆分）
        jieba.load_userdict(JIEBA_DICT_PATH)
        print(f"成功加载 {len(disease_names)} 个疾病名称到Jieba词典")
        self.disease_set = set(disease_names)
    def extract_diseases_from_text(self, text):
        if pd.isna(text):
            return []
        # 分词（使用自定义词典确保疾病名称不被拆分）
        words = jieba.lcut(str(text).strip())
        # 筛选出在疾病集合中的词（用set加速查找）
        return [word for word in words if word in self.disease_set]

if __name__ == "__main__":
    # 测试代码
    extractor = DiseaseExtractor("disease_names_processed.csv")
    sample_text = "患者患有高血压和糖尿病，伴有冠心病史。"
    extracted_diseases = extractor.extract_diseases_from_text(sample_text)
    print("提取的疾病名称：", extracted_diseases)
    
    
    