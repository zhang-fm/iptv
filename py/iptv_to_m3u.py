import re
import os
import requests

# ===============================
# 配置区
# ===============================
# 修正 1: TARGET_URL 改为本地读取，因为 Action 运行环境里文件已经下载了
TARGET_FILE = "test/IPTV.txt" 
# 修正 2: 修复字符串引号错误
OUTPUT_FILE = "test/IPTV.m3u"

LOGO_BASE = "https://gcore.jsdelivr.net/gh/kenye201/TVlog/img/"
EPG_URL = "https://live.fanmingming.cn/e.xml"

# ... 工具函数保持不变 (clean_group_name, get_logo_url, is_valid_url) ...

def clean_group_name(text: str) -> str:
    return text.strip().rstrip(":：")

def get_logo_url(name: str) -> str:
    n = name.strip()
    n = re.sub(r"[ -_]HD|高清|超清|4K|8K|\+|PLUS|Ⅰ|Ⅱ|Ⅲ|Ⅳ|Ⅴ", "", n, flags=re.IGNORECASE)
    if n.upper().startswith("CCTV"):
        n = n.replace("-", "").replace(" ", "")
        if "欧洲" in n or "美洲" in n:
            n = "CCTV4"
    return f"{LOGO_BASE}{n.upper()}.png"

def is_valid_url(url: str) -> bool:
    return bool(re.match(r"^(https?|rtp|udp)://", url, re.IGNORECASE))

# ===============================
# 主逻辑
# ===============================
def main():
    # 修正 3: 直接读取本地文件，不需要 requests
    if not os.path.exists(TARGET_FILE):
        print(f"❌ 找不到源文件: {TARGET_FILE}")
        return

    print(f"📖 正在处理本地文件: {TARGET_FILE}")
    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_group = "未分类"
    m3u_lines = [f'#EXTM3U x-tvg-url="{EPG_URL}"'] # 注意这里去掉内部换行，后面统一join

    for line in lines:
        line = line.strip()
        if not line: continue
        if "#genre#" in line:
            raw_group = line.split(",", 1)[0]
            current_group = clean_group_name(raw_group)
            continue
        if "," not in line: continue

        parts = line.split(",", 1)
        name, url = parts[0].strip(), parts[1].strip()

        if not name or not is_valid_url(url): continue

        logo = get_logo_url(name)
        m3u_lines.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{current_group}",{name}')
        m3u_lines.append(url)

    # 写入文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

    print(f"✅ 转换完成：{OUTPUT_FILE}")

if __name__ == "__main__":
    main()
