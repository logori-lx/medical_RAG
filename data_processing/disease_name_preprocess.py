import pandas as pd
import re

COMMON_DISEASE_NAME_LENGTH = 6
def filter_diseases_by_suffix(excel_path):
    print("正在读取Excel文件...")
    try:
        # 读取Excel（默认读取第一个工作表，疾病名称默认在第一列）
        df_raw = pd.read_excel(excel_path, header=None)  # 无表头，避免列名干扰
        disease_col = df_raw.iloc[:, 2]  # 取第一列作为疾病名称列
        print(f"成功读取 {len(disease_col)} 条原始数据")
    except Exception as e:
        print(f"读取Excel失败：{str(e)}")
        return

    # --------------------------
    # 2. 定义疾病后缀正则表达式
    # --------------------------
    # 核心：覆盖常见疾病后缀（炎/病/综合征等）+ 特殊疾病类型，避免漏筛
    DISEASE_SUFFIX_REGEX = r"""
    ^[a-zA-Z0-9\u4e00-\u9fa5\s\(\)\-\/]+?  # 前缀：允许字母/数字/中文/空格/括号/连接符
    (?:
        # 常见疾病后缀（核心筛选依据）
        综合征|综合症|病|症|炎|瘤|癌|疮|疡|痔|癣|斑|疹|毒|疯|
        障碍|缺陷|变性|增生|硬化|萎缩|畸形|麻痹|贫血|血症|水肿|
        积液|肥大|息肉|结石|囊肿|结核|痢疾|伤寒|
        # 器官特异性疾病后缀（补充筛选，避免漏筛常见疾病）
        肝炎|肺炎|肾炎|胃炎|肠炎|关节炎|神经炎|角膜炎|结膜炎|
        中耳炎|鼻窦炎|咽喉炎|支气管炎|
        # 特殊疾病类型（无典型后缀但属于疾病的名称）
        哮喘|糖尿病|高血压|冠心病|帕金森|阿尔茨海默|艾滋病|
        流感|麻疹|水痘|带状疱疹|梅毒|淋病|疟疾|霍乱
    )
    [\s\(\)\-\/]*$  # 后缀：允许结尾的空格/括号/连接符（如"糖尿病 (2型)"）
    """
    # 编译正则：忽略空格换行、大小写不敏感、支持中文
    disease_pattern = re.compile(DISEASE_SUFFIX_REGEX, re.VERBOSE | re.UNICODE | re.IGNORECASE)

    # --------------------------
    # 3. 筛选有效疾病名称
    # --------------------------
    print("正在筛选有效疾病名称...")
    long_name_diseases = []
    short_name_diseases = []
    invalid_records = []

    # 第一次遍历，筛选出符合后缀规则的疾病名称
    for idx, raw_name in enumerate(disease_col):
        # 预处理：转为字符串、去前后空格、去特殊标点（避免格式干扰）
        if pd.isna(raw_name):  # 跳过空值
            invalid_records.append({"序号": idx + 1, "原始内容": "空值", "原因": "空数据"})
            continue
        
        # 转为字符串并预处理
        clean_name = str(raw_name).strip()
        # 去除无意义的特殊字符（如全角空格、制表符）
        clean_name = re.sub(r"[\t\u3000]", "", clean_name)
        
        if len(clean_name) < 2:  # 跳过过短文本（如单个字、空字符串）
            invalid_records.append({"序号": idx + 1, "原始内容": raw_name, "原因": "文本过短（<2字符）"})
            continue
            
        if disease_pattern.match(clean_name):
            if len(clean_name) <= COMMON_DISEASE_NAME_LENGTH:
                short_name_diseases.append(clean_name)
            else:
                long_name_diseases.append(clean_name)
        else:
            invalid_records.append({"序号": idx + 1, "原始内容": raw_name, "原因": "未匹配疾病后缀规则"})

    # --------------------------
    # 4. 去重处理
    # --------------------------
    print("正在进行去重处理...")
    
    # 短名称去重（使用set自动去重）
    unique_short_names = list(set(short_name_diseases))
    # 排序（按长度降序，长度相同按字母顺序）
    unique_short_names.sort(key=lambda x: (-len(x), x))
    print(f"筛选出 {len(unique_short_names)} 条唯一短名称疾病")
    
    # 长名称前缀去重
    # 首先对长名称按长度排序（从短到长），这样可以优先保留较短的前缀
    long_name_diseases.sort(key=lambda x: len(x))
    
    unique_long_names = []
    # 用于存储已经处理过的前缀（包括短名称和已保留的长名称）
    processed_prefixes = set(unique_short_names)
    
    for long_name in long_name_diseases:
        # 检查当前长名称是否以任何已处理的前缀开头
        is_duplicate = False
        for prefix in processed_prefixes:
            if long_name.startswith(prefix):
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_long_names.append(long_name)
            processed_prefixes.add(long_name[COMMON_DISEASE_NAME_LENGTH])
    print(f"筛选出 {len(unique_long_names)} 条唯一长名称疾病")
    return unique_long_names + unique_short_names
            
        
def add_custom_diseases(csv_path, custom_diseases_csv_path):
    # Load the files
    try:
        df_orig = pd.read_csv(csv_path)
        df_supp = pd.read_csv(custom_diseases_csv_path)

        # Concatenate
        df_combined = pd.concat([df_orig, df_supp])

        # Drop duplicates based on 'disease_name', keeping the first occurrence
        # Assuming the user wants to keep the original if it exists, or the new one if not.
        # Since we are just merging and sorting, order of drop doesn't matter much if names are identical.
        df_combined = df_combined.drop_duplicates(subset='disease_name')

        # Ensure 'name_length' is correct (recalculate just in case)
        df_combined['name_length'] = df_combined['disease_name'].astype(str).apply(len)

        # Sort by name_length in descending order
        df_combined = df_combined.sort_values(by='name_length', ascending=False)

        df_combined.to_csv(csv_path, index=False)

        print(f"Successfully merged and sorted. Total entries: {len(df_combined)}")
        print(df_combined.head())

    except Exception as e:
        print(f"An error occurred: {e}")
        
                 
    
#目的：生成jieba疾病词典，可以实现使用jieba库匹配识别出语句中的疾病
if __name__ == "__main__":
    # 河北卫健委的数据中含有大量在普通人眼中不是疾病的疾病，故而需要对其中的数据进行筛选
    # xlsx来源：河北卫健委
    INPUT_EXCEL = "disease_names.xlsx"
    # 输出路径：筛选后疾病的CSV（可自定义名称）
    OUTPUT_CSV = "./disease_names_processed.csv"

    # 执行筛选
    res = filter_diseases_by_suffix(INPUT_EXCEL)
    df_final = pd.DataFrame({
        "disease_name": res,
        "name_length": [len(name) for name in res],
    })
    
    # 按长度降序排序，长度相同按字母顺序
    df_final = df_final.sort_values(by=["name_length", "disease_name"], ascending=[False, True]).reset_index(drop=True)
    
    # 保存为CSV
    df_final.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"筛选结果已保存到 {OUTPUT_CSV}，共 {len(df_final)} 条有效疾病名称。")
    
    # 筛选后的数据没有很多常见病的名称
    # 故与genai生成的常见病列表(supplementary_common_diseases.csv)合并，作为补充
    add_custom_diseases(OUTPUT_CSV, 'supplementary_common_diseases.csv')
    
    
    