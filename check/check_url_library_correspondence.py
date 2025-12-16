#!/usr/bin/env python3
"""
使用kimi-k2模型检查accessible_library_urls.json中库名和URL的对应性
- 检测URL是否与库名对应
- 将不对应的结果保存到文件中
"""

import json
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
api_version = "2024-03-01-preview"

# 定义kimi-k2模型配置
model_config = {
    "model_name": "kimi-k2-0905-preview",
    "endpoint": "https://search.bytedance.net/gpt/openapi/online/v2/crawl/openai/deployments/gpt_openapi",
    "max_tokens": 4095,
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

def check_url_correspondence(client, library_name, url):
    """
    使用kimi-k2模型检查URL是否与库名对应，带重试机制
    
    参数：
        client: Azure OpenAI客户端
        library_name: 库名
        url: 要检查的URL
    
    返回：
        bool: True表示对应，False表示不对应
    """
    if not url or not isinstance(url, str):
        return False
    
    # 构建prompt
    prompt = f"""
    Role: 你是一个专业的软件库和URL对应关系分析专家。
    
    Objective: 分析给定的URL是否与指定的软件库名称对应。
    
    Decision Criteria:
    - True（对应）: URL确实指向{library_name}软件库的相关页面（如GitHub发布页、官方文档等），库名通常会在URL路径中体现
    - False（不对应）: URL不指向{library_name}软件库的页面，或者URL中没有任何与{library_name}相关的标识
    
    Source URL (要分析的URL):
    {url}
    
    Output Requirement:
    请严格按照以下格式输出：
    仅输出单个布尔值，True或False，不要添加任何其他文字或解释。
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
                    response_text = choice.message.content.strip()
            
            # 确保返回值是True或False
            if response_text.lower() == "true":
                return True
            elif response_text.lower() == "false":
                return False
            else:
                # 如果模型输出不符合预期，默认返回False
                print(f"警告：模型返回非预期值 '{response_text}'，默认返回False")
                return False
                
        except Exception as e:
            print(f"错误：检查URL对应性时发生异常（第{attempt+1}/{max_retries}次尝试）- {e}")
            
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
            
            # 如果是最后一次尝试或429错误但已达到最大重试次数，返回False
            if attempt >= max_retries - 1:
                print(f"已达到最大重试次数，处理失败")
                traceback.print_exc()
                return False


def process_item(item):
    """
    处理单个数据项，创建客户端并检查URL对应性
    
    参数：
        item: 要处理的数据项，格式为 (library_name, url)
    
    返回：
        dict: 处理结果
    """
    library_name, url = item
    
    # 为每个线程创建独立的客户端，避免并发冲突
    client = create_client()
    
    try:
        is_corresponding = check_url_correspondence(client, library_name, url)
        return {
            "library_name": library_name,
            "url": url,
            "is_corresponding": is_corresponding
        }
    except Exception as e:
        print(f"处理 {library_name} - {url} 时发生异常: {e}")
        traceback.print_exc()
        return {
            "library_name": library_name,
            "url": url,
            "is_corresponding": False
        }


def main():
    input_file = '/Users/bytedance/codesimpleQA_generate-2/data/accessible_library_urls.json'
    output_file = '/Users/bytedance/codesimpleQA_generate-2/check/url_correspondence_results.json'
    mismatched_file = '/Users/bytedance/codesimpleQA_generate-2/check/mismatched_urls.json'
    
    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"错误：文件 {input_file} 不存在")
        return
    
    try:
        # 读取JSON文件
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 准备要处理的项目列表
        items = []
        for library_name, urls in data.items():
            for url in urls:
                items.append((library_name, url))
        
        print(f"读取文件成功，共有 {len(items)} 条URL需要检查")
        
        # 并发处理数据，设置并发度为16
        results = []
        concurrency = 16
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            # 提交所有任务
            future_to_item = {executor.submit(process_item, item): item for item in items}
            
            # 处理完成的任务
            for future in tqdm(concurrent.futures.as_completed(future_to_item), 
                              total=len(items), desc="检查URL对应性"):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"获取任务结果时发生异常: {e}")
                    traceback.print_exc()
        
        # 保存所有结果
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 筛选出不对应的URL
        mismatched_results = [r for r in results if not r['is_corresponding']]
        
        # 保存不对应的结果
        with open(mismatched_file, 'w', encoding='utf-8') as f:
            json.dump(mismatched_results, f, ensure_ascii=False, indent=2)
        
        # 统计结果
        total_count = len(results)
        corresponding_count = sum(1 for r in results if r['is_corresponding'])
        mismatched_count = len(mismatched_results)
        
        print(f"\n检查完成！")
        print(f"总URL数：{total_count}")
        print(f"对应URL数：{corresponding_count}")
        print(f"不对应URL数：{mismatched_count}")
        print(f"所有结果已保存到 {output_file}")
        print(f"不对应结果已保存到 {mismatched_file}")
        
    except json.JSONDecodeError as e:
        print(f"错误：JSON解析失败 - {e}")
    except Exception as e:
        print(f"错误：处理文件时发生异常 - {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
