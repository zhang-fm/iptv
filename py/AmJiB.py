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
    "央视频道": [
        "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV4欧洲", "CCTV4美洲", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
        "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15", "CCTV16", "CCTV17", "CCTV4K", "CCTV8K",
        "兵器科技", "风云音乐", "风云足球", "风云剧场", "怀旧剧场", "第一剧场", "女性时尚", "世界地理", "央视台球", "高尔夫网球",
        "央视文化精品", "卫生健康", "电视指南", "中学生", "发现之旅", "书法频道", "国学频道", "环球奇观"
    ],
    "卫视频道": [
        "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "深圳卫视", "北京卫视", "广东卫视", "广西卫视", "东南卫视", "海南卫视",
        "河北卫视", "河南卫视", "湖北卫视", "江西卫视", "四川卫视", "重庆卫视", "贵州卫视", "云南卫视", "天津卫视", "安徽卫视",
        "山东卫视", "辽宁卫视", "黑龙江卫视", "吉林卫视", "内蒙古卫视", "宁夏卫视", "山西卫视", "陕西卫视", "甘肃卫视", "青海卫视",
        "新疆卫视", "西藏卫视", "三沙卫视", "兵团卫视", "延边卫视", "安多卫视", "康巴卫视", "农林卫视", "山东教育卫视",
        "中国教育1台", "中国教育2台", "中国教育3台", "中国教育4台", "早期教育"
    ],
    "数字频道": [
        "CHC动作电影", "CHC家庭影院", "CHC影迷电影", "淘电影", "淘精彩", "淘剧场", "淘4K", "淘娱乐", "淘BABY", "淘萌宠", "重温经典",
        "星空卫视", "CHANNEL[V]", "凤凰卫视中文台", "凤凰卫视资讯台", "凤凰卫视香港台", "凤凰卫视电影台", "求索纪录", "求索科学",
        "求索生活", "求索动物", "纪实人文", "金鹰纪实", "纪实科教", "睛彩青少", "睛彩竞技", "睛彩篮球", "睛彩广场舞", "魅力足球", "五星体育",
        "劲爆体育", "快乐垂钓", "茶频道", "先锋乒羽", "天元围棋", "汽摩", "梨园频道", "文物宝库", "武术世界", "哒啵赛事", "哒啵电竞", "黑莓电影", "黑莓动画", 
        "乐游", "生活时尚", "都市剧场", "欢笑剧场", "游戏风云", "金色学堂", "动漫秀场", "新动漫", "卡酷少儿", "金鹰卡通", "优漫卡通", "哈哈炫动", "嘉佳卡通", 
        "中国交通", "中国天气", "华数4K", "华数星影", "华数动作影院", "华数喜剧影院", "华数家庭影院", "华数经典电影", "华数热播剧场", "华数碟战剧场",
        "华数军旅剧场", "华数城市剧场", "华数武侠剧场", "华数古装剧场", "华数魅力时尚", "华数少儿动画", "华数动画"
    ],
    "4K频道": [
         "东方卫视4K","北京卫视4K","江苏卫视4K","浙江卫视4K","湖南卫视4K","深圳卫视4K","四川卫视4K","山东卫视4K", "广东卫视4K"
    ],
    "湖北": [
        "湖北公共新闻", "湖北经视频道", "湖北综合频道", "湖北垄上频道", "湖北影视频道", "湖北生活频道", "湖北教育频道", "武汉新闻综合", "武汉电视剧", "武汉科技生活",
        "武汉文体频道", "武汉教育频道", "阳新综合", "房县综合", "蔡甸综合",
    ],
    "山西": [
        "山西黄河HD", "山西经济与科技HD", "山西影视HD", "山西社会与法治HD", "山西文体生活HD",
    ],
    "福建": [
        "福建综合", "福建新闻", "福建经济", "福建电视剧", "福建公共", "福建少儿", "泉州电视台", "福州电视台",
    ],
     "大湾区": [
         "广东珠江","广东体育","广东新闻","广东民生","广东影视","广东综艺","岭南戏曲","广东经济科教", "广州综合","广州新闻","广州影视","广州竞赛","广州法治","广州南国都市","佛山综合",
    ],
}

# ===== 映射（别名 -> 标准名） =====
CHANNEL_MAPPING = {
    "CCTV1": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV-1综合"],
    "CCTV2": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV-2财经"],
    "CCTV3": ["CCTV-3", "CCTV-3 HD", "CCTV3 HD", "CCTV-3综艺"],
    "CCTV4": ["CCTV-4", "CCTV-4 HD", "CCTV4 HD", "CCTV-4中文国际"],
    "CCTV4欧洲": ["CCTV-4欧洲", "CCTV-4欧洲", "CCTV4欧洲 HD", "CCTV-4 欧洲", "CCTV-4中文国际欧洲", "CCTV4中文欧洲"],
    "CCTV4美洲": ["CCTV-4美洲", "CCTV-4北美", "CCTV4美洲 HD", "CCTV-4 美洲", "CCTV-4中文国际美洲", "CCTV4中文美洲"],
    "CCTV5": ["CCTV-5", "CCTV-5 HD", "CCTV5 HD", "CCTV-5体育"],
    "CCTV5+": ["CCTV-5+", "CCTV-5+ HD", "CCTV5+ HD", "CCTV-5+体育赛事"],
    "CCTV6": ["CCTV-6", "CCTV-6 HD", "CCTV6 HD", "CCTV-6电影"],
    "CCTV7": ["CCTV-7", "CCTV-7 HD", "CCTV7 HD", "CCTV-7国防军事"],
    "CCTV8": ["CCTV-8", "CCTV-8 HD", "CCTV8 HD", "CCTV-8电视剧"],
    "CCTV9": ["CCTV-9", "CCTV-9 HD", "CCTV9 HD", "CCTV-9纪录"],
    "CCTV10": ["CCTV-10", "CCTV-10 HD", "CCTV10 HD", "CCTV-10科教"],
    "CCTV11": ["CCTV-11", "CCTV-11 HD", "CCTV11 HD", "CCTV-11戏曲"],
    "CCTV12": ["CCTV-12", "CCTV-12 HD", "CCTV12 HD", "CCTV-12社会与法"],
    "CCTV13": ["CCTV-13", "CCTV-13 HD", "CCTV13 HD", "CCTV-13新闻"],
    "CCTV14": ["CCTV-14", "CCTV-14 HD", "CCTV14 HD", "CCTV-14少儿"],
    "CCTV15": ["CCTV-15", "CCTV-15 HD", "CCTV15 HD", "CCTV-15音乐"],
    "CCTV16": ["CCTV-16", "CCTV-16 HD", "CCTV-16 4K", "CCTV-16奥林匹克", "CCTV16 4K", "CCTV-16奥林匹克4K"],
    "CCTV17": ["CCTV-17", "CCTV-17 HD", "CCTV17 HD", "CCTV-17农业农村"],
    "CCTV4K": ["CCTV4K超高清", "CCTV-4K超高清", "CCTV-4K 超高清", "CCTV 4K"],
    "CCTV8K": ["CCTV8K超高清", "CCTV-8K超高清", "CCTV-8K 超高清", "CCTV 8K"],
    "兵器科技": ["CCTV-兵器科技", "CCTV兵器科技"],
    "风云音乐": ["CCTV-风云音乐", "CCTV风云音乐"],
    "第一剧场": ["CCTV-第一剧场", "CCTV第一剧场"],
    "风云足球": ["CCTV-风云足球", "CCTV风云足球"],
    "风云剧场": ["CCTV-风云剧场", "CCTV风云剧场"],
    "怀旧剧场": ["CCTV-怀旧剧场", "CCTV怀旧剧场"],
    "女性时尚": ["CCTV-女性时尚", "CCTV女性时尚"],
    "世界地理": ["CCTV-世界地理", "CCTV世界地理"],
    "央视台球": ["CCTV-央视台球", "CCTV央视台球"],
    "高尔夫网球": ["CCTV-高尔夫网球", "CCTV高尔夫网球", "CCTV央视高网", "CCTV-高尔夫·网球", "央视高网"],
    "央视文化精品": ["CCTV-央视文化精品", "CCTV央视文化精品", "CCTV文化精品", "CCTV-文化精品", "文化精品"],
    "卫生健康": ["CCTV-卫生健康", "CCTV卫生健康"],
    "电视指南": ["CCTV-电视指南", "CCTV电视指南"],
    "中国教育1台": ["CETV1", "中国教育一台", "中国教育1", "CETV-1 综合教育", "CETV-1"],
    "中国教育2台": ["CETV2", "中国教育二台", "中国教育2", "CETV-2 空中课堂", "CETV-2"],
    "中国教育3台": ["CETV3", "中国教育三台", "中国教育3", "CETV-3 教育服务", "CETV-3"],
    "中国教育4台": ["CETV4", "中国教育四台", "中国教育4", "CETV-4 职业教育", "CETV-4"],
    "早期教育": ["中国教育5台", "中国教育五台", "CETV早期教育", "华电早期教育", "CETV 早期教育"],
    "CHC影迷电影": ["CHC高清电影", "CHC-影迷电影", "影迷电影", "chc高清电影"],
    "淘电影": ["IPTV淘电影", "北京IPTV淘电影", "北京淘电影"],
    "淘精彩": ["IPTV淘精彩", "北京IPTV淘精彩", "北京淘精彩"],
    "淘剧场": ["IPTV淘剧场", "北京IPTV淘剧场", "北京淘剧场"],
    "淘4K": ["IPTV淘4K", "北京IPTV4K超清", "北京淘4K", "淘4K", "淘 4K"],
    "淘娱乐": ["IPTV淘娱乐", "北京IPTV淘娱乐", "北京淘娱乐"],
    "淘BABY": ["IPTV淘BABY", "北京IPTV淘BABY", "北京淘BABY", "IPTV淘baby", "北京IPTV淘baby", "北京淘baby"],
    "淘萌宠": ["IPTV淘萌宠", "北京IPTV萌宠TV", "北京淘萌宠"],
    "魅力足球": ["上海魅力足球"],
    "睛彩青少": ["睛彩羽毛球"],
    "求索纪录": ["求索记录", "求索纪录4K", "求索记录4K", "求索纪录 4K", "求索记录 4K"],
    "金鹰纪实": ["湖南金鹰纪实", "金鹰记实"],
    "纪实科教": ["北京纪实科教", "BRTV纪实科教", "纪实科教8K"],
    "星空卫视": ["星空衛視", "星空衛视", "星空卫視"],
    "CHANNEL[V]": ["CHANNEL-V", "Channel[V]"],
    "凤凰卫视中文台": ["凤凰中文", "凤凰中文台", "凤凰卫视中文", "凤凰卫视"],
    "凤凰卫视香港台": ["凤凰香港台", "凤凰卫视香港", "凤凰香港"],
    "凤凰卫视资讯台": ["凤凰资讯", "凤凰资讯台", "凤凰咨询", "凤凰咨询台", "凤凰卫视咨询台", "凤凰卫视资讯", "凤凰卫视咨询"],
    "凤凰卫视电影台": ["凤凰电影", "凤凰电影台", "凤凰卫视电影", "鳳凰衛視電影台", " 凤凰电影"],
    "茶频道": ["湖南茶频道"],
    "快乐垂钓": ["湖南快乐垂钓"],
    "先锋乒羽": ["湖南先锋乒羽"],
    "天元围棋": ["天元围棋频道"],
    "汽摩": ["重庆汽摩", "汽摩频道", "重庆汽摩频道"],
    "梨园频道": ["河南梨园频道", "梨园", "河南梨园"],
    "文物宝库": ["河南文物宝库"],
    "武术世界": ["河南武术世界"],
    "乐游": ["乐游频道", "上海乐游频道", "乐游纪实", "SiTV乐游频道", "SiTV 乐游频道"],
    "欢笑剧场": ["上海欢笑剧场4K", "欢笑剧场 4K", "欢笑剧场4K", "上海欢笑剧场"],
    "生活时尚": ["生活时尚4K", "SiTV生活时尚", "上海生活时尚"],
    "都市剧场": ["都市剧场4K", "SiTV都市剧场", "上海都市剧场"],
    "游戏风云": ["游戏风云4K", "SiTV游戏风云", "上海游戏风云"],
    "金色学堂": ["金色学堂4K", "SiTV金色学堂", "上海金色学堂"],
    "动漫秀场": ["动漫秀场4K", "SiTV动漫秀场", "上海动漫秀场"],
    "卡酷少儿": ["北京KAKU少儿", "BRTV卡酷少儿", "北京卡酷少儿", "卡酷动画"],
    "哈哈炫动": ["炫动卡通", "上海哈哈炫动"],
    "优漫卡通": ["江苏优漫卡通", "优漫漫画"],
    "金鹰卡通": ["湖南金鹰卡通"],
    "中国交通": ["中国交通频道"],
    "中国天气": ["中国天气频道"],
    "华数4K": ["华数低于4K", "华数4K电影", "华数爱上4K"],
    "山西卫视": ["山西卫视高清"],
    "山西黄河HD": ["山西黄河", "黄河电视台高清"],
    "山西经济与科技HD": ["山西经济与科技", "山西经济与科技高清"],
    "山西社会与法治HD": ["山西社会与法治", "山西社会与法治高清"],
    "山西文体生活HD": ["山西文体生活", "山西文体生活高清"],
    "山西影视HD": ["山西影视", "山西影视高清"]  
}# 如需更多别名，可自行补回

# ===============================
# 第一阶段：IP 爬取与分类
# ===============================
# ===============================
# 第一阶段：IP 爬取与分类 (已增加地域过滤)
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

    # 定义排除名单
    exclude_provinces = ["江苏省", "浙江省", "上海市", "广东省"]
    
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
            
            # 提取省份和运营商
            province = data.get("regionName", "未知")
            isp_raw = (data.get("isp") or "").lower()
            isp = "电信" if "telecom" in isp_raw else "联通" if "unicom" in isp_raw else "移动" if "mobile" in isp_raw else "未知"
            
            # 🔥 核心修改：过滤“江浙沪广”的“电信”IP
            if isp == "电信" and any(p in province for p in exclude_provinces):
                print(f"⏩ 过滤排除区域：{province}{isp} ({ip_port})")
                continue

            if isp != "未知":
                fname = f"{province}{isp}.txt"
                province_isp_dict.setdefault(fname, set()).add(ip_port)
        except Exception as e: 
            print(f"⚠️ 归属地查询异常: {e}")
            continue

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
