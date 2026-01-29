import os
import re

# ===============================
# 配置区
# ===============================
INPUT_FILE = "test/IPTV.txt"          # 输入文件
OUTPUT_FILE = "test/IPTV.m3u"             # 输出文件
LOGO_BASE = "https://gcore.jsdelivr.net/gh/kenye201/TVlog/img/"
EPG_URL = "https://live.fanmingming.cn/e.xml"

def get_logo_url(ch_name):
    name = ch_name.strip()
    name = re.sub(r"[ -_]?(HD|高清|4K|超清|超高清|8K|plus|\+|\s*Ⅰ|Ⅱ|Ⅲ|Ⅳ|Ⅴ)$", "", name, flags=re.IGNORECASE)
    name = name.replace(" ", "").replace("&", "")
    return f"{LOGO_BASE}{name}.png"

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 找不到 {INPUT_FILE}")
        return

    print(f"正在读取 {INPUT_FILE} 并尝试保留原始分类结构...")
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(f'#EXTM3U x-tvg-url="{EPG_URL}"\n\n')

        current_group = "未分组"  # 默认分组

        for line in lines:
            original_line = line.rstrip()
            stripped = line.strip()

            if not stripped:
                out.write(original_line + "\n")
                continue

            # 分组标题行
            if stripped.endswith(",#genre#"):
                group_name = stripped.split(",")[0].strip()
                current_group = group_name if group_name else "未分组"
                continue  # 不写入分组标题（播放器不需要）

            # 公告行
            if "更新时间" in stripped or "GitHub" in stripped or "作者" in stripped:
                parts = stripped.split(",", 1)
                if len(parts) == 2:
                    title, url = parts
                    out.write(f'#EXTINF:-1 group-title="公告说明",{title.strip()}\n{url.strip()}\n\n')
                continue

            # 频道行
            if "," in stripped:
                try:
                    ch_name, full_url = stripped.split(",", 1)
                    ch_name = ch_name.strip()
                    full_url = full_url.strip()

                    logo = get_logo_url(ch_name)

                    out.write(
                        f'#EXTINF:-1 tvg-name="{ch_name}" tvg-logo="{logo}" '
                        f'group-title="{current_group}",{ch_name}\n'
                    )
                    out.write(f"{full_url}\n\n")

                except Exception as e:
                    print(f"跳过错误行: {stripped} → {e}")

            # 其他行原样保留
            else:
                out.write(original_line + "\n")

    print(f"转换完成！已生成 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
