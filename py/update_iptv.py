import requests
import re

def fetch_content(url):
    try:
        response = requests.get(url)
        response.encoding = 'utf-8'
        return response.text if response.status_code == 200 else ""
    except:
        return ""

def parse_txt(content):
    """解析 TXT 内容，返回分类字典"""
    groups = {}
    current_genre = "其他频道"
    
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # 判断是否是分类行
        if ",#genre#" in line:
            current_genre = line.split(',')[0]
            if current_genre not in groups:
                groups[current_genre] = []
        else:
            # 频道行处理
            if "," in line:
                groups.setdefault(current_genre, []).append(line)
    return groups

# GitHub 原始文件路径 (请根据实际分支名修改，通常是 main 或 master)
raw_base = "https://raw.githubusercontent.com/linyu345/iptv/main/"
file1_url = raw_base + "py/live.txt"
file2_url = raw_base + "py/IPTV2.txt"

print("正在获取远程文件...")
data1 = parse_txt(fetch_content(file1_url))
data2 = parse_txt(fetch_content(file2_url))

# 合并逻辑：以 data2 (IPTV2.txt) 的分类顺序为基准
merged_groups = data2.copy()

# 将 data1 中存在但 data2 中没有的分类加进去
for genre, channels in data1.items():
    if genre not in merged_groups:
        merged_groups[genre] = channels
    else:
        # 如果分类相同，合并频道列表
        merged_groups[genre].extend(channels)

# 最终去重并写入
with open("merged_iptv.txt", "w", encoding="utf-8") as f:
    for genre, channels in merged_groups.items():
        f.write(f"{genre},#genre#\n")
        
        unique_channels = []
        seen_urls = set()
        
        for ch in channels:
            # 提取 URL 部分进行去重 (CCTV1,URL$线路)
            parts = ch.split(',')
            if len(parts) >= 2:
                url_part = parts[1].strip()
                if url_part not in seen_urls:
                    seen_urls.add(url_part)
                    unique_channels.append(ch)
        
        for ch in unique_channels:
            f.write(f"{ch}\n")
        f.write("\n")

print("合并完成：merged_iptv.txt")
