#!/usr/bin/env python3
"""
删除CSV文件的最后一列
"""

import csv
import os

input_file = '/Users/bytedance/codesimpleQA_generate-2/data/simpleqa_dataset_new.csv'
output_file = '/Users/bytedance/codesimpleQA_generate-2/data/simpleqa_dataset_new.csv'  # 覆盖原文件

# 读取原始文件并处理行
with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

if not rows:
    print("文件为空")
    exit()

# 删除最后一列
processed_rows = [row[:-1] for row in rows]

# 写入处理后的内容
with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(processed_rows)

print(f"已成功删除 {input_file} 的最后一列")
print(f"处理后文件已保存到 {output_file}")
print(f"原列数: {len(rows[0])}, 新列数: {len(processed_rows[0])}")