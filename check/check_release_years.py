#!/usr/bin/env python3
"""
检测library_crawled_data_append.json中每一个库对应的三个release_date是否为2023、2024、2025各一个
"""

import json
import re
from collections import defaultdict

def extract_year(release_date):
    """
    从release_date字符串中提取年份
    
    参数：
        release_date: 发布日期字符串
    
    返回：
        int: 提取的年份，如果无法提取则返回None
    """
    if not release_date or not isinstance(release_date, str):
        return None
    
    # 尝试匹配年份（2023-2025）
    match = re.search(r'(202[3-5])', release_date)
    if match:
        return int(match.group(1))
    
    # 尝试匹配 "Unknown release date" 或其他格式
    if "Unknown" in release_date:
        return None
    
    return None

def main():
    # 修改输入文件路径为library_crawled_data_append.json
    input_file = '/Users/bytedance/codesimpleQA_generate-2/data/library_crawled_data_append.json'
    output_file = '/Users/bytedance/codesimpleQA_generate-2/check/invalid_release_years.json'
    
    try:
        # 读取JSON文件
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"读取文件成功，共有 {len(data)} 个条目")
        
        # 将相同library_name的条目分组
        library_groups = defaultdict(list)
        for entry in data:
            library_name = entry.get('library_name', 'Unknown')
            library_groups[library_name].append(entry)
        
        print(f"共包含 {len(library_groups)} 个不同的库")
        
        invalid_libraries = []
        
        for library_name, entries in library_groups.items():
            print(f"\n检查库: {library_name}")
            
            # 检查是否有三个版本
            if len(entries) != 3:
                print(f"  警告: {library_name} 不是三个版本，而是 {len(entries)} 个版本")
                invalid_libraries.append({
                    "library": library_name,
                    "entries": entries,
                    "reason": f"版本数量不正确，应为3个，实际为{len(entries)}个"
                })
                continue
            
            # 提取每个版本的年份
            years = []
            for entry in entries:
                release_date = entry.get('release_date', '')
                year = extract_year(release_date)
                years.append(year)
                
                print(f"  版本: {entry.get('version', '未知')}, 发布日期: {release_date}, 提取年份: {year}")
            
            # 检查年份是否包含2023、2024、2025各一个
            expected_years = {2023, 2024, 2025}
            actual_years = set([y for y in years if y is not None])
            
            if actual_years != expected_years:
                print(f"  错误: {library_name} 的年份分布不正确")
                print(f"  期望年份: {expected_years}")
                print(f"  实际年份: {actual_years}")
                
                invalid_libraries.append({
                    "library": library_name,
                    "entries": entries,
                    "expected_years": list(expected_years),
                    "actual_years": list(actual_years),
                    "years_extracted": years,
                    "reason": "年份分布不符合要求（2023、2024、2025各一个）"
                })
            else:
                print(f"  正确: {library_name} 的年份分布符合要求")
        
        # 保存不符合要求的库到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(invalid_libraries, f, ensure_ascii=False, indent=2)
        
        print(f"\n分析完成！")
        print(f"总共有 {len(invalid_libraries)} 个库不符合年份分布要求")
        print(f"不符合要求的库已保存到 {output_file}")
        
    except json.JSONDecodeError as e:
        print(f"错误：JSON解析失败 - {e}")
    except Exception as e:
        print(f"错误：处理文件时发生异常 - {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
