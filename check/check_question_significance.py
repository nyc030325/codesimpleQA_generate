#!/usr/bin/env python3
"""
使用gemini-3-pro模型检查simpleqa_dataset_new.csv中所有题目是否有实际含义
- 1表示有意义（正常的问答题目）
- 0表示无意义（特别是答案在题目里面的情况）
"""

import csv
import os
import time
import random
import traceback
import concurrent.futures
from openai import AzureOpenAI
from openai import APIError, RateLimitError
from tqdm import tqdm

# 设置API参数
api_key = "dDBVPJZeExZ8L0GL25J7RPIAGiwLwcrO_GPT_AK"
api_version = "2024-02-01"

# 定义gemini-3-pro模型配置
MODEL_NAME = "gemini-3-pro-preview-new"
model_config = {
    "model_name": MODEL_NAME,
    "endpoint": "https://search.bytedance.net/gpt/openapi/online/v2/crawl",
    "max_tokens": 4096,
    "api_type": "chat"
}

# 创建Azure OpenAI客户端
def create_client():
    """创建Azure OpenAI客户端"""
    return AzureOpenAI(
        api_key=api_key,
        azure_endpoint=model_config["endpoint"],
        api_version=api_version
    )

def check_question_significance(client, problem, answer):
    """
    使用gemini-3-pro模型检查题目是否有意义，带重试机制
    
    参数：
        client: Azure OpenAI客户端
        problem: 题目内容
        answer: 答案内容
    
    返回：
        int: 1表示有意义，0表示无意义
    """
    if not problem or not isinstance(problem, str) or not answer or not isinstance(answer, str):
        return 0
    
    # 构建prompt
    prompt = f"""
    Role: 你是一个专业的题目质量评估专家。
    
    Objective: 分析给定的问答题目是否具有实际的问答意义。
    
    Decision Criteria:
    - 1（有意义）: 题目是一个正常的问答题目，答案需要从题目中推理或通过知识获取，而不是直接包含在题目文本中
    - 0（无意义）: 题目没有实际的问答意义，特别是当答案直接包含在题目文本中的情况
    
    Example Analysis:
    1. 题目: "In LLVM 16.0.0 what new uinc_wrap operation was added to atomicrmw"
       答案: "uinc_wrap"
       评估: 有意义（答案不在题目文本中）
       输出: 1
    
    2. 题目: "In LLVM 16.0.0 what new symbol is specified by Module Flags Metadata stack-protector-guard-symbol"
       答案: "stack-protector-guard-symbol"
       评估: 无意义（答案直接包含在题目文本中）
       输出: 0
    
    Source Data:
    - 题目: {problem}
    - 答案: {answer}
    
    Output Requirement:
    请严格按照以下格式输出：
    仅输出单个数字，1或0，不要添加任何其他文字或解释。
    """
    
    max_retries = 3
    retry_delay = 1.0  # 初始重试延迟
    
    for attempt in range(max_retries):
        try:
            # 添加随机延迟，避免请求峰值
            time.sleep(random.uniform(0.1, 0.5))
            
            # 构建API调用参数
            api_params = {
                "model": model_config["model_name"],
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": model_config["max_tokens"],
                "stream": False,
                "extra_headers": {
                    "X-TT-LOGID": "${your_logid}"
                }
            }
            
            # 调用API
            response = client.chat.completions.create(**api_params)
            
            # 解析响应
            response_text = ""
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
            
            # 确保返回值是1或0
            if response_text == "1":
                return 1
            elif response_text == "0":
                return 0
            else:
                # 如果模型输出不符合预期，默认返回0
                print(f"警告：模型返回非预期值 '{response_text}'，默认返回0")
                return 0
                
        except Exception as e:
            print(f"错误：检查题目时发生异常（第{attempt+1}/{max_retries}次尝试）- {e}")
            
            # 检查是否是429状态码错误
            is_429_error = False
            if isinstance(e, RateLimitError) or "429" in str(e):
                is_429_error = True
                print(f"检测到429状态码（请求频率过高），将等待1分钟后重试...")
                time.sleep(60)  # 429错误时等待1分钟
            elif attempt < max_retries - 1:
                print(f"{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
            
            # 如果是最后一次尝试或429错误但已达到最大重试次数，返回0
            if attempt >= max_retries - 1:
                print(f"已达到最大重试次数，处理失败")
                traceback.print_exc()
                return 0

def process_item(item):
    """
    处理单个数据项，创建客户端并检查题目意义
    
    参数：
        item: 要处理的数据项
    
    返回：
        dict: 处理结果
    """
    problem = item.get('problem', '')
    answer = item.get('answer', '')
    library_name = item.get('library_name', '')
    tag = item.get('tag', '')
    language = item.get('language', '')
    year = item.get('year', '')
    problem_type = item.get('problem_type', '')
    
    # 为每个线程创建独立的客户端，避免并发冲突
    client = create_client()
    
    try:
        significance = check_question_significance(client, problem, answer)
        return {
            "problem": problem,
            "answer": answer,
            "library_name": library_name,
            "tag": tag,
            "language": language,
            "year": year,
            "problem_type": problem_type,
            "significance": significance
        }
    except Exception as e:
        print(f"处理题目 '{problem}' 时发生异常: {e}")
        traceback.print_exc()
        return {
            "problem": problem,
            "answer": answer,
            "library_name": library_name,
            "tag": tag,
            "language": language,
            "year": year,
            "problem_type": problem_type,
            "significance": 0
        }


def main():
    input_file = '/Users/bytedance/codesimpleQA_generate-2/data/simpleqa_dataset_new.csv'
    output_file = '/Users/bytedance/codesimpleQA_generate-2/check/question_significance_results.csv'
    
    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"错误：文件 {input_file} 不存在")
        return
    
    try:
        # 读取CSV文件
        data = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        
        print(f"读取文件成功，共有 {len(data)} 条记录")
        
        # 并发处理数据，设置并发度为16
        results = []
        concurrency = 32
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            # 提交所有任务
            future_to_item = {executor.submit(process_item, item): item for item in data}
            
            # 处理完成的任务
            for future in tqdm(concurrent.futures.as_completed(future_to_item), 
                              total=len(data), desc="检查题目意义"):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"获取任务结果时发生异常: {e}")
                    traceback.print_exc()
        
        # 保存结果
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            fieldnames = ['problem', 'answer', 'library_name', 'tag', 'language', 'year', 'problem_type', 'significance']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow(result)
        
        # 统计结果
        significant_count = sum(1 for r in results if r['significance'] == 1)
        insignificant_count = sum(1 for r in results if r['significance'] == 0)
        
        print(f"\n检查完成！")
        print(f"总记录数：{len(results)}")
        print(f"有意义的题目数：{significant_count}")
        print(f"无意义的题目数：{insignificant_count}")
        print(f"结果已保存到 {output_file}")
        
    except csv.Error as e:
        print(f"错误：CSV解析失败 - {e}")
    except Exception as e:
        print(f"错误：处理文件时发生异常 - {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()