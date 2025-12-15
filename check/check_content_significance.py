#!/usr/bin/env python3
"""
使用kimi-k2模型检查library_crawled_data_append.json中所有content是否有实际含义
- 1表示有意义（包含版本更新内容）
- 0表示无意义（和版本更新无关）
"""

import json
import os
import time
import random
import traceback
import concurrent.futures
from openai import AzureOpenAI
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

def check_content_significance(client, content, library_name, version):
    """
    使用kimi-k2模型检查content是否有意义，带重试机制
    
    参数：
        client: Azure OpenAI客户端
        content: 要检查的内容
        library_name: 库名
        version: 版本号
    
    返回：
        int: 1表示有意义，0表示无意义
    """
    if not content or not isinstance(content, str):
        return 0
    
    # 构建prompt
    prompt = f"""
    Role: 你是一个专业的软件版本更新内容分析专家。
    
    Objective: 分析给定的文本内容是否包含某个软件库特定版本的实际更新内容。
    
    Decision Criteria:
    - 1（有意义）: 内容确实包含了{library_name} {version}版本的具体更新信息，如新增功能、修复问题、API变更等
    - 0（无意义）: 内容不包含任何与{library_name} {version}版本更新相关的实际信息，比如只有错误信息、空内容、无关文本等
    
    Source Text (要分析的内容):
    {content[:10000]}  # 限制内容长度，避免API调用失败
    
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
            print(f"错误：检查内容时发生异常（第{attempt+1}/{max_retries}次尝试）- {e}")
            if attempt < max_retries - 1:
                print(f"{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
            else:
                print(f"已达到最大重试次数，处理失败")
                traceback.print_exc()
                return 0

def process_item(item):
    """
    处理单个数据项，创建客户端并检查内容意义
    
    参数：
        item: 要处理的数据项
    
    返回：
        dict: 处理结果
    """
    content = item.get('content', '')
    library_name = item.get('library_name', '')
    version = item.get('version', '')
    url = item.get('url', '')
    
    # 为每个线程创建独立的客户端，避免并发冲突
    client = create_client()
    
    try:
        significance = check_content_significance(client, content, library_name, version)
        return {
            "library_name": library_name,
            "version": version,
            "url": url,
            "content_length": len(content),
            "significance": significance
        }
    except Exception as e:
        print(f"处理 {library_name} {version} 时发生异常: {e}")
        traceback.print_exc()
        return {
            "library_name": library_name,
            "version": version,
            "url": url,
            "content_length": len(content),
            "significance": 0
        }


def main():
    input_file = '/Users/bytedance/codesimpleQA_generate-2/data/library_crawled_data_append.json'
    output_file = '/Users/bytedance/codesimpleQA_generate-2/check/content_significance_results.json'
    
    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"错误：文件 {input_file} 不存在")
        return
    
    try:
        # 读取JSON文件
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"读取文件成功，共有 {len(data)} 条记录")
        
        # 并发处理数据，设置并发度为16
        results = []
        concurrency = 16
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            # 提交所有任务
            future_to_item = {executor.submit(process_item, item): item for item in data}
            
            # 处理完成的任务
            for future in tqdm(concurrent.futures.as_completed(future_to_item), 
                              total=len(data), desc="检查内容意义"):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"获取任务结果时发生异常: {e}")
                    traceback.print_exc()
        
        # 保存结果
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 统计结果
        significant_count = sum(1 for r in results if r['significance'] == 1)
        insignificant_count = sum(1 for r in results if r['significance'] == 0)
        
        print(f"\n检查完成！")
        print(f"总记录数：{len(results)}")
        print(f"有意义的内容数：{significant_count}")
        print(f"无意义的内容数：{insignificant_count}")
        print(f"结果已保存到 {output_file}")
        
    except json.JSONDecodeError as e:
        print(f"错误：JSON解析失败 - {e}")
    except Exception as e:
        print(f"错误：处理文件时发生异常 - {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
