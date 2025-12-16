import json
import sys

# 读取JSON文件
file_path = '/Users/bytedance/codesimpleQA_generate-2/data/accessible_library_urls.json'
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception as e:
    print(f"读取文件失败: {e}")
    sys.exit(1)

# 提取所有URL
all_urls = []
for library_name, urls in data.items():
    all_urls.extend(urls)

# 检查重复
url_count = {}
for url in all_urls:
    url_count[url] = url_count.get(url, 0) + 1

# 收集重复的URL
duplicate_urls = [url for url, count in url_count.items() if count > 1]

# 打印结果
if duplicate_urls:
    print("有")
    print("重复的URL列表：")
    for url in duplicate_urls:
        print(f"  - {url} (出现{url_count[url]}次)")
else:
    print("无")