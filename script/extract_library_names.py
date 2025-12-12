import json

# 读取JSON文件
try:
    with open('library_crawled_data_append.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取所有库名
    library_names = set()
    
    # 根据JSON结构不同，可能需要调整提取方式
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 'library_name' in item:
                library_names.add(item['library_name'])
    elif isinstance(data, dict):
        # 如果是嵌套结构，需要递归查找
        def extract_names(obj):
            if isinstance(obj, dict):
                if 'library_name' in obj:
                    library_names.add(obj['library_name'])
                for value in obj.values():
                    extract_names(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_names(item)
        
        extract_names(data)
    
    # 输出结果
    print("提取到的所有库名：")
    for name in sorted(library_names):
        print(f"- {name}")
    
    print(f"\n共提取到 {len(library_names)} 个库名")
    
except Exception as e:
    print(f"处理文件时发生错误：{e}")
