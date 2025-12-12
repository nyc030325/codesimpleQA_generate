#!/usr/bin/env python3
"""
将多行字符串转换为一行字符串的工具

功能：
1. 提供函数接口，将多行字符串转换为一行
2. 支持命令行输入多行字符串进行转换
3. 支持从文件读取多行字符串并转换

使用方法：
1. 作为模块导入：
   from convert_multiline_to_singleline import convert_to_singleline
   result = convert_to_singleline(multiline_str)

2. 命令行直接输入：
   python convert_multiline_to_singleline.py
   然后输入多行字符串，按Ctrl+D（Linux/Mac）或Ctrl+Z（Windows）结束输入

3. 从文件读取：
   python convert_multiline_to_singleline.py --file input.txt
"""

import argparse
import sys

def convert_to_singleline(multiline_str, escape_quotes=True, preserve_newlines=False):
    """
    将多行字符串转换为一行字符串
    
    参数：
        multiline_str (str): 输入的多行字符串
        escape_quotes (bool): 是否转义字符串中的双引号，默认为True
        preserve_newlines (bool): 是否保留换行符为\n转义序列，默认为False
    
    返回：
        str: 转换后的单行字符串
    """
    # 处理换行符
    if preserve_newlines:
        singleline = multiline_str.replace('\r\n', '\n')  # 统一Windows换行符
        singleline = singleline.replace('\r', '\n')  # 处理单独的回车符
        # 保留换行符为转义序列
        singleline = singleline.replace('\n', '\\n')
    else:
        singleline = multiline_str.replace('\r\n', ' ')
        singleline = singleline.replace('\n', ' ')
        singleline = singleline.replace('\r', ' ')
    
    # 转义双引号
    if escape_quotes:
        singleline = singleline.replace('"', '\\"')
    
    # 折叠连续的空格
    import re
    singleline = re.sub(r'\s+', ' ', singleline)
    
    # 去除首尾空格
    return singleline.strip()

def main():
    parser = argparse.ArgumentParser(description='将多行字符串转换为一行字符串')
    parser.add_argument('--file', '-f', type=str, help='输入文件路径')
    parser.add_argument('--preserve-newlines', '-n', action='store_true', help='保留换行符为\\n转义序列')
    parser.add_argument('--no-escape-quotes', action='store_true', help='不转义字符串中的双引号')
    
    args = parser.parse_args()
    
    if args.file:
        # 从文件读取
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"错误：文件 '{args.file}' 不存在")
            sys.exit(1)
        except Exception as e:
            print(f"错误：读取文件时发生异常：{e}")
            sys.exit(1)
    else:
        # 从标准输入读取
        print("请输入多行字符串（按Ctrl+D结束输入）：")
        content = sys.stdin.read()
    
    # 转换
    result = convert_to_singleline(
        content,
        preserve_newlines=args.preserve_newlines,
        escape_quotes=not args.no_escape_quotes
    )
    
    # 输出结果
    print("\n转换结果：")
    print(result)

if __name__ == "__main__":
    main()
