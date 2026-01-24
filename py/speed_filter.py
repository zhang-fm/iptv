import os
import re
import time
import requests
import concurrent.futures
import sys
import random
import functools

# 强制实时刷新输出，不再等待缓存
print = functools.partial(print, flush=True)

# ===============================
# 配置区
# ===============================
INPUT_FILES = ["py/live.txt", "py/IPTV2.txt"]
OUTPUT_FILE = "py/livezubo.txt"
BLACKLIST_FILE = "py/blacklist.txt"

CHECK_COUNT = 3      # 每个服务器抽测 3 个频道
CHECK_TIMEOUT = 10   # 每个频道超时时间
MIN_PEAK_REQUIRED = 1.15  # 峰值门槛 MB/s

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
        # 增加 stream=True 避免下载整个视频，只测前 1MB
        res = requests.get(url, timeout=CHECK_TIMEOUT, stream=True, headers={'User-Agent': 'vlc/3.0.8'})
        if res.status_code != 200: return 0
        
        chunk = res.raw.read(1024 * 1024) # 读 1MB
        duration = time.time() - start_time
        return 1.0 / duration if duration > 0 else 0
    except:
        return 0

def test_ip_group(ip_port, channels):
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
    
    # 确保黑名单文件存在
    if not os.path.exists(BLACKLIST_FILE):
        open(BLACKLIST_FILE, 'w').close()
        print("🆕 已创建新的黑名单文件")

    blacklist = load_blacklist()
    print(f"🚫 当前黑名单库条数: {len(blacklist)}")

    # 读取输入文件
    all_lines = []
    for f_path in INPUT_FILES:
        if os.path.exists(f_path):
            with open(f_path, "r", encoding="utf-8") as f:
                all_lines.extend(f.readlines())
    
    if not all_lines:
        print("❌ 错误: 未发现任何输入线路文件 (live.txt/IPTV2.txt)")
        return

    # 分组并过滤
    ip_groups = {}
    for line in all_lines:
        if "," in line and "http://" in line:
            name, url = line.strip().split(",", 1)
            match = re.search(r'http://(.*?)/', url)
            if match:
                ip_port = match.group(1)
                if ip_port not in blacklist:
                    ip_groups.setdefault(ip_port, []).append((name, url))

    total_ips = len(ip_groups)
    print(f"🚀 准备测试服务器总数: {total_ips}")
    print("-" * 50)

    results = {}
    new_dead_ips = []
    done_count = 0

    # 开始并行测试
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(test_ip_group, ip, chs): ip for ip, chs in ip_groups.items()}
        
        for future in concurrent.futures.as_completed(futures):
            done_count += 1
            ip, peak, is_alive = future.result()
            
            # 实时进度显示
            status_icon = "✅" if is_alive else "❌"
            progress = f"[{done_count}/{total_ips}]"
            print(f"{progress} {status_icon} {ip:20} | 峰值: {peak:5.2f} MB/s")
            
            if not is_alive:
                new_dead_ips.append(ip)
                save_to_blacklist(ip) # 发现一个写一个，防止脚本中途崩溃丢失记录
            elif peak >= MIN_PEAK_REQUIRED:
                results[ip] = peak

    # 写入输出
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for ip, peak in results.items():
            for name, url in ip_groups[ip]:
                f.write(f"{name},{url}\n")

    print("-" * 50)
    print(f"✨ 测速总结:")
    print(f"   - 达标保留: {len(results)} 个服务器")
    print(f"   - 本次新增黑名单: {len(new_dead_ips)} 个")
    print(f"   - 结果已保存至: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
