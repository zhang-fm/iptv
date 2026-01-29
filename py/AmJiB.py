import os
import re
import requests
import time
import concurrent.futures
import subprocess
import socket
from datetime import datetime, timezone, timedelta

# ===============================
# 配置区
# ===============================
FOFA_URLS = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# 路径管理
BASE_DIR = os.getcwd()
COUNTER_FILE = os.path.join(BASE_DIR, "py/计数.txt")
IP_DIR = os.path.join(BASE_DIR, "ip")
RTP_DIR = os.path.join(BASE_DIR, "rtp")
ZUBO_FILE = os.path.join(BASE_DIR, "py/zubo.txt")
IPTV_FILE = os.path.join(BASE_DIR, "test/IPTV.txt")
LIVE_BACKUP_FILE = os.path.join(BASE_DIR, "py/live.txt")

# 频道分类与别名映射 (保持你之前的配置)
CHANNEL_CATEGORIES = {
    "央视频道": ["CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5", "CCTV5+", "CCTV6", "CCTV7", "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17", "CCTV4K", "CCTV8K"],
    "卫视频道": ["湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "北京卫视", "广东卫视"],
    "4K频道": ["东方卫视4K","北京卫视4K","江苏卫视4K","浙江卫视4K","湖南卫视4K","深圳卫视4K"],
    "大湾区": ["广东珠江","广东体育","广东新闻","广州综合","佛山综合"],
}

CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合"],
    "CCTV13": ["CCTV-13", "CCTV-13 HD", "CCTV13 HD", "CCTV-13新闻"],
    # ... 其他映射保持不变
}

# ===============================
# 第一阶段：IP 爬取与分类
# ===============================
def first_stage():
    os.makedirs(IP_DIR, exist_ok=True)
    all_ips = set()
    for url, _ in FOFA_URLS.items():
        print(f"📡 正在爬取 FOFA...")
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            urls_all = re.findall(r'<a href="http://(.*?)"', r.text)
            all_ips.update(u.strip() for u in urls_all if u.strip())
        except Exception as e:
            print(f"❌ 爬取失败：{e}")

    # 获取地理位置并分类
    province_isp_dict = {}
    for ip_port in all_ips:
        host = ip_port.split(":")[0]
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
            try: host = socket.gethostbyname(host)
            except: continue
        
        # 增加延迟防止 API 限制
        time.sleep(1.2)
        try:
            res = requests.get(f"http://ip-api.com/json/{host}?lang=zh-CN", timeout=10)
            data = res.json()
            province = data.get("regionName", "未知")
            isp_raw = (data.get("isp") or "").lower()
            isp = "电信" if "telecom" in isp_raw else "联通" if "unicom" in isp_raw else "移动" if "mobile" in isp_raw else "未知"
            
            if isp != "未知":
                fname = f"{province}{isp}.txt"
                province_isp_dict.setdefault(fname, set()).add(ip_port)
        except: continue

    # 更新计数器
    count = get_run_count() + 1
    save_run_count(count)

    for filename, ip_set in province_isp_dict.items():
        path = os.path.join(IP_DIR, filename)
        with open(path, "a", encoding="utf-8") as f:
            for ip_port in sorted(ip_set):
                f.write(ip_port + "\n")
    print(f"✅ 第一阶段完成，当前轮次：{count}")
    return count

def get_run_count():
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip() or "0")
        except: return 0
    return 0

def save_run_count(count):
    os.makedirs(os.path.dirname(COUNTER_FILE), exist_ok=True)
    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        f.write(str(count))

# ===============================
# 第二阶段：生成 zubo.txt
# ===============================
def second_stage():
    print("🔔 第二阶段：生成 zubo.txt")
    combined_lines = []
    if not os.path.exists(RTP_DIR) or not os.path.exists(IP_DIR): return

    for ip_file in os.listdir(IP_DIR):
        rtp_path = os.path.join(RTP_DIR, ip_file)
        ip_path = os.path.join(IP_DIR, ip_file)
        if os.path.exists(rtp_path):
            with open(ip_path, encoding="utf-8") as f1, open(rtp_path, encoding="utf-8") as f2:
                ips = [x.strip() for x in f1 if x.strip()]
                rtps = [x.strip() for x in f2 if x.strip()]
                for ip in ips:
                    for rtp in rtps:
                        if "," in rtp and "://" in rtp:
                            name, url = rtp.split(",", 1)
                            proto = "rtp" if "rtp://" in url else "udp"
                            parts = url.split("://")
                            if len(parts) > 1:
                                combined_lines.append(f"{name},http://{ip}/{proto}/{parts[1]}")
    
    with open(ZUBO_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(list(set(combined_lines))))
    print(f"🎯 zubo.txt 已生成，记录数: {len(combined_lines)}")

# ===============================
# 第三阶段：测速与写入 IPTV.txt
# ===============================
def third_stage():
    print("🧩 第三阶段：测速并生成 IPTV.txt")
    if not os.path.exists(ZUBO_FILE): return

    def check_stream(url):
        try:
            result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-i", url], 
                                    capture_output=True, timeout=5)
            return b"codec_type" in result.stdout
        except: return False

    all_lines = []
    with open(ZUBO_FILE, "r", encoding="utf-8") as f:
        all_lines = [l.strip() for l in f if "," in l]

    ip_groups = {}
    for line in all_lines:
        match = re.match(r"http://([^/]+)/", line.split(",")[1])
        if match: ip_groups.setdefault(match.group(1), []).append(line)

    print(f"🚀 正在检测 {len(ip_groups)} 个 IP 源...")
    playable_ips = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        future_to_ip = {executor.submit(check_stream, lines[0].split(",")[1]): ip for ip, lines in ip_groups.items()}
        for future in concurrent.futures.as_completed(future_to_ip):
            if future.result(): playable_ips.add(future_to_ip[future])

    # 写入文件逻辑
    beijing_now = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(IPTV_FILE), exist_ok=True)
    with open(IPTV_FILE, "w", encoding="utf-8") as f:
        f.write(f"更新时间,#genre#\n{beijing_now},#genre#\n\n")
        for cat, ch_list in CHANNEL_CATEGORIES.items():
            f.write(f"{cat},#genre#\n")
            for target in ch_list:
                for ip in playable_ips:
                    for line in ip_groups[ip]:
                        ch_name, url = line.split(",", 1)
                        if ch_name == target or ch_name in CHANNEL_MAPPING.get(target, []):
                            f.write(f"{target},{url}\n")
            f.write("\n")

    # 备份
    with open(IPTV_FILE, "r", encoding="utf-8") as s, open(LIVE_BACKUP_FILE, "w", encoding="utf-8") as d:
        d.write(s.read())
    print("🎯 IPTV.txt 与 live.txt 生成成功")

# ===============================
# Git 推送函数
# ===============================
def push_all_files():
    print("🚀 推送所有更新文件到 GitHub...")
    try:
        subprocess.run(['git', 'config', '--global', 'user.name', 'github-actions'], check=True)
        subprocess.run(['git', 'config', '--global', 'user.email', 'github-actions@users.noreply.github.com'], check=True)
        
        for f in [COUNTER_FILE, ZUBO_FILE, IPTV_FILE, LIVE_BACKUP_FILE]:
            if os.path.exists(f): subprocess.run(['git', 'add', f], check=False)
        if os.path.exists(IP_DIR): subprocess.run(['git', 'add', os.path.join(IP_DIR, "*.txt")], check=False)

        res = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if not res.stdout.strip(): return

        subprocess.run(['git', 'commit', '-m', f"自动更新 {datetime.now().strftime('%m-%d %H:%M')}"], check=True)
        subprocess.run(['git', 'pull', 'origin', 'main', '--rebase', '--autostash'], check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        print("✅ 推送成功！")
    except Exception as e: print(f"❌ 推送失败: {e}")

# ===============================
# 主程序
# ===============================
if __name__ == "__main__":
    run_count = first_stage()
    if run_count % 10 == 0:
        second_stage()
        third_stage()
    push_all_files()
