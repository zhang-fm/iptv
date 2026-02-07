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

CHECK_COUNT = 3      
CHECK_TIMEOUT = 10   
MIN_PEAK_REQUIRED = 0.50  

# 屏蔽名单配置
BLOCK_PROVINCES = ["Shanghai", "Jiangsu", "Zhejiang", "Guangdong"] # 江浙沪广
BLOCK_ISP = "China Telecom" # 电信

def get_ip_info(ip):
    """查询 IP 归属地和运营商"""
    try:
        # 使用 ip-api.com (免费额度每分钟45次，并行测速时建议加少量延迟或限制并发)
        # fields=status,message,regionName,isp
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=status,regionName,isp", timeout=5).json()
        if response.get("status") == "success":
            return response.get("regionName"), response.get("isp")
    except:
        pass
    return None, None

def is_blocked(ip):
    """判断是否属于 江浙沪广电信"""
    # 提取纯 IP (去掉端口)
    pure_ip = ip.split(':')[0]
    region, isp = get_ip_info(pure_ip)
    
    if region and isp:
        # 判断省份是否在屏蔽名单，且运营商包含“Telecom”或“电信”
        if region in BLOCK_PROVINCES and ("Telecom" in isp or "电信" in isp):
            return True, f"{region} {isp}"
    return False, None

def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_blacklist(ip, reason=""):
    with open(BLACKLIST_FILE, "a", encoding="utf-8") as f:
        comment = f" # {reason}" if reason else ""
        f.write(f"{ip}{comment}\n")

def get_realtime_speed(url):
    try:
        start_time = time.time()
        res = requests.get(url, timeout=CHECK_TIMEOUT, stream=True, headers={'User-Agent': 'vlc/3.0.8'})
        if res.status_code != 200: return 0
        
        chunk = res.raw.read(1024 * 1024) 
        duration = time.time() - start_time
        return 1.0 / duration if duration > 0 else 0
    except:
        return 0

def test_ip_group(ip_port, channels):
    """测试某个IP下的随机频道"""
    # --- 新增屏蔽逻辑 ---
    blocked, reason = is_blocked(ip_port)
    if blocked:
        return ip_port, -1.0, False, f"屏蔽区域: {reason}"
    # ------------------

    all_urls = [url for _, url in channels]
    test_targets = random.sample(all_urls, min(len(all_urls), CHECK_COUNT))
    best_peak = 0.0
    alive_count = 0

    for url in test_targets:
        speed = get_realtime_speed(url)
        if speed > 0.01:
            alive_count += 1
            if speed > best_peak: best_peak = speed

    return ip_port, best_peak, (alive_count > 0), ""

def main():
    print(f"📅 任务启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not os.path.exists(BLACKLIST_FILE):
        open(BLACKLIST_FILE, 'w').close()

    blacklist = load_blacklist()
    category_map = {}
    
    for f_path in INPUT_FILES:
        if not os.path.exists(f_path): continue
        current_category = "未分类"
        with open(f_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "#genre#" in line:
                    if "#genre#" in line: current_category = line.split(",")[0].strip()
                    continue
                if "," in line and "http" in line:
                    parts = line.split(",", 1)
                    ch_name, url = parts[0].strip(), parts[1].strip()
                    match = re.search(r'http://(.*?)/', url)
                    if match:
                        ip_port = match.group(1)
                        if ip_port in blacklist: continue
                        if current_category not in category_map: category_map[current_category] = {}
                        if ip_port not in category_map[current_category]: category_map[current_category][ip_port] = []
                        category_map[current_category][ip_port].append((ch_name, url))

    unique_ips = {}
    for cat_dict in category_map.values():
        for ip, channels in cat_dict.items():
            if ip not in unique_ips: unique_ips[ip] = channels

    total_ips = len(unique_ips)
    print(f"🚀 准备测试 {total_ips} 个服务器 (已启用江浙沪广电信屏蔽)")

    valid_ips = {} 
    new_dead_ips = []
    done_count = 0

    # 注意：并发数不宜过高，否则 IP 查询 API 会封禁请求
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(test_ip_group, ip, chs): ip for ip, chs in unique_ips.items()}
        for future in concurrent.futures.as_completed(futures):
            done_count += 1
            ip, peak, is_alive, msg = future.result()
            
            if peak == -1.0:
                print(f"[{done_count}/{total_ips}] 🛡️  {ip:20} | {msg}")
                save_to_blacklist(ip, msg)
                continue

            status_icon = "✅" if is_alive else "❌"
            print(f"[{done_count}/{total_ips}] {status_icon} {ip:20} | 峰值: {peak:5.2f} MB/s")
            
            if not is_alive:
                new_dead_ips.append(ip)
                save_to_blacklist(ip, "死链")
            elif peak >= MIN_PEAK_REQUIRED:
                valid_ips[ip] = peak

    # 写入结果 (保持原有逻辑)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for cat_name, ip_dict in category_map.items():
            cat_content = []
            for ip in ip_dict:
                if ip in valid_ips:
                    for ch_name, url in ip_dict[ip]:
                        cat_content.append(f"{ch_name},{url}")
            if cat_content:
                f.write(f"{cat_name},#genre#\n")
                for item in cat_content: f.write(f"{item}\n")
                f.write("\n")

    print("-" * 50)
    print(f"✨ 任务结束！屏蔽且拉黑了探测到的江浙沪广电信源。")

if __name__ == "__main__":
    main()
