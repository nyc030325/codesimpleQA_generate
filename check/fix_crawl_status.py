#!/usr/bin/env python3
"""
处理library_crawled_data_append.json文件
- 将所有title为"爬取失败"的条目换为空字符串
- 相应的crawl_status换成"success"
"""

import json
import os

def main():
    file_path = '/Users/bytedance/codesimpleQA_generate-2/data/library_crawled_data_append.json'
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误：文件 {file_path} 不存在")
        return
    
    try:
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"读取文件成功，共有 {len(data)} 条记录")
        
        # 处理数据
        modified_count = 0
        for item in data:
            # 检查title是否为"爬取失败"
            if isinstance(item.get('title'), str) and item['title'] == "爬取失败":
                item['title'] = ""
                item['crawl_status'] = "success"
                modified_count += 1
        
        print(f"已修改 {modified_count} 条记录")
        
        # 保存修改后的文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"文件已成功保存到 {file_path}")
        
    except json.JSONDecodeError as e:
        print(f"错误：JSON解析失败 - {e}")
    except Exception as e:
        print(f"错误：处理文件时发生异常 - {e}")

if __name__ == "__main__":
    main()
