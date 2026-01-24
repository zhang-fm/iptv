import os
import re

# --- 配置区 ---
INPUT_FILE = "py/live_full.txt"
OUTPUT_M3U = "test/IPTV2.m3u"
LOGO_BASE = "https://gcore.jsdelivr.net/gh/kenye201/TVlog/img/"
EPG_URL = "https://live.fanmingming.com/e.xml"

# 7大核心卫视顺序
CORE_SATELLITE = ["湖南卫视", "东方卫视", "浙江卫视", "江苏卫视", "北京卫视", "湖北卫视", "深圳卫视"]

def clean_channel_name(name):
    """频道名洗版规则：保留4K，剔除一切杂质"""
    # 1. 提取是否包含 4K（不分大小写）
    is_4k = "4K" in name.upper()
    
    # 2. 暴力剔除干扰词（正则表达式，无视大小写）
    # 剔除：高清, 标清, 超清, HD, SD, (.*)括号内容, [.*]内容, - (横杠)
    clean = re.sub(r'[\(\[\uff08].*?[\)\]\uff09]', '', name) # 删掉括号内容
    clean = re.sub(r'HD|SD|高清|标清|超清|超高|超准|频道|-', '', clean, flags=re.IGNORECASE)
    clean = clean.replace(" ", "").upper()
    
    # 3. CCTV 规范化：CCTV-1 -> CCTV1
    if "CCTV" in clean:
        match = re.search(r'CCTV(\d+)', clean)
        if match:
            num = match.group(1)
            # CCTV5+ 特殊保护
            if "5+" in name or "5PLUS" in name.upper():
                clean = "CCTV5+"
            else:
                clean = f"CCTV{num}"
    
    # 4. 重新挂载 4K 标签
    if is_4k and "4K" not in clean:
        clean += "4K"
        
    return clean

def get_sort_weight(name):
    """根据清洗后的名字分配权重"""
    # CCTV 数字 (1-17)
    cctv_num_match = re.search(r'CCTV(\d+)', name)
    if cctv_num_match:
        num = int(cctv_num_match.group(1))
        if 1 <= num <= 17: return 100 + num
        return 200
    
    if "CCTV5+" in name: return 105.5
    if "CCTV" in name: return 210
    if "4K" in name: return 300
    
    for i, core in enumerate(CORE_SATELLITE):
        if core in name: return 400 + i
            
    if "卫视" in name: return 500
    return 900

def convert():
    if not os.path.exists(INPUT_FILE): return

    server_groups = {}
    region_server_map = {}

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or "#genre#" in line or "," not in line: continue
            
            parts = line.split(',', 1)
            raw_name = parts[0]
            url_part = parts[1]
            
            # --- 执行洗版：规范频道名 ---
            display_name = clean_channel_name(raw_name)
            
            if "$" in url_part:
                url_only, region = url_part.split('$', 1)
                server_match = re.search(r'http://([\d\.]+:\d+)/', url_only)
                if server_match:
                    server_ip = server_match.group(1)
                    if region not in region_server_map: region_server_map[region] = []
                    if server_ip not in region_server_map[region]: region_server_map[region].append(server_ip)
                    if server_ip not in server_groups: server_groups[server_ip] = {"region": region, "channels": []}
                    
                    server_groups[server_ip]["channels"].append({
                        "name": display_name,
                        "url": url_only,
                        "weight": get_sort_weight(display_name)
                    })

    m3u_lines = [f'#EXTM3U x-tvg-url="{EPG_URL}"']
    for region in sorted(region_server_map.keys()):
        for idx, server_ip in enumerate(region_server_map[region]):
            group_tag = f"({region}{idx + 1})"
            channels = server_groups[server_ip]["channels"]
            # 排序：先权重，再字母，并去重（防止同一服务器同一频道重复出现）
            seen = set()
            sorted_channels = []
            for c in sorted(channels, key=lambda x: (x['weight'], x['name'])):
                if c['name'] not in seen:
                    sorted_channels.append(c)
                    seen.add(c['name'])
            
            for ch in sorted_channels:
                logo_url = f"{LOGO_BASE}{ch['name']}.png"
                m3u_lines.append(f'#EXTINF:-1 tvg-logo="{logo_url}" group-title="{group_tag}",{ch["name"]}')
                m3u_lines.append(ch['url'])

    with open(OUTPUT_M3U, 'w', encoding='utf-8') as f:
        f.write("\n".join(m3u_lines))
    print("✨ 洗版并重排完成！")

if __name__ == "__main__":
    convert()
