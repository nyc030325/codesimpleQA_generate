import os
import re

# 定义旧路径到新路径的映射
path_mappings = {
    # 根目录下的JSON文件移动到data目录
    r'"../data/library_crawled_data_append.json"': '"../data/library_crawled_data_append.json"',
    r'"../check/invalid_release_years.json"': '"../check/invalid_release_years.json"',
    r'"../data/specific_library_crawled_data.json"': '"../data/specific_library_crawled_data.json"',
    r'"../data/accessible_library_urls.json"': '"../data/accessible_library_urls.json"',
    r'"../data/all_libraries_crawled_data.json"': '"../data/all_libraries_crawled_data.json"',
    r'"../data/data.json"': '"../data/data.json"',
    r'"../data/simpleqa_dataset_new.csv"': '"../data/simpleqa_dataset_new.csv"',
    
    # 绝对路径更新
    r'/Users/bytedance/codesimpleQA_generate-2/data/library_crawled_data_append.json':
        '/Users/bytedance/codesimpleQA_generate-2/data/library_crawled_data_append.json',
    r'/Users/bytedance/codesimpleQA_generate-2/check/invalid_release_years.json':
        '/Users/bytedance/codesimpleQA_generate-2/check/invalid_release_years.json',
    r'/Users/bytedance/codesimpleQA_generate-2/data/specific_library_crawled_data.json':
        '/Users/bytedance/codesimpleQA_generate-2/data/specific_library_crawled_data.json',
    r'/Users/bytedance/codesimpleQA_generate-2/data/accessible_library_urls.json':
        '/Users/bytedance/codesimpleQA_generate-2/data/accessible_library_urls.json',
    r'/Users/bytedance/codesimpleQA_generate-2/data/all_libraries_crawled_data.json':
        '/Users/bytedance/codesimpleQA_generate-2/data/all_libraries_crawled_data.json',
    r'/Users/bytedance/codesimpleQA_generate-2/data/data.json':
        '/Users/bytedance/codesimpleQA_generate-2/data/data.json',
    r'/Users/bytedance/codesimpleQA_generate-2/data/simpleqa_dataset_new.csv':
        '/Users/bytedance/codesimpleQA_generate-2/data/simpleqa_dataset_new.csv',
}

def update_file_paths(file_path):
    """更新文件中的路径"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 记录是否有修改
    modified = False
    
    # 应用所有路径映射
    for old_path, new_path in path_mappings.items():
        if old_path in content:
            content = content.replace(old_path, new_path)
            modified = True
    
    # 如果有修改，保存文件
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"已更新: {file_path}")
    else:
        print(f"无需更新: {file_path}")

def main():
    # 遍历所有Python文件
    for root, dirs, files in os.walk('/Users/bytedance/codesimpleQA_generate-2'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                update_file_paths(file_path)

if __name__ == "__main__":
    main()
