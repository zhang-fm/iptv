import os
import re
import time
import requests
import concurrent.futures
import sys
import random
import functools

# 强制实时刷新输出
print = functools.partial(print, flush=True)

# ===============================
# 配置区
# ===============================
INPUT_FILES = ["py/live.txt", "py/IPTV2.txt"]
OUTPUT_FILE = "py/livezubo.txt"
BLACKLIST_FILE = "py/blacklist.txt"

CHECK_COUNT = 3      # 每个服务器抽测 3 个频道
CHECK_TIMEOUT = 10   # 每个频道超时时间
MIN_PEAK_REQUIRED = 0.50  # 峰值门槛 MB/s

def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_blacklist(ip):
    with open(BLACKLIST_FILE, "a", encoding="utf-8") as f:
        f.write(ip + "\n")

def get_realtime_speed(url):
    try:
        start_time = time.time()
        res = requests.get(url, timeout=CHECK_TIMEOUT, stream=True, headers={'User-Agent': 'vlc/3.0.8'})
        if res.status_code != 200: return 0
        
        chunk = res.raw.read(1024 * 1024) # 读 1MB
        duration = time.time() - start_time
        return 1.0 / duration if duration > 0 else 0
    except:
        return 0

def test_ip_group(ip_port, channels):
    """测试某个IP下的随机频道"""
    all_urls = [url for _, url in channels]
    test_targets = random.sample(all_urls, min(len(all_urls), CHECK_COUNT))
    best_peak = 0.0
    alive_count = 0

    for url in test_targets:
        speed = get_realtime_speed(url)
        if speed > 0.01:
            alive_count += 1
            if speed > best_peak: best_peak = speed

    return ip_port, best_peak, (alive_count > 0)

def main():
    print(f"📅 任务启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not os.path.exists(BLACKLIST_FILE):
        open(BLACKLIST_FILE, 'w').close()
        print("🆕 已创建新的黑名单文件")

    blacklist = load_blacklist()
    
    # 核心数据结构
    # { "分类名称": { "ip:port": [(name, url), ...] } }
    category_map = {}
    
    # 1. 解析输入文件并保留分类
    for f_path in INPUT_FILES:
        if not os.path.exists(f_path): continue
        
        current_category = "未分类"
        with open(f_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                
                # 识别分类行 (例如: 央视频道,#genre#)
                if "#genre#" in line:
                    current_category = line.split(",")[0].strip()
                    continue
                
                # 识别频道行 (例如: CCTV1,http://ip:port/...)
                if "," in line and "http" in line:
                    parts = line.split(",", 1)
                    ch_name = parts[0].strip()
                    url = parts[1].strip()
                    
                    # 提取 IP:Port
                    match = re.search(r'http://(.*?)/', url)
                    if match:
                        ip_port = match.group(1)
                        if ip_port in blacklist: continue
                        
                        # 构建嵌套字典
                        if current_category not in category_map:
                            category_map[current_category] = {}
                        if ip_port not in category_map[current_category]:
                            category_map[current_category][ip_port] = []
                        
                        category_map[current_category][ip_port].append((ch_name, url))

    # 2. 提取所有唯一的 IP:Port 进行测速（避免重复测速）
    unique_ips = {}
    for cat_dict in category_map.values():
        for ip, channels in cat_dict.items():
            if ip not in unique_ips:
                unique_ips[ip] = channels

    total_ips = len(unique_ips)
    print(f"🚀 发现 {len(category_map)} 个分类，准备测试 {total_ips} 个服务器")
    print("-" * 50)

    # 3. 并行测速
    valid_ips = {} # 存储达标的 IP 及其峰值
    new_dead_ips = []
    done_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(test_ip_group, ip, chs): ip for ip, chs in unique_ips.items()}
        for future in concurrent.futures.as_completed(futures):
            done_count += 1
            ip, peak, is_alive = future.result()
            
            status_icon = "✅" if is_alive else "❌"
            print(f"[{done_count}/{total_ips}] {status_icon} {ip:20} | 峰值: {peak:5.2f} MB/s")
            
            if not is_alive:
                new_dead_ips.append(ip)
                save_to_blacklist(ip)
            elif peak >= MIN_PEAK_REQUIRED:
                valid_ips[ip] = peak

    # 4. 按分类写入结果文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for cat_name, ip_dict in category_map.items():
            # 检查该分类下是否有达标的 IP
            cat_content = []
            for ip in ip_dict:
                if ip in valid_ips:
                    for ch_name, url in ip_dict[ip]:
                        cat_content.append(f"{ch_name},{url}")
            
            # 如果该分类下有活的频道，则写入分类标题和内容
            if cat_content:
                f.write(f"{cat_name},#genre#\n")
                for item in cat_content:
                    f.write(f"{item}\n")
                f.write("\n") # 分类间留空行

    print("-" * 50)
    print(f"✨ 测速总结:")
    print(f"   - 达标保留服务器: {len(valid_ips)}")
    print(f"   - 本次新增黑名单: {len(new_dead_ips)}")
    print(f"   - 结果已保存至: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
