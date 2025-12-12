#!/usr/bin/env python3
"""
找出accessible_library_urls.json文件中重复的URL
"""

import json
from collections import defaultdict

def main():
    # 读取JSON文件
    with open('/Users/bytedance/codesimpleQA_generate-2/data/accessible_library_urls.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 统计每个URL出现的次数和所属的库
    url_to_libraries = defaultdict(list)
    all_urls = []
    
    for library, urls in data.items():
        for url in urls:
            url_to_libraries[url].append(library)
            all_urls.append(url)
    
    print(f"总共有 {len(all_urls)} 个URL记录")
    print(f"总共有 {len(url_to_libraries)} 个唯一URL")
    
    # 找出重复的URL
    duplicate_urls = {url: libraries for url, libraries in url_to_libraries.items() if len(libraries) > 1}
    
    if duplicate_urls:
        print(f"\n发现 {len(duplicate_urls)} 个重复的URL：")
        for url, libraries in duplicate_urls.items():
            print(f"\nURL: {url}")
            print(f"重复次数: {len(libraries)}")
            print(f"所属库: {', '.join(libraries)}")
    else:
        print("\n没有发现重复的URL")

if __name__ == "__main__":
    main()
