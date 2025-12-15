import json

# 读取爬取的数据
with open('data/library_crawled_data_append.json', 'r', encoding='utf-8') as f:
    crawled_data = json.load(f)

print(f"总条目数: {len(crawled_data)}")

# 统计content相同的条目
duplicate_content = {}
for entry in crawled_data:
    content = entry.get('content', '')
    if content:
        if content in duplicate_content:
            duplicate_content[content].append(entry)
        else:
            duplicate_content[content] = [entry]

# 统计有重复content的条目数
duplicate_count = 0
for content, entries in duplicate_content.items():
    if len(entries) > 1:
        duplicate_count += 1
        print(f"\n找到 {len(entries)} 个条目具有相同的content:")
        print(f"Content长度: {len(content)} 字符")
        for entry in entries:
            print(f"  - Library: {entry.get('library_name')}, Version: {entry.get('version')}, URL: {entry.get('url')}")

print(f"\n共有 {duplicate_count} 组重复的content")
