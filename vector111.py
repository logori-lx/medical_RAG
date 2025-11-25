import os
import re
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
from tqdm import tqdm

# Configuration Parameters
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"  # Disable symbolic link warnings
MEDICAL_DATA_DIR = r"D:\software\software engineering\project"  # Data Root directory
BGE_MODEL_NAME = "BAAI/bge-small-zh-v1.5"  # Chinese Medical Embedding Model
COLLECTION_NAME = "medical_qa_chroma"  # Chroma collection name
CHROMA_STORAGE_PATH = "./chroma_medical_data"  # Vector Data Storage path

# File Name and Department Mapping
FILE_DEPARTMENT_MAP = {
    "男科5-13000.csv": "Andriatria_男科",
    "内科5000-33000.csv": "IM_内科",
    "妇产科6-28000.csv": "OAGD_妇产科",
    "儿科5-14000.csv": "Pediatric_儿科",
    "肿瘤科5-10000.csv": "Oncology_肿瘤科",
    "外科5-14000.csv": "Surgical_外科"
}

# Disease extraction Regular expressions
DISEASE_PATTERN = re.compile(
    r'((High|Low|Acute|Slow|Severe|Mild|Primary|Secondary|Original|Subsequent|Good|Bad)?[A-Za-z]{2,15}?(?:Disease|Syndrome|Inflammation|Tumor|Cancer|Ulcer|Poisoning|Infection|Disorder|Defect|Malformation|Paralysis|Spasm|Hemorrhage|Infarction|Sclerosis|Atrophy|Hyperplasia|Calculus|Abscess|Effusion|Fever|Pain|Dermatitis|Rash|Paralysis|Jaundice|Blindness|Deafness|Palsy|Tuberculosis|Dysentery|Wart|Hemorrhoid))',
    re.IGNORECASE
)




# Load medical Q&A data
def load_medical_data(data_dir):
    all_dfs = []
    print(f"Start loading the medical Q&A data")
    for filename, department in FILE_DEPARTMENT_MAP.items():
        file_path = Path(data_dir) / filename
        print(f"Loading {filename}...")

        # Use the open function to specify the encoding and error handling, and then pass it to read_csv
        with open(file_path, "r", encoding="gbk", errors="ignore") as f:
            df = pd.read_csv(f)

        # Unified listing
        df.columns = ["department", "title", "ask", "answer"]
        all_dfs.append(df)
        print(f"Loading {department}：{len(df)} piece of data")

    # Merge all the data and reset the index
    merged_df = pd.concat(all_dfs, ignore_index=True)
    print(f"\nThe data loading is complete. The total number of entries after merging: {len(merged_df)}")
    return merged_df



# Data Cleaning
def clean_medical_data(df):
    print("\nStart data cleaning...")

    # Chinese double quotation marks to English double quotation marks
    def fix_quotes(text):
        if pd.isna(text):
            return text
        return str(text).replace('“', '"').replace('”', '"').strip()

    # Apply to all text columns
    text_cols = ["title", "ask", "answer", "department"]
    for col in text_cols:
        df[col] = df[col].apply(fix_quotes)

    # Handle null values: Delete the core fields (ask/answer) if they are empty, and fill the other fields with None
    df = df.dropna(subset=["ask", "answer"])  # Delete invalid lines without Q&A content
    df = df.fillna("None")  # Other empty columns are filled with None
    df = df.replace("", "None")  # Convert an empty string to None

    # duplicate removal
    df = df.drop_duplicates(subset=["ask", "answer"], keep="first")

    print(f"The cleaning is complete. Only valid data remains ：{len(df)} pieces")
    return df



# 3. Extract related diseases
def extract_related_diseases(df):
    print("\nStart extracting related diseases (optimize regular expressions to cover more disease types)...")

    def extract_disease_from_text(row):
        # Merge the title, question and answer texts
        combined_text = f"{row['title']} {row['ask']} {row['answer']}"
        # Regular matching disease
        diseases = DISEASE_PATTERN.findall(combined_text)
        # Extract the disease names from the matching results, remove duplicates and filter out noise
        unique_diseases = list(set([d[0] for d in diseases if len(d[0]) >= 2 and not d[0].endswith("Minor illness")]))
        # Return the default value when there is no matching result
        return unique_diseases if unique_diseases else ["There is no clear related disease"]

    # Batch extraction
    tqdm.pandas(desc="Progress of disease extraction")
    df["related_disease"] = df.progress_apply(extract_disease_from_text, axis=1)

    print("Disease extraction completed")
    return df


# Initialize the Chroma vector database
def init_chroma():
    print("\nInitialize the Chroma vector database...")
    # Create a persistent client
    client = chromadb.PersistentClient(path=CHROMA_STORAGE_PATH)

    # Configure the Chinese embedding function (BGE-small-zh-v1.5)
    bge_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=BGE_MODEL_NAME
    )

    # Create/obtain a collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=bge_ef,
        metadata={"description": "Medical Q&A dataset"}
    )

    print(f"Chroma initialization is complete. Collection name: {COLLECTION_NAME}")
    return collection



# 5. Store in the Chroma vector database (list to string, adapted metadata format)
def save_to_chroma(collection, df):
    print("\nStart saving data to Chroma...")

    # 构造Chroma所需格式：ids、documents、metadatas
    ids = [str(i + 1) for i in range(len(df))]  # The ID increments from 1
    documents = df["answer"].tolist()  # The doctor's response serves as the core content of the search
    metadatas = [
        {
            "department": row["department"],
            "related_disease": ",".join(row["related_disease"]),  # List to String
            "title": row["title"],
            "query": row["ask"]  # User questions are stored in metadata for easy viewing
        }
        for _, row in df.iterrows()
    ]

    # Store in batches
    batch_size = 1000
    for i in tqdm(range(0, len(ids), batch_size), desc="Save progress"):
        batch_ids = ids[i:i + batch_size]
        batch_docs = documents[i:i + batch_size]
        batch_metas = metadatas[i:i + batch_size]
        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metas
        )

    print(f"The data storage has been completed. The total number of entries in the collection：{collection.count()}")


# Query from Chroma
def query_chroma(collection, query_text, top_k=3):
    """Query the question-and-answer pairs most similar to medical questions and return normal Chinese results"""
    results = collection.query(
        query_texts=[query_text],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]  # There is no need to explicitly specify ids
    )

    # The sorting result: The string is converted back to the list, and the display format is adapted
    formatted_results = []
    for i in range(len(results["ids"][0])):
        # Convert the disease string back to the list
        related_diseases = results["metadatas"][0][i]["related_disease"].split(",")
        formatted_results.append({
            "id": results["ids"][0][i],
            "related_disease": related_diseases,
            "department": results["metadatas"][0][i]["department"],
            "user_query": results["metadatas"][0][i]["query"],
            "doctor_answer": results["documents"][0][i],
            "similarity": 1 - results["distances"][0][i]  # Distance to similarity
        })
    return formatted_results

if __name__ == "__main__":
    if Path(CHROMA_STORAGE_PATH).exists():
        print(f"An old data folder was found{CHROMA_STORAGE_PATH}, please delete it manually before running!")
        print("(The old data contains garbled characters or encoding anomalies and must be cleared before new data can be stored.)")
        exit()

    # Load the merged data
    medical_df = load_medical_data(MEDICAL_DATA_DIR)

    # Data cleaning (handling quotation marks, null values, and deduplication)
    cleaned_df = clean_medical_data(medical_df)

    # Extract related diseases (regularization)
    final_df = extract_related_diseases(cleaned_df)

    # Initialize the Chroma vector database
    chroma_collection = init_chroma()

    # store into Chroma
    save_to_chroma(chroma_collection, final_df)

    # Query verification
    test_queries = [
        "Can patients with hypertension take Codonopsis pilosula?",
        "How to care for a pediatric baby with a fever?",
        "What are the causes of menstrual disorders in obstetrics and gynecology?",
        "What should cancer patients in the oncology department pay attention to in their diet?"
    ]

    # Execute the test query and print the results
    for query in test_queries:
        print("\n" + "=" * 60)
        print(f"Query question: {query}")
        print("The most similar medical Q&A results: ")
        results = query_chroma(chroma_collection, query, top_k=2)

        for i, res in enumerate(results, 1):
            print(f"\nThe {i} piece（similarity：{res['similarity']:.4f}）")
            print(f"Department：{res['department']}")
            print(f"Related diseases：{', '.join(res['related_disease'])}")
            print(f"User's question：{res['user_query']}")
            print(f"The doctor replied：{res['doctor_answer'][:100]}...")  # Extract the first 100 characters to avoid making the output too long