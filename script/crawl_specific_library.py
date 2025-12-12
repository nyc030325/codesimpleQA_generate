import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random
from tqdm import tqdm
import concurrent.futures
import sys

def read_accessible_urls():
    """读取accessible_library_urls.json文件"""
    # 使用脚本所在目录的绝对路径来构建文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "../data/accessible_library_urls.json")
    file_path = os.path.normpath(file_path)  # 规范化路径
    if not os.path.exists(file_path):
        print(f"文件未找到: {file_path}")
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def crawl_url(url, library_name, max_retries=3):
    """爬取单个URL的内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for attempt in range(max_retries):
        try:
            # 添加随机延迟避免被封禁
            time.sleep(random.uniform(0.5, 2.0))
            
            # 发送请求获取页面内容
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()  # 检查请求是否成功
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取页面标题
            title = soup.title.string if soup.title else "No title found"
            
            # 提取主要内容（根据不同网站结构调整）
            content_text = "No content found"
            
            # 处理GitHub release页面
            if "github.com" in url and "/releases/tag/" in url:
                # 尝试多种GitHub发布页面结构
                github_selectors = [
                    '.markdown-body',  # 标准GitHub发布说明
                    '.release-body',  # 发布内容
                    '.Box-body',  # 通用Box结构
                    '.release-desc',  # 发布描述
                    '#release-body'  # 发布内容ID
                ]
                
                for selector in github_selectors:
                    release_content = soup.select_one(selector)
                    if release_content:
                        content_text = release_content.get_text(separator='\n', strip=True)
                        if content_text.strip():
                            break
                        else:
                            continue
                
                # 如果没有找到内容，尝试查找所有段落和标题
                if content_text == "No content found":
                    text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'code', 'pre'])
                    if text_elements:
                        content_text = '\n'.join([elem.get_text().strip() for elem in text_elements if elem.get_text().strip()])
                        if not content_text.strip():
                            content_text = "No content found"
            
            # 处理文档页面
            elif any(doc_site in url for doc_site in ["docs.", ".readthedocs.io", "tiangolo.com", "palletsprojects.com", "python-poetry.org", "networkx.org", "matplotlib.org", "pydata.org", "scikit-learn.org", "alembic.sqlalchemy.org", "scrapy.org"]):
                # 特殊处理Scrapy带锚点的URL
                if "scrapy.org" in url and "#" in url:
                    # 获取锚点
                    anchor = url.split("#")[1]
                    
                    # 尝试直接通过ID选择器获取特定版本的内容
                    version_section = soup.select_one(f"#{anchor}")
                    if version_section:
                        # 对于Scrapy的版本页面，不仅要提取版本标题，还要提取后续内容
                        content_text = version_section.get_text(separator='\n', strip=True)
                        
                        # 查找当前版本部分的下一个兄弟元素，直到找到下一个版本部分
                        current = version_section.next_sibling
                        while current:
                            # 如果是元素节点
                            if hasattr(current, 'name'):
                                # 如果找到了下一个版本部分（以h2开头），停止收集
                                if current.name == 'h2' and 'Scrapy' in current.text:
                                    break
                                # 收集其他所有内容
                                current_text = current.get_text(separator='\n', strip=True)
                                if current_text:
                                    content_text += '\n' + current_text
                            current = current.next_sibling
                    else:
                        # 如果直接通过ID找不到，尝试查找包含该锚点的section
                        sections = soup.select("section")
                        for section in sections:
                            if section.get("id") == anchor:
                                content_text = section.get_text(separator='\n', strip=True)
                                break
                        else:
                            # 如果还是找不到，使用通用选择器
                            content_text = ""
                else:
                    # 为特定网站添加专门的选择器
                    specific_selectors = {
                        "pydata.org": ['.bd-content', '.bd-article-content', '.bd-main',  # 优先使用Sphinx主题的内容选择器
                            '#content', '#main-container', '.container',  # 通用容器选择器
                            '.whatsnew', '.whatsnew-content',  # 针对WhatsNew页面的选择器
                            '.section', '.main-content', '.article', '.document',  # 其他常见选择器
                            '#pandas-main-content', '.pandas-content'  # Pandas特定选择器
                        ],  # Pandas文档
                        "palletsprojects.com": ['.text', '.body', '.content', '.bd-article-content'],  # Flask文档
                        "scikit-learn.org": ['.section', '.content', '#main-content', '.bd-article-content', '.article',
                            '.bd-main', '.bd-content', '.main-content', '.document',  # 增加Scikit-learn文档选择器
                            '#scikit-learn-main-content', '.scikit-content', '.whatsnew-content'  # 专门针对whats_new页面
                        ],  # Scikit-learn文档
                        "matplotlib.org": ['.body', '.content', '.section', '#main-content', '.document', '.article'],  # Matplotlib文档
                        "python-poetry.org": ['.history', '.timeline', '.content', '.section', '.bd-article-content'],  # Poetry文档
                        "networkx.org": ['.release', '.changelog', '.content', '.section', '#main-content', '.document'],  # NetworkX文档
                        "readthedocs.io": ['.section', '.content', '#main-content', '.wy-nav-content', '.rst-content', '.bd-article-content',
                            '#readthedocs-main-content', '.readthedocs-content', '.content-main',  # 增加ReadTheDocs选择器
                            '.wy-body-for-nav', '.rst-content', '.document', '.wy-menu-content',  # 专门针对Hypothesis页面
                            '#content', '.content-wrapper', '.markdown-content', 'article', 'div.main'
                        ],  # ReadTheDocs (Hypothesis)
                        "alembic.sqlalchemy.org": ['.section', '.content', '#main-content', '.wy-nav-content', '.rst-content', '.bd-article-content',
                            '#alembic-content', '.alembic-main-content', '.changelog', '.release-notes',  # 增加Alembic选择器
                            'article', 'div.main', '.document', '.content-wrapper'  # 专门针对Alembic页面
                        ],  # Alembic (SQLAlchemy)
                        "scrapy.org": ['.section', '.content', '#main-content', '.wy-nav-content', '.rst-content', '.bd-article-content',
                            '.document', '.article', '#content', '.content-wrapper', '.main-content',  # 增加Scrapy文档选择器
                            '#scrapy-main-content', '.scrapy-content', '.news-content', '.whatsnew-content'  # 专门针对news页面
                        ]  # Scrapy文档
                    }
                    
                    # 尝试特定网站的选择器
                    site_found = False
                    content_text = ""
                    for site, selectors in specific_selectors.items():
                        if site in url:
                            for selector in selectors:
                                content_element = soup.select_one(selector)
                                if content_element:
                                    content_text = content_element.get_text(separator='\n', strip=True)
                                    if content_text.strip():
                                        site_found = True
                                        break
                                    else:
                                        continue
                            if site_found:
                                break
                    
                    # 如果没有找到特定网站的内容，尝试通用选择器
                    if not content_text.strip():
                        general_selectors = [
                            '.content', '.main-content', '.article', '.document', 
                            '#content', '.bd-article-content', '.bd-content',
                            '#main', '.main', '.section', '.page-content'
                        ]
                        
                        for selector in general_selectors:
                            content_element = soup.select_one(selector)
                            if content_element:
                                content_text = content_element.get_text(separator='\n', strip=True)
                                if content_text.strip():
                                    break
                    
                    # 如果仍然没有找到内容，尝试查找所有段落和标题
                    if not content_text.strip():
                        text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'code', 'pre'])
                        if text_elements:
                            content_text = '\n'.join([elem.get_text().strip() for elem in text_elements if elem.get_text().strip()])
                            if not content_text.strip():
                                content_text = ""
            
            # 处理其他类型页面
            else:
                # 尝试通用选择器
                general_selectors = [
                    '.content', '.main-content', '.article', '.document', 
                    '#content', '.bd-article-content', '.bd-content',
                    '#main', '.main', '.section', '.page-content'
                ]
                
                for selector in general_selectors:
                    content_element = soup.select_one(selector)
                    if content_element:
                        content_text = content_element.get_text(separator='\n', strip=True)
                        if content_text.strip():
                            break
                
                # 如果没有找到内容，尝试查找所有段落和标题
                if content_text == "No content found":
                    text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'code', 'pre'])
                    if text_elements:
                        content_text = '\n'.join([elem.get_text().strip() for elem in text_elements if elem.get_text().strip()])
                        if not content_text.strip():
                            content_text = "No content found"
            
            # 尝试从URL中提取版本信息
            version = "Unknown version"
            if "/v" in url:
                # 从URL中提取版本号
                parts = url.split("/")
                for part in parts:
                    if part.startswith("v") and any(char.isdigit() for char in part):
                        version = part
                        break
            elif "/version/" in url:
                # 处理类似 /version/2.2.0/ 的URL
                parts = url.split("/version/")
                if len(parts) > 1:
                    version_part = parts[1].split("/")[0]
                    if version_part and any(char.isdigit() for char in version_part):
                        version = version_part
            elif "/releases/" in url:
                # 处理GitHub releases页面
                parts = url.split("/")
                for part in parts:
                    if any(char.isdigit() for char in part):
                        version = part
                        break
            
            # 尝试从URL中提取发布日期（如果可能）
            release_date = "Unknown release date"
            
            # 提取发布日期或更新日期
            # 尝试relative-time标签（GitHub使用）
            date_element = soup.find('relative-time')
            if date_element:
                release_date = date_element['datetime']
            else:
                # 尝试time标签
                date_elements = soup.find_all('time')
                if date_elements:
                    for elem in date_elements:
                        if 'datetime' in elem.attrs:
                            release_date = elem['datetime']
                            break
                        elif elem.string:
                            release_date = elem.string.strip()
                            break
            
            # 处理带有锚点的URL，提取锚点位置的内容
            if '#' in url and content_text != "No content found":
                anchor = url.split('#')[1]
                
                # 针对特定库的特殊锚点处理
                if "scrapy.org" in url:
                    # Scrapy特殊处理：锚点是section元素，不是标题
                    # 尝试多种方式查找Scrapy的版本部分
                    import re
                    version_anchor = anchor.replace('-', '.')  # 将锚点转换为版本号格式
                    anchor_element = None
                    
                    # 1. 直接查找带版本号的section
                    for section in soup.find_all('section', id=True):
                        if version_anchor in section['id'].replace('-', '.'):
                            anchor_element = section
                            break
                    
                    # 2. 如果没找到，查找包含版本号的h2标题
                    if not anchor_element:
                        for h2 in soup.find_all('h2'):
                            if version_anchor in h2.get_text():
                                anchor_element = h2.parent  # 获取h2的父元素
                                break
                    
                    # 3. 如果还是没找到，使用默认ID查找
                    if not anchor_element:
                        anchor_element = soup.find(id=anchor)
                elif "python-poetry.org" in url:
                    # Poetry特殊处理：锚点是版本号，但页面中的ID是格式化的
                    # 查找h2标题，其文本包含锚点中的版本号
                    import re
                    version_pattern = re.compile(re.escape(anchor), re.IGNORECASE)
                    h2_tags = soup.find_all('h2')
                    for h2 in h2_tags:
                        text = h2.get_text().strip()
                        if version_pattern.search(text):
                            anchor_element = h2
                            break
                    else:
                        anchor_element = soup.find(id=anchor)
                elif "github.com" in url and "faker" in url.lower() and "releases/tag" in url:
                    # Faker特殊处理：使用GitHub API获取release信息
                    import re
                    try:
                        # 从URL提取版本号
                        version_match = re.search(r'/tag/(v?\d+(\.\d+)*)', url)
                        if version_match:
                            version = version_match.group(1)
                            
                            # 构建API URL，支持不同的Faker仓库
                            if "faker-js" in url:
                                repo = "faker-js/faker"
                            else:
                                repo = "joke2k/faker"
                            
                            api_url = f"https://api.github.com/repos/{repo}/releases/tags/{version}"
                            api_response = requests.get(api_url, headers=headers, timeout=10)
                            
                            if api_response.status_code == 200:
                                release_data = api_response.json()
                                anchor_content = f"Release Notes for {version}:\n"
                                anchor_content += f"Published: {release_data['published_at']}\n"
                                anchor_content += f"Tag Name: {release_data['tag_name']}\n"
                                if release_data['body']:
                                    anchor_content += f"\n{release_data['body']}"
                                
                                # 使用API返回的内容
                                content_text = anchor_content
                                anchor_element = None  # 跳过默认锚点处理
                            else:
                                # API请求失败，回退到原方法
                                anchor_element = soup.find(id=anchor)
                        else:
                            anchor_element = soup.find(id=anchor)
                    except Exception as e:
                        print(f"Error fetching Faker release via API: {e}")
                        anchor_element = soup.find(id=anchor)
                elif "readthedocs.io" in url and "hypothesis" in url and "changes" in url:
                    # Hypothesis特殊处理：直接获取变更日志内容
                    try:
                        # 直接获取当前URL的内容
                        response = requests.get(url, headers=headers, timeout=30)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 查找与锚点匹配的元素
                        anchor_element = soup.find(id=anchor)
                        
                        if anchor_element:
                            # 收集锚点部分的内容
                            content_parts = [anchor_element.get_text(separator='\n', strip=True)]
                            next_element = anchor_element.next_sibling
                            
                            while next_element:
                                if hasattr(next_element, 'name') and next_element.name.startswith('h'):
                                    # 遇到下一个标题，停止收集
                                    break
                                if hasattr(next_element, 'get_text') and next_element.get_text(strip=True):
                                    content_parts.append(next_element.get_text(separator='\n', strip=True))
                                next_element = next_element.next_sibling
                            
                            anchor_content = '\n'.join(content_parts)
                            
                            # 如果锚点内容不为空，使用它
                            if anchor_content.strip():
                                content_text = anchor_content
                                anchor_element = None  # 跳过默认锚点处理
                    except Exception as e:
                        print(f"Error fetching Hypothesis changes: {e}")
                        anchor_element = soup.find(id=anchor)
                else:
                    # 默认处理：查找与锚点匹配的元素
                    anchor_element = soup.find(id=anchor)
                
                if anchor_element:
                    # 收集锚点元素及其相关内容，特别处理嵌套结构
                    related_content = []
                    
                    # 检查锚点元素类型
                    if anchor_element.name == 'section':
                        # 对于section元素（如Flask的版本页面），收集其直接子元素内容
                        # 直到遇到下一个同级别或更高级别的section
                        for child in anchor_element.children:
                            if hasattr(child, 'name'):
                                # 如果遇到下一个section，停止收集
                                if child.name == 'section':
                                    break
                                # 收集所有其他子元素内容
                                element_text = child.get_text(separator='\n', strip=True)
                                if element_text:
                                    related_content.append(element_text)
                    else:
                        # 对于非section元素，使用原有的处理方式
                        related_content = [anchor_element.get_text(separator='\n', strip=True)]
                        
                        # 查找锚点元素的后续兄弟元素，直到下一个相同级别的标题或页面结束
                        current_element = anchor_element.next_sibling
                        while current_element:
                            # 如果是元素节点
                            if hasattr(current_element, 'name'):
                                # 如果遇到相同或更高层级的标题，停止收集
                                if current_element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                    # 检查标题级别（数字越小级别越高）
                                    current_level = int(current_element.name[1])
                                    anchor_level = int(anchor_element.name[1]) if anchor_element.name and anchor_element.name.startswith('h') else 6
                                    
                                    if current_level <= anchor_level:
                                        break
                                
                                # 收集元素内容
                                element_text = current_element.get_text(separator='\n', strip=True)
                                if element_text:
                                    related_content.append(element_text)
                            
                            current_element = current_element.next_sibling
                    
                    # 合并相关内容
                    anchor_content = '\n'.join(related_content)
                    
                    # 如果锚点内容不为空，使用锚点内容替代完整内容
                    if anchor_content.strip():
                        content_text = anchor_content
            
            return {
                "library_name": library_name,
                "url": url,
                "version": version,
                "title": title,
                "release_date": release_date,
                "content": content_text,
                "crawl_status": "success"
            }
            
        except requests.exceptions.RequestException as e:
            print(f"尝试 {attempt + 1}/{max_retries} 爬取 {url} 失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(1, 3))  # 增加重试延迟
            else:
                return {
                    "library_name": library_name,
                    "url": url,
                    "version": "Unknown version",
                    "title": "爬取失败",
                    "release_date": "Unknown release date",
                    "content": f"爬取失败: {str(e)}",
                    "crawl_status": "failed"
                }


def main():
    # 检查命令行参数
    if len(sys.argv) != 2:
        print("使用方法: python crawl_specific_library.py <库名>")
        print("示例: python crawl_specific_library.py Pandas")
        sys.exit(1)
    
    # 获取指定的库名
    target_library = sys.argv[1]
    print(f"正在爬取库: {target_library}")
    
    # 读取URL数据
    library_urls = read_accessible_urls()
    if not library_urls:
        print("未找到URL数据")
        return
    
    # 检查指定的库名是否存在
    if target_library not in library_urls:
        print(f"库名 '{target_library}' 不存在于accessible_library_urls.json中")
        print(f"可用的库名: {', '.join(library_urls.keys())}")
        return
    
    # 获取对应的三个URLs
    urls = library_urls[target_library]
    if len(urls) != 3:
        print(f"警告: 库 '{target_library}' 对应的URL数量不是3个，而是 {len(urls)} 个")
    
    print(f"找到 {len(urls)} 个URL:")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")
    
    # 用于存储爬取结果
    crawled_data = []
    
    # 使用线程池并行爬取
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # 提交所有任务并显示进度条
        future_to_url = {
            executor.submit(crawl_url, url, target_library): url 
            for url in urls
        }
        
        # 处理完成的任务并更新进度条
        for future in tqdm(concurrent.futures.as_completed(future_to_url), 
                          total=len(urls), desc=f"正在爬取 {target_library}"):
            try:
                result = future.result()
                crawled_data.append(result)
                
                if result["crawl_status"] == "success":
                    print(f"✓ 成功爬取: {result['url']}")
                else:
                    print(f"✗ 爬取失败: {result['url']} - {result['content']}")
            except Exception as e:
                url = future_to_url[future]
                print(f"✗ 爬取 {url} 发生未知错误: {e}")
    
    # 保存爬取结果（使用统一文件名）
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建输出文件的绝对路径
    output_file = os.path.normpath(os.path.join(script_dir, "../data/specific_library_crawled_data.json"))
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(crawled_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n爬取完成！")
    print(f"结果已保存到: {output_file}")
    
    # 统计结果
    success_count = sum(1 for item in crawled_data if item.get("crawl_status") == "success")
    failed_count = sum(1 for item in crawled_data if item.get("crawl_status") == "failed")
    
    # 检查content是否有重复
    content_list = []
    for item in crawled_data:
        if item.get("crawl_status") == "success":
            content_list.append(item.get("content", ""))
        else:
            content_list.append("爬取失败内容")
    
    duplicate_count = 0
    if len(content_list) >= 3:
        # 检查三个content之间的重复情况
        if content_list[0] == content_list[1] and content_list[0] == content_list[2]:
            duplicate_count = 3  # 三个都相同
        elif content_list[0] == content_list[1] or content_list[0] == content_list[2] or content_list[1] == content_list[2]:
            duplicate_count = 2  # 有两个相同
    
    print(f"\n统计信息:")
    print(f"总URL数量: {len(urls)}")
    print(f"成功爬取: {success_count}")
    print(f"爬取失败: {failed_count}")
    
    # 打印重复检查结果
    if duplicate_count == 3:
        print(f"内容重复检查结果: 3个URL的内容全部相同")
    elif duplicate_count == 2:
        print(f"内容重复检查结果: 有2个URL的内容相同")
    else:
        print(f"内容重复检查结果: 3个URL的内容都不相同")
    
    # 询问用户是否要追加保存到统一的JSON文件
    # 构建append_file的绝对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    append_file = os.path.normpath(os.path.join(script_dir, "../data/library_crawled_data_append.json"))
    while True:
        user_input = input(f"\n是否将结果追加到 {append_file}？(yes/no): ").strip().lower()
        if user_input in ['yes', 'y']:
            # 读取现有文件内容
            existing_data = []
            if os.path.exists(append_file):
                try:
                    with open(append_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except json.JSONDecodeError:
                    print("现有文件格式有误，将创建新文件")
                    existing_data = []
            
            # 过滤掉现有数据中与当前库名相同的所有条目
            current_library_name = crawled_data[0]['library_name'] if crawled_data else ""
            filtered_data = [item for item in existing_data if item.get('library_name') != current_library_name]
            
            # 将新数据添加到过滤后的现有数据中
            filtered_data.extend(crawled_data)
            
            # 保存到文件
            with open(append_file, 'w', encoding='utf-8') as f:
                json.dump(filtered_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n结果已成功追加到: {append_file}")
            print(f"当前文件包含 {len(filtered_data)} 个条目")
            break
        elif user_input in ['no', 'n']:
            print("\n未进行追加保存")
            break
        else:
            print("请输入 yes 或 no")


if __name__ == "__main__":
    # 确保tqdm已安装
    try:
        from tqdm import tqdm
    except ImportError:
        print("正在安装tqdm...")
        os.system("pip install tqdm")
        from tqdm import tqdm
    
    main()
