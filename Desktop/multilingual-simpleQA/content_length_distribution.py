import json
import os

# 定义文件路径
file_path = "/Users/bytedance/Desktop/multilingual-simpleQA/library_crawled_data_append.json"

# 检查文件是否存在
if not os.path.exists(file_path):
    print(f"文件 {file_path} 不存在")
    exit()

# 读取JSON数据
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except json.JSONDecodeError as e:
    print(f"JSON解析错误: {e}")
    exit()

# 提取所有content字段的长度，并记录索引和库名
content_info = []
content_lengths = []
for index, item in enumerate(data):
    if isinstance(item, dict) and 'content' in item:
        length = len(item['content'])
        content_lengths.append(length)
        # 记录索引、长度和库名（如果有）
        library_name = item.get('library_name', '未知库')
        url = item.get('url', '未知URL')
        content_info.append({
            'index': index,
            'length': length,
            'library_name': library_name,
            'url': url
        })

# 定义长度区间（可以根据实际情况调整）
intervals = [
    (0, 500),
    (500, 1000),
    (1000, 5000),
    (5000, 10000),
    (10000, 20000),
    (20000, 50000),
    (50000, float('inf'))
]

# 统计每个区间的数量
distribution = {}
for start, end in intervals:
    count = sum(1 for length in content_lengths if start <= length < end)
    if end == float('inf'):
        interval_name = f"{start}+"
    else:
        interval_name = f"{start}-{end}"
    distribution[interval_name] = count

# 计算总数量和平均长度
total_items = len(content_lengths)
average_length = sum(content_lengths) / total_items if total_items > 0 else 0
max_length = max(content_lengths) if content_lengths else 0
min_length = min(content_lengths) if content_lengths else 0

# 输出结果
print("Content字段长度分布统计")
print("=" * 50)
print(f"总条目数: {total_items}")
print(f"平均长度: {average_length:.2f} 字符")
print(f"最大长度: {max_length} 字符")
print(f"最小长度: {min_length} 字符")
print("\n长度区间分布:")
print("-" * 30)
for interval, count in distribution.items():
    percentage = (count / total_items) * 100 if total_items > 0 else 0
    print(f"{interval}: {count} 个 ({percentage:.1f}%)")

# 打印所有500字符以内的具体长度值，并将内容保存到文件
short_content_entries = [item for item in content_info if item['length'] < 500]
if short_content_entries:
    print("\n500字符以内的具体长度值:")
    print("-" * 30)
    # 排序后打印
    short_content_entries.sort(key=lambda x: x['length'])
    
    # 打开文件保存短内容
    output_file = "/Users/bytedance/Desktop/multilingual-simpleQA/short_content_entries.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, entry in enumerate(short_content_entries, 1):
            print(f"第{i}条: {entry['length']} 字符, Library: {entry['library_name']}, Version: {entry.get('version', 'N/A')}")
            
            # 写入文件
            f.write(f"=== 条目 {i} ===\n")
            f.write(f"库名: {entry['library_name']}\n")
            f.write(f"版本: {entry.get('version', 'N/A')}\n")
            f.write(f"URL: {entry['url']}\n")
            f.write(f"长度: {entry['length']} 字符\n")
            f.write(f"内容:\n{data[entry['index']]['content']}\n")
            f.write("\n" + "="*50 + "\n\n")
    
    print(f"\n已将所有500字符以内的内容保存到: {output_file}")
else:
    print("\n没有500字符以内的内容")

# 查找长度为246的content字段
print("\n查找长度为246的content字段:")
print("-" * 30)
found_items = [item for item in content_info if item['length'] == 246]
if found_items:
    for item in found_items:
        print(f"索引: {item['index']}")
        print(f"库名: {item['library_name']}")
        print(f"URL: {item['url']}")
        # 打印完整内容
        print(f"完整内容: {data[item['index']]['content']}")
        print("-" * 30)
else:
    print("没有找到长度为246的content字段")

# 打印所有小于500字符的content完整信息
print("\n所有小于500字符的content信息:")
print("=" * 50)
short_items = [item for item in content_info if item['length'] < 500]
if short_items:
    for item in short_items:
        print(f"\n索引: {item['index']}")
        print(f"库名: {item['library_name']}")
        print(f"URL: {item['url']}")
        print(f"长度: {item['length']} 字符")
        print(f"完整内容: {data[item['index']]['content']}")
        print("-" * 30)
else:
    print("\n没有找到小于500字符的content字段")

print("=" * 50)