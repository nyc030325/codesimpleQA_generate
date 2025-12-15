#!/usr/bin/env python3
"""
提取 accessible_library_urls.json 中的所有不同仓库名并打印
"""

import json
import os

def main():
    # 定义文件路径
    file_path = '/Users/bytedance/codesimpleQA_generate-2/data/accessible_library_urls.json'
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误：文件 {file_path} 不存在")
        return
    
    try:
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取所有仓库名（JSON对象的键）
        repository_names = list(data.keys())
        
        # 排序仓库名
        repository_names.sort()
        
        # 打印结果
        print(f"共找到 {len(repository_names)} 个仓库：")
        print("=" * 50)
        for name in repository_names:
            print(name)
        print("=" * 50)
        print(f"总计：{len(repository_names)} 个仓库")
        
    except json.JSONDecodeError as e:
        print(f"JSON解析错误：{e}")
    except Exception as e:
        print(f"发生错误：{e}")

if __name__ == "__main__":
    main()