#!/usr/bin/env python3
"""
精确检查两个JSON文件中的URL是否一一对应（包括重复URL）

功能：
1. 读取accessible_library_urls.json和library_crawled_data_append.json
2. 检查accessible_library_urls.json中的所有URL记录（包括重复的）是否都在library_crawled_data_append.json中存在
3. 找出具体哪些URL记录没有匹配上
"""

import json
from collections import Counter

def load_json_file(file_path):
    """
    加载JSON文件
    
    参数：
        file_path (str): JSON文件路径
    
    返回：
        dict或list: JSON文件内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"错误：读取文件 {file_path} 失败：{e}")
        return None

def extract_all_urls_from_accessible(accessible_data):
    """
    从accessible_library_urls.json中提取所有URL（包括重复的）
    
    参数：
        accessible_data (dict): accessible_library_urls.json的内容
    
    返回：
        list: 所有URL的列表（包括重复的）
    """
    urls = []
    for library, library_urls in accessible_data.items():
        for url in library_urls:
            urls.append(url)
    return urls

def extract_all_urls_from_crawled(crawled_data):
    """
    从library_crawled_data_append.json中提取所有URL（包括重复的）
    
    参数：
        crawled_data (list): library_crawled_data_append.json的内容
    
    返回：
        list: 所有URL的列表（包括重复的）
    """
    urls = []
    for item in crawled_data:
        if 'url' in item:
            urls.append(item['url'])
    return urls

def check_exact_correspondence(accessible_file, crawled_file):
    """
    精确检查两个文件中的URL是否一一对应
    
    参数：
        accessible_file (str): accessible_library_urls.json文件路径
        crawled_file (str): library_crawled_data_append.json文件路径
    """
    # 加载文件
    accessible_data = load_json_file(accessible_file)
    crawled_data = load_json_file(crawled_file)
    
    if not accessible_data or not crawled_data:
        return
    
    # 提取URL列表
    accessible_urls = extract_all_urls_from_accessible(accessible_data)
    crawled_urls = extract_all_urls_from_crawled(crawled_data)
    
    # 使用Counter统计URL出现次数
    accessible_counter = Counter(accessible_urls)
    crawled_counter = Counter(crawled_urls)
    
    # 计算差异
    missing_urls = []
    for url, count in accessible_counter.items():
        if crawled_counter.get(url, 0) < count:
            # 计算缺少的次数
            missing_count = count - crawled_counter.get(url, 0)
            missing_urls.extend([url] * missing_count)
    
    # 输出结果
    print("URL精确对应关系检查结果：")
    print(f"\naccessible_library_urls.json中的URL总数（包括重复）：{len(accessible_urls)}")
    print(f"library_crawled_data_append.json中的URL总数（包括重复）：{len(crawled_urls)}")
    
    if missing_urls:
        print(f"\naccessible_library_urls.json中有 {len(missing_urls)} 个URL记录未在library_crawled_data_append.json中找到匹配：")
        for url in missing_urls:
            print(f"  - {url}")
        
        # 统计每个缺失URL的次数
        missing_counter = Counter(missing_urls)
        print(f"\n缺失URL统计（去重后）：")
        for url, count in missing_counter.items():
            print(f"  {url}: 缺少 {count} 次")
    else:
        print("\naccessible_library_urls.json中的所有URL记录都在library_crawled_data_append.json中找到了匹配")
    
    # 检查是否有额外的URL
    extra_urls = []
    for url, count in crawled_counter.items():
        if accessible_counter.get(url, 0) < count:
            extra_count = count - accessible_counter.get(url, 0)
            extra_urls.extend([url] * extra_count)
    
    if extra_urls:
        print(f"\nlibrary_crawled_data_append.json中有 {len(extra_urls)} 个额外的URL记录不在accessible_library_urls.json中：")
        for url in extra_urls:
            print(f"  - {url}")

if __name__ == "__main__":
    accessible_file = '/Users/bytedance/codesimpleQA_generate-2/data/accessible_library_urls.json'
    crawled_file = '/Users/bytedance/codesimpleQA_generate-2/data/library_crawled_data_append.json'
    check_exact_correspondence(accessible_file, crawled_file)
