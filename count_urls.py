import json

# Load the accessible library URLs
with open('/Users/bytedance/Desktop/multilingual-simpleQA/accessible_library_urls.json', 'r') as f:
    accessible_urls = json.load(f)

# Count libraries with less than 3 URLs
print("Libraries with less than 3 accessible URLs:")
print("-" * 60)

count = 0
for lib_name, urls in accessible_urls.items():
    if len(urls) < 3:
        count += 1
        print(f"{lib_name}: {len(urls)} URLs")

print("-" * 60)
print(f"Total libraries with less than 3 URLs: {count}")
print(f"Total libraries with accessible URLs: {len(accessible_urls)}")