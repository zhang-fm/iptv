import os
import re

# --- 配置区 ---
RTP_DIR = "rtp"
# 目标改为 livezubo.txt
INPUT_TXT = "py/livezubo.txt"  
OUTPUT_TXT = "py/live_full.txt"

def get_live_servers():
    """从 livezubo.txt 提取存活的 IP 和地区"""
    servers = {} # {"湖北电信": {"58.50.205.3:4022", ...}}
    if not os.path.exists(INPUT_TXT):
        print(f"❌ 找不到输入文件: {INPUT_TXT}")
        return servers

    print(f"📖 正在从 {INPUT_TXT} 提取有效服务器...")
    with open(INPUT_TXT, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or "#genre#" in line:
                continue
            
            # 匹配格式: 频道名,http://124.77.177.88:5555/rtp/239.253.10.1:5140$上海市电信
            # 提取 IP:端口 (124.77.177.88:5555) 和 注释 (上海市电信)
            match = re.search(r'http://([\d\.]+:\d+)/rtp/.*?\$([\u4e00-\u9fa5]+)', line)
            if match:
                ip_port = match.group(1)
                region = match.group(2)
                
                # 进一步清洗地区名，只保留省份/运营商核心词（例如：上海市电信 -> 上海电信）
                clean_region = region.replace("市", "")
                
                if clean_region not in servers:
                    servers[clean_region] = set()
                servers[clean_region].add(ip_port)
    
    print(f"✅ 提取到的活服务器地区: {list(servers.keys())}")
    return servers

def generate():
    live_servers = get_live_servers()
    if not live_servers:
        print("❌ 未提取到任何有效 IP，请检查 livezubo.txt 格式。")
        return

    output_lines = []
    if not os.path.exists(RTP_DIR):
        print(f"❌ 找不到 rtp 目录")
        return

    # 获取 rtp 目录下所有的地区文件
    rtp_files = [f for f in os.listdir(RTP_DIR) if f.endswith(".txt")]
    
    # 模拟分类头部
    output_lines.append("全量更新,#genre#")

    for region_file in sorted(rtp_files):
        # rtp/湖北电信.txt -> region_key = 湖北电信
        region_key = region_file.replace(".txt", "").replace("市", "")
        
        # 匹配：如果 rtp 里的文件名（如湖北电信）在 livezubo 的存活地区里
        if region_key in live_servers:
            print(f"🔗 正在缝合地区: {region_key}")
            with open(os.path.join(RTP_DIR, region_file), 'r', encoding='utf-8') as f:
                rtp_content = f.readlines()
            
            for ip_port in live_servers[region_key]:
                for line in rtp_content:
                    line = line.strip()
                    if "," in line and "#genre#" not in line:
                        ch_name, rtp_addr = line.split(',', 1)
                        # 提取组播地址
                        m = re.search(r'(\d+\.\d+\.\d+\.\d+:\d+)', rtp_addr)
                        if m:
                            multicast = m.group(1)
                            # 拼接：频道,http://IP:PORT/rtp/组播地址$地区
                            output_lines.append(f"{ch_name},http://{ip_port}/rtp/{multicast}${region_key}")

    with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
        f.write("\n".join(output_lines))
    print(f"✨ 处理完成！文件 {OUTPUT_TXT} 已生成，共 {len(output_lines)} 条线路。")

if __name__ == "__main__":
    generate()
