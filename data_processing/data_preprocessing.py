import pandas as pd
from jieba_extract_disease import DiseaseExtractor  # 导入自定义的疾病提取器

MAX_RELATED_DISEASES_COUNT = 2

class DataPreprocessor:
    def __init__(self, disease_dict_csv):
        """
        初始化数据预处理器，加载疾病名称构建Jieba自定义词典。

        :param disease_dict_csv: 含疾病名称的CSV路径（如你的disease_names_processed.csv）
        """
        self.extractor = DiseaseExtractor(disease_dict_csv)
    
    def process_medical_data(self, input_csv, output_csv):
        # 读取输入CSV文件
        df = pd.read_csv(input_csv, encoding="utf-8-sig")
        
        # 存储有效行的Top N疾病和原始行数据
        valid_rows = []
        top_diseases_per_row = []
        
        for _, row in df.iterrows():
            # 合并三列文本内容
            text_parts = [
                str(row['department']),
                str(row['title']),
                str(row['ask'])
            ]
            combined_text = ' '.join(text_parts)
            
            # 提取疾病名称
            diseases = self.extractor.extract_diseases_from_text(combined_text)
            
            # 只处理识别到疾病的数据
            if not diseases:
                continue  # 无疾病则跳过当前行
            
            # 计算当前行的Top N疾病
            # 统计频率
            freq = {}
            for disease in diseases:
                freq[disease] = freq.get(disease, 0) + 1
            # 按频率排序（降序），频率相同则按出现顺序
            sorted_diseases = sorted(freq.items(), key=lambda x: (-x[1], diseases.index(x[0])))
            sorted_names = [item[0] for item in sorted_diseases]
            # 取前N个，不足则用空字符串填充
            row_top = sorted_names[:MAX_RELATED_DISEASES_COUNT]
            if len(row_top) < MAX_RELATED_DISEASES_COUNT:
                row_top += [""] * (MAX_RELATED_DISEASES_COUNT - len(row_top))
            
            # 保存有效行数据和对应的疾病
            valid_rows.append(row)
            top_diseases_per_row.append(row_top)
        
        # 基于有效行创建新的DataFrame
        result_df = pd.DataFrame(valid_rows)
        
        # 添加Top N疾病列
        for i in range(MAX_RELATED_DISEASES_COUNT):
            col_name = f'related_disease_{i+1}'
            result_df[col_name] = [row_top[i] for row_top in top_diseases_per_row]
        
        # 保存结果到新CSV
        result_df.to_csv(output_csv, encoding="utf-8-sig", index=False)
        print(f"处理完成，共保留 {len(result_df)} 条有效数据，结果已保存至 {output_csv}")
    
    def preprocess_dir(self, process_dir_path, output_dir_path):
        import os
        # 确保输出目录存在
        os.makedirs(output_dir_path, exist_ok=True)
        list_dir = os.listdir(process_dir_path) 
        for file_name in list_dir:
            if file_name.endswith('.csv'):
                file_path = os.path.join(process_dir_path, file_name)
                self.process_medical_data(
                    input_csv=file_path,
                    output_csv=os.path.join(output_dir_path, file_name)
                )

if __name__ == "__main__":
    DISEASE_DICT = "disease_names_processed.csv"  # 疾病词典CSV路径
    preprocessor = DataPreprocessor(disease_dict_csv=DISEASE_DICT)
    preprocessor.preprocess_dir("original_data", "processed_data")