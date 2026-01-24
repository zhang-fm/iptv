import os
import re
import socket
import urllib3
from concurrent.futures import ThreadPoolExecutor

# 1. 屏蔽 SSL 警告（虽然本地读取用不到，但保留以防万一）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 配置区 ---
# 修正：直接指向本地库路径。假设脚本在 py/ 文件夹下。
# 使用相对路径，确保在 GitHub Action 运行环境（根目录）下能找到。
LOCAL_IP_FILE = "ip/重庆市联通.txt"
LOCAL_RTP_FILE = "rtp/四川电信.txt"
LOGO_PREFIX = "https://gcore.jsdelivr.net/gh/kenye201/TVlog/img/"

# 输出路径：项目根目录下的 test/sc_telecom.m3u
BASE_DIR = os.getcwd() 
OUTPUT_DIR = os.path.join(BASE_DIR, "test")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sc_telecom.m3u")

def read_local_file(file_path):
    """读取本地文件内容"""
    try:
        if not os.path.exists(file_path):
            print(f"❌ 错误：找不到本地文件 {file_path}")
            return ""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"读取文件失败: {file_path}, 错误: {e}")
        return ""

def check_port(server):
    """探测单个端口存活"""
    try:
        host, port = server.split(':')
        with socket.create_connection((host, int(port)), timeout=1.0):
            return server
    except:
        return None

def main():
    # 自动创建 test 目录
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 已创建目录: {OUTPUT_DIR}")

    print("🚀 开始读取本地资源并扫描 (多线程模式)...")
    
    # 修改：改为从本地读取
    ips_raw = read_local_file(LOCAL_IP_FILE)
    rtps_raw = read_local_file(LOCAL_RTP_FILE)

    if not ips_raw or not rtps_raw:
        print("❌ 核心本地数据读取失败。请检查文件路径是否正确。")
        return

    # 提取 IP:PORT 格式
    ip_list = sorted(list(set(re.findall(r'(\d+\.\d+\.\d+\.\d+:\d+)', ips_raw))))
    print(f"📊 找到待测服务器: {len(ip_list)} 个")

    # 多线程扫描
    print(f"🔍 正在扫描端口 (并发数: 20)...")
    alive_servers = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(check_port, ip_list))
        for res in results:
            if res:
                print(f" [√] 在线: {res}")
                alive_servers.append(res)
                if len(alive_servers) >= 10: # 找到10个存活的就停下，防止文件过大
                    break
    
    if not alive_servers:
        print("❌ 未发现存活服务器，无法生成 M3U。")
        return

    # 频道解析
    channels = []
    for line in rtps_raw.split('\n'):
        line = line.strip()
        if line and ',' in line:
            parts = line.split(',')
            name = parts[0].strip()
            rtp_addr = parts[1].strip()
            if rtp_addr:
                # 清洗 rtp:// 前缀
                clean_rtp = rtp_addr.replace("rtp://", "")
                channels.append({
                    "name": name,
                    "rtp": clean_rtp,
                    "logo": f"{LOGO_PREFIX}{name}.png",
                    "is_4k": "4K" in name.upper()
                })

    # 生成 M3U 内容
    m3u_content = '#EXTM3U x-tvg-url="https://live.fanmingming.cn/e.xml"\n\n'
    for idx, server in enumerate(alive_servers, 1):
        for chan in channels:
            group_prefix = "四川4K-" if chan['is_4k'] else "四川电信"
            group_title = f"{group_prefix}{idx}"
            
            m3u_content += f'#EXTINF:-1 tvg-name="{chan["name"]}" tvg-logo="{chan["logo"]}" group-title="{group_title}",{chan["name"]}\n'
            m3u_content += f'http://{server}/rtp/{chan["rtp"]}\n\n'

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    
    print(f"✅ 完成！有效服务器 {len(alive_servers)} 个，结果存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
