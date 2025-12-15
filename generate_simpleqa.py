import json
import csv
import os
import argparse
from openai import AzureOpenAI, APIError
import time
import traceback
import concurrent.futures
from tqdm import tqdm
import threading

# 设置API参数（使用用户提供的Azure OpenAI接口配置）
api_key = "dDBVPJZeExZ8L0GL25J7RPIAGiwLwcrO_GPT_AK"
api_version = "2024-03-01-preview"

# 定义可用的模型配置
# 可以通过修改DEFAULT_MODEL变量来选择使用哪个模型
DEFAULT_MODEL = "gemini-2.5-pro"  # 可选：gemini-2.5-pro, gemini-3-pro-preview-new, glm-4.6, o3-pro-2025-06-10, kimi-k2-0905-preview

# 模型配置
model_configs = {
    "gemini-2.5-pro": {
        "endpoint": "https://search.bytedance.net/gpt/openapi/online/v2/crawl",
        "max_tokens": 4096,
        "thinking": {
            "include_thoughts": True,
            "budget_tokens": 2000  # 设置为0可关闭thinking功能
        },
        "api_type": "chat"  # 使用chat.completions.create API
    },
    "gemini-3-pro-preview-new": {
        "endpoint": "https://search.bytedance.net/gpt/openapi/online/v2/crawl",
        "max_tokens": 4096,
        "thinking": {
            "include_thoughts": True,
            "budget_tokens": 2000  # 设置为0可关闭thinking功能
        },
        "api_type": "chat"  # 使用chat.completions.create API
    },
    "glm-4.6": {
        "endpoint": "https://search.bytedance.net/gpt/openapi/online/v2/crawl/openai/deployments/gpt_openapi",
        "max_tokens": 4000,
        "thinking": None,  # GLM模型不支持thinking功能
        "api_type": "chat"  # 使用chat.completions.create API
    },
    "o3-pro-2025-06-10": {
        "endpoint": "https://search.bytedance.net/gpt/openapi/online/responses",
        "max_tokens": 4096,
        "thinking": None,  # o3-pro模型不使用thinking功能
        "api_type": "responses"  # 使用responses.create API
    },
    "kimi-k2-0905-preview": {
        "endpoint": "https://search.bytedance.net/gpt/openapi/online/v2/crawl/openai/deployments/gpt_openapi",
        "max_tokens": 4095,  # 用户提供的测试代码中使用的范围是[1, 4095]
        "thinking": None,  # Kimi模型不支持thinking功能
        "api_type": "chat"  # 使用chat.completions.create API
    }
}

def get_year_from_release_date(release_date):
    """从发布日期提取年份"""
    if release_date and len(release_date) >= 4:
        return release_date[:4]
    return "2024"  # 默认值

def get_year_from_version(version):
    """从版本号推测年份"""
    version_str = str(version)
    if "2023" in version_str:
        return "2023"
    elif "2024" in version_str:
        return "2024"
    elif "2025" in version_str:
        return "2025"
    # 根据版本号模式推测
    if version_str.startswith("v1.2") or version_str.startswith("1.2"):
        return "2023"
    elif version_str.startswith("v2.0") or version_str.startswith("2.0"):
        return "2024"
    elif version_str.startswith("v2.3") or version_str.startswith("2.3"):
        return "2025"
    return "2024"  # 默认值

def generate_questions_for_content(content, library_name, tag, version, release_date, fixed_year=None, model=None):
    """为给定内容生成2个SimpleQA问题"""
    max_retries = 20  # 最大重试次数
    retry_count = 0
    questions = []
    
    while retry_count < max_retries:
        try:
            # 使用指定的模型或默认模型
            current_model = model or DEFAULT_MODEL
            
            # 获取模型配置
            if current_model not in model_configs:
                raise ValueError(f"不支持的模型: {current_model}")
            
            config = model_configs[current_model]
            
            # 创建Azure OpenAI客户端
            client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=config["endpoint"],
                api_version=api_version
            )

            # 使用固定年份（如果提供），否则使用原来的逻辑
            if fixed_year:
                year = fixed_year
            else:
                # 提取年份
                year = get_year_from_release_date(release_date)
                if year == "2024":
                    year = get_year_from_version(version)

            # 构建prompt
            # 读取data.json内容作为输入数据源
            with open('data/data.json', 'r', encoding='utf-8') as f:
                data_json_content = f.read()
            
            prompt = f"""
Role: You are a Senior Python Ecosystem Expert.

Objective: Create a "Hard Mode" Benchmark Dataset for Python Ecosystem libraries, focusing on their evolution from 2023 to 2025.

Input Data (Source of Truth):
Use this JSON list to populate the library_name and tag columns in your output. Do not infer tags yourself; strictly use this data.
{data_json_content}

GENERATION INSTRUCTIONS
Your task is to generate exactly 2 SimpleQA Questions based on the Source Material for Generation provided below.

CRITICAL QUESTION GENERATION RULES:
Follow these examples, which are derived from the source text, to understand the quality requirements.

*   **Unique, Unambiguous Answer:** The question must be precise.
*   **Timelessness via Versioning:** Every question MUST specify the exact library version.
    *   ❌ Bad: "In Pre-commit what new command line option was added to pre-commit run" (No version specified, answer may vary across versions.)
    *   ✅ Good: "In Pre-commit 4.4.0 what new command line option was added to pre-commit run" (Version-specific, answer is tied to this exact release.)
*   **Specific, Non-Binary Answers:** The answer must be a specific term, not "Yes/No".
*   **No Answer in Question:** The question text must not contain the exact answer.
*   **Target Singular Changes to Omit Description (ULTIMATE HARD MODE):** Prefer to ask about a change that is the only one of its kind in the update (e.g., the only new parameter to a function, the only new command-line option). This allows you to omit the functional description, creating the hardest type of question. **This 'ULTIMATE HARD MODE' rule is the most critical principle for question generation; you must actively seek and prioritize opportunities to apply it.**
    *   ❌ Bad: "In Pre-commit 4.4.0 what new command line option was added to pre-commit run to stop immediately on failure?" (The description "stop immediately on failure" is a dead giveaway for --fail-fast.)
    *   ✅ Good (if it's the only new option): "In Pre-commit 4.4.0 what new command line option was added to pre-commit run" (Extremely difficult. This is only a valid question if it was the single new option, forcing the model to identify this unique fact from the notes, not guess from a description.)

PROBLEM TYPE DEFINITIONS:
- API: Questions concerning specific code signatures, such as function arguments, method names, class attributes, or return types.
- General: Questions concerning high-level behavior, logic changes, CLI commands, configuration settings, or deprecations.

Additional Constraints:

*   The generated problem text must not contain any commas.
*   **Question Distribution Constraints:**
    *   At most 1 question can be type "API".
    *   The remaining question(s) must be type "General".

SOURCE MATERIAL FOR GENERATION

Both the questions you formulate and the answers you provide must be derived directly from the following release notes. This is your single source of truth.

[Library Version]
{version}

[Library Release Notes]
{content[:30000]}

OUTPUT FORMAT
Output must be in plain CSV format without any additional text, explanation, or markdown code block markers.

CRITICAL CSV FORMAT REQUIREMENTS:

*   Each row must contain exactly 7 fields.
*   Fields must be in this exact order: `problem,answer,library_name,tag,language,year,problem_type`
*   Do not add any extra commas or fields.

Columns:

*   `problem`: The question text (Max 30 words).
*   `answer`: The short answer (Max 6 words).
*   `library_name`: Must match exactly: `{library_name}`
*   `tag`: Must match exactly: `{tag}`
*   `language`: Always "Python".
*   `year`: Must match exactly: `{year}`
*   `problem_type`: "API" or "General".

Example Output:
problem,answer,library_name,tag,language,year,problem_type
In Pre-commit 4.4.0 what new command line option was added to pre-commit run,--fail-fast,Pre-commit,NICHE,Python,2025,General

FINAL REMINDERS:
1. Generate ONLY the CSV output without any additional text, explanation, or markdown code block markers.
2. Generate questions that are as challenging as possible. Ideally, the answers should only apply to the current specific version, rather than long-standing facts about the library. This ensures that the questions truly test understanding of the provided version descriptions.
3. Strictly adhere to the Target Singular Changes to Omit Description rule.
"""

            # 构建API调用参数
            if config["api_type"] == "responses":
                # 使用responses.create API格式
                content = [
                    {
                        "type": "input_text",
                        "text": prompt
                    }
                ]
                api_params = {
                    "model": current_model,
                    "input": [
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    "extra_headers": {
                        "X-TT-LOGID": "${your_logid}"
                    }
                }
                # 调用API
                response = client.responses.create(**api_params)
            else:
                # 使用chat.completions.create API格式
                # 根据模型类型设置不同的content格式
                if current_model == "glm-4.6":
                    # GLM模型需要特殊的content格式
                    content = [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                else:
                    # Gemini模型使用常规字符串格式
                    content = prompt
                    
                api_params = {
                    "model": current_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    "max_tokens": config["max_tokens"],
                    "stream": False,
                    "extra_headers": {
                        "X-TT-LOGID": "${your_logid}"
                    }
                }
                
                # 如果模型支持thinking功能，添加thinking参数
                if config["thinking"] is not None:
                    api_params["extra_body"] = {
                        "thinking": config["thinking"]
                    }
                
                # 调用API
                response = client.chat.completions.create(**api_params)

            # 解析响应
            response_text = ""
            if config["api_type"] == "responses":
                # 解析responses.create API的响应（如o3-pro-2025-06-10）
                try:
                    # 尝试多种可能的响应格式
                    if hasattr(response, 'output') and isinstance(response.output, list):
                        for output_item in response.output:
                            if hasattr(output_item, 'content'):
                                if isinstance(output_item.content, list):
                                    for content_item in output_item.content:
                                        if hasattr(content_item, 'text'):
                                            response_text += content_item.text
                                elif isinstance(output_item.content, str):
                                    response_text += output_item.content
                    elif hasattr(response, 'choices') and response.choices:
                        # 兼容chat API格式
                        choice = response.choices[0]
                        if hasattr(choice, 'content'):
                            if isinstance(choice.content, list):
                                for item in choice.content:
                                    if hasattr(item, 'text'):
                                        response_text += item.text
                            else:
                                response_text += choice.content.strip()
                        elif hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                            if isinstance(choice.message.content, list):
                                for item in choice.message.content:
                                    if hasattr(item, 'text'):
                                        response_text += item.text
                            else:
                                response_text += choice.message.content.strip()
                    elif hasattr(response, 'content'):
                        # 直接获取content属性
                        if isinstance(response.content, str):
                            response_text = response.content.strip()
                except Exception as e:
                    print(f"Error parsing o3-pro response: {e}")
                    traceback.print_exc()
            else:
                # 解析chat.completions.create API的响应
                if hasattr(response, 'choices') and response.choices:
                    choice = response.choices[0]
                    if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                        if isinstance(choice.message.content, list):
                            # 处理内容列表
                            for item in choice.message.content:
                                if hasattr(item, 'text'):
                                    response_text += item.text
                        else:
                            response_text = choice.message.content.strip()
            print(f"Response received for {library_name} {version}:")
            print("Raw response text:")
            print(repr(response_text))

            # 处理CSV输出
            csv_lines = response_text.splitlines()
            questions = []
            for line in csv_lines:
                line = line.strip()
                if line and not line.startswith("problem,answer"):
                    try:
                        # 解析CSV行
                        parts = list(csv.reader([line]))[0]
                        print(f"Line: {repr(line)}")
                        print(f"Parsed parts: {len(parts)} - {parts}")
                        if len(parts) >= 7:
                            questions.append(parts)
                            # 每个URL最多生成2个问题
                            if len(questions) >= 2:
                                break
                    except Exception as e:
                        print(f"Error parsing CSV line: {e}")
                        continue

            # 检查是否生成了至少2个有效问题
            if len(questions) >= 2:
                print(f"✓ 成功生成了 {len(questions)} 个有效问题，满足要求！")
                return questions[:2]  # 确保只返回前2个问题
            else:
                retry_count += 1
                print(f"⚠️  只生成了 {len(questions)} 个有效问题，需要重试（{retry_count}/{max_retries}）...")
                if retry_count < max_retries:
                    time.sleep(2)  # 重试前等待2秒

        except APIError as e:
            retry_count += 1
            print(f"API Error generating questions for {library_name} {version}: {e}")
            traceback.print_exc()
            if retry_count < max_retries:
                # 检查是否为429错误（QPM超过限制）
                if e.status_code == 429:
                    print(f"遇到429错误（QPM超过限制），将在60秒后重试...")
                    time.sleep(60)  # 429错误时等待60秒
                else:
                    print(f"需要重试（{retry_count}/{max_retries}）...")
                    time.sleep(2)  # 其他错误时等待2秒
            else:
                print(f"达到最大重试次数，放弃重试")
                return []
        except Exception as e:
            retry_count += 1
            print(f"Error generating questions for {library_name} {version}: {e}")
            traceback.print_exc()
            if retry_count < max_retries:
                print(f"需要重试（{retry_count}/{max_retries}）...")
                time.sleep(2)  # 重试前等待2秒
            else:
                print(f"达到最大重试次数，放弃重试")
                return []
    
    # 如果达到最大重试次数仍然没有生成2个有效问题，返回当前生成的问题
    print(f"⚠️  达到最大重试次数，仅生成了 {len(questions)} 个有效问题")
    return questions

def process_entry(entry, library_info, model=None):
    """处理单个条目，生成问题"""
    library_name = entry.get("library_name", "")
    if library_name not in library_info:
        print(f"Warning: Library {library_name} not found in data.json")
        return []

    content = entry.get("content", "")
    if not content:
        print(f"Warning: No content for {library_name} {entry.get('version', '')}")
        return []

    # 获取library信息
    info = library_info[library_name]
    tag = info["tag"]
    language = info["language"]

    # 获取版本、发布日期和固定年份
    version = entry.get("version", "")
    release_date = entry.get("release_date", "")
    fixed_year = entry.get("fixed_year")

    print(f"\nProcessing {library_name} {version}...")
    questions = generate_questions_for_content(content, library_name, tag, version, release_date, fixed_year, model)
    return questions

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='生成SimpleQA数据集')
    parser.add_argument('-m', '--model', type=str, choices=list(model_configs.keys()), 
                      default=DEFAULT_MODEL, help=f'选择使用的模型，默认为{DEFAULT_MODEL}')
    parser.add_argument('-i', '--input', type=str, 
                      default='data/library_crawled_data_append.json', 
                      help='输入文件路径，默认为data/library_crawled_data_append.json')
    parser.add_argument('-o', '--output', type=str, 
                      default='data/simpleqa_dataset_new.csv', 
                      help='输出文件路径，默认为data/simpleqa_dataset_new.csv')
    parser.add_argument('-w', '--workers', type=int, 
                      default=32, help='并行处理的最大线程数，默认为32')
    parser.add_argument('-n', '--num_entries', type=int, 
                      default=None, help='只处理前n个条目，默认处理所有条目')
    
    args = parser.parse_args()
    
    # 读取library信息
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.normpath(os.path.join(script_dir, "data/data.json"))
    with open(data_file, 'r', encoding='utf-8') as f:
        library_data = json.load(f)

    # 创建library信息映射
    library_info = {}
    for item in library_data:
        library_info[item["name"]] = {
            "tag": item["tag"],
            "language": item["language"]
        }

    # 读取爬取的数据
    with open(args.input, 'r', encoding='utf-8') as f:
        crawled_data = json.load(f)
    
    # 只处理前n个条目（如果指定了）
    if args.num_entries is not None:
        print(f"只处理前 {args.num_entries} 个条目")
        crawled_data = crawled_data[:args.num_entries]
    
    # 读取accessible_library_urls.json文件，用于获取URL与年份的对应关系
    script_dir = os.path.dirname(os.path.abspath(__file__))
    accessible_file = os.path.normpath(os.path.join(script_dir, "data/accessible_library_urls.json"))
    with open(accessible_file, 'r', encoding='utf-8') as f:
        accessible_urls = json.load(f)
    
    # 为每个库创建URL到年份的映射字典（顺序：0→2023，1→2024，2→2025）
    url_year_mapping = {}
    for library_name, urls in accessible_urls.items():
        for idx, url in enumerate(urls):
            year = 2023 + idx  # 确保顺序为2023、2024、2025
            url_year_mapping[(library_name, url)] = str(year)
    
    # 为每个条目分配正确的年份
    modified_crawled_data = []
    for entry in crawled_data:
        library_name = entry.get("library_name", "")
        url = entry.get("url", "")
        key = (library_name, url)
        
        # 根据URL在accessible_library_urls.json中的位置分配年份
        if key in url_year_mapping:
            entry["fixed_year"] = url_year_mapping[key]
        else:
            # 如果找不到对应关系，使用默认的循环分配
            print(f"Warning: Could not find year for {library_name} - {url}")
            entry["fixed_year"] = "2023"  # 默认值
        
        modified_crawled_data.append(entry)

    # 创建输出CSV文件
    output_file = args.output
    # 写入表头
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["problem", "answer", "library_name", "tag", "language", "year", "problem_type"])

    # 使用多线程并行处理条目
    max_workers = args.workers  # 设置最大并发数，避免API限流
    processed_count = 0
    csv_lock = threading.Lock()  # 用于保护CSV写入的线程锁
    
    print(f"\nProcessing {len(modified_crawled_data)} entries with {max_workers} concurrent threads...")
    print(f"Using model: {args.model}")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_entry = {
            executor.submit(process_entry, entry, library_info, args.model): entry 
            for entry in modified_crawled_data
        }
        
        # 处理完成的任务
        for future in tqdm(concurrent.futures.as_completed(future_to_entry), total=len(modified_crawled_data)):
            entry = future_to_entry[future]
            try:
                questions = future.result()
                if questions:
                    processed_count += 1
                    # 立即将结果写入CSV，使用锁确保线程安全
                    with csv_lock, open(output_file, 'a', newline='', encoding='utf-8') as csvfile:
                        csvwriter = csv.writer(csvfile)
                        for question in questions:
                            csvwriter.writerow(question)
            except Exception as e:
                library_name = entry.get("library_name", "Unknown")
                version = entry.get("version", "Unknown")
                print(f"Error processing {library_name} {version}: {e}")
    
    print(f"Processed {processed_count}/{len(modified_crawled_data)} entries")

    print(f"\nSimpleQA dataset generated successfully: {output_file}")
    print(f"Processed {processed_count} entries")

if __name__ == "__main__":
    main()
