#!/usr/bin/env python3
"""
球队名称翻译工具 - 英文转中文
"""

TEAM_NAME_TRANSLATIONS = {
    # 英超
    "Manchester United": "曼联",
    "Manchester City": "曼彻斯特城/曼城",
    "Liverpool": "利物浦",
    "Chelsea": "切尔西",
    "Arsenal": "阿森纳",
    "Tottenham Hotspur": "托特纳姆热刺",
    "Tottenham": "托特纳姆热刺",
    "Newcastle United": "纽卡斯尔/纽卡斯尔联",
    "Newcastle": "纽卡斯尔/纽卡斯尔联",
    "Brighton and Hove Albion": "布莱顿",
    "Brighton": "布莱顿",
    "Aston Villa": "阿斯顿维拉",
    "West Ham United": "西汉姆联",
    "West Ham": "西汉姆联",
    "Crystal Palace": "水晶宫",
    "Fulham": "富勒姆",
    "Wolverhampton Wanderers": "狼队",
    "Wolves": "狼队",
    "Everton": "埃弗顿",
    "Brentford": "布伦特福德",
    "Nottingham Forest": "诺丁汉森林",
    "Bournemouth": "伯恩茅斯",
    "Leeds United": "利兹联",
    "Leeds": "利兹联",
    "Leicester City": "莱斯特城",
    "Leicester": "莱斯特城",
    "Southampton": "南安普顿",
    "Ipswich Town": "伊普斯维奇",
    "Ipswich": "伊普斯维奇",
    "Luton Town": "卢顿",
    "Luton": "卢顿",
    "Sheffield United": "谢菲尔德联",
    "Sheffield": "谢菲尔德联",
    "Burnley": "伯恩利",

    # 西甲
    "Real Madrid": "皇家马德里",
    "Barcelona": "巴塞罗那",
    "Atletico Madrid": "马德里竞技",
    "Atlético Madrid": "马德里竞技",
    "Sevilla": "塞维利亚",
    "Real Sociedad": "皇家社会",
    "Villarreal": "比利亚雷亚尔",
    "Real Betis": "皇家贝蒂斯",
    "Athletic Bilbao": "毕尔巴鄂竞技",
    "Girona": "赫罗纳",
    "Valencia": "瓦伦西亚/巴伦西亚",
    "Osasuna": "奥萨苏纳",
    "CA Osasuna": "奥萨苏纳",
    "Celta Vigo": "塞尔塔",
    "Mallorca": "马洛卡",
    "RCD Mallorca": "马洛卡",
    "Getafe": "赫塔费/赫塔菲",
    "Cadiz": "加的斯",
    "Alaves": "阿拉维斯",
    "Alavés": "阿拉维斯",
    "Elche CF": "埃尔切",
    "Elche": "埃尔切",
    "Las Palmas": "拉斯帕尔马斯",
    "Rayo Vallecano": "巴列卡诺",
    "Espanyol": "西班牙人",
    "Levante": "莱万特",
    "Levante UD": "莱万特",
    "Real Oviedo": "皇家奥维耶多",
    "Oviedo": "皇家奥维耶多",

    # 葡超
    "Porto": "波尔图",
    "SC Braga": "布拉加",
    "Braga": "布拉加",

    # 南美球队
    "Palmeiras-SP": "帕尔梅拉斯",
    "Palmeiras": "帕尔梅拉斯",
    "Sporting Cristal": "水晶竞技",
    "Flamengo-RJ": "弗拉门戈",
    "Flamengo": "弗拉门戈",
    "Independiente Medellín": "麦德林独立",
    "Peñarol Montevideo": "佩纳罗尔",
    "Platense": "普拉滕斯",
    "Libertad Asuncion": "亚松森自由",
    "Independiente del Valle": "山谷独立",
    "Lanus": "拉努斯",
    "Club Always Ready": "时刻准备",

    # 德甲
    "Bayern Munich": "拜仁慕尼黑",
    "Borussia Dortmund": "多特蒙德",
    "RB Leipzig": "莱比锡红牛",
    "Bayer Leverkusen": "勒沃库森",
    "Union Berlin": "柏林联合",
    "Freiburg": "弗赖堡",
    "Eintracht Frankfurt": "法兰克福",
    "Wolfsburg": "沃尔夫斯堡",
    "Mainz 05": "美因茨",
    "FSV Mainz 05": "美因茨",
    "Borussia Monchengladbach": "门兴格拉德巴赫",
    "Mönchengladbach": "门兴格拉德巴赫",
    "Borussia Mönchengladbach": "门兴格拉德巴赫",
    "Hoffenheim": "霍芬海姆",
    "TSG Hoffenheim": "霍芬海姆",
    "Hamburger SV": "汉堡",
    "HSV": "汉堡",
    "Werder Bremen": "不莱梅",
    "Augsburg": "奥格斯堡",
    "VfB Stuttgart": "斯图加特",
    "Stuttgart": "斯图加特",
    "Heidenheim": "海登海姆",
    "Bochum": "波鸿",
    "FC Koln": "科隆",
    "1. FC Köln": "科隆",
    "1. FC Koln": "科隆",
    "St. Pauli": "圣保利",
    "FC St. Pauli": "圣保利",
    "St Pauli": "圣保利",

    # 希腊球队
    "AEK Athens": "AEK雅典",

    # 意甲
    "Bologna": "博洛尼亚",
    "Inter Milan": "国际米兰",
    "Inter": "国际米兰",
    "AC Milan": "AC米兰",
    "Milan": "AC米兰",
    "Juventus": "尤文图斯",
    "Napoli": "那不勒斯",
    "Roma": "罗马",
    "Lazio": "拉齐奥",
    "Atalanta": "亚特兰大",
    "Fiorentina": "佛罗伦萨",
    "Torino": "都灵",
    "Monza": "蒙扎",
    "Udinese": "乌迪内斯",
    "Sassuolo": "萨索洛",
    "Empoli": "恩波利",
    "Cagliari": "卡利亚里",
    "Verona": "维罗纳",
    "Lecce": "莱切",
    "Salernitana": "萨勒尼塔纳",
    "Frosinone": "弗洛西诺内",
    "Genoa": "热那亚",
    "Pisa": "比萨",

    # 法甲
    "Paris Saint Germain": "巴黎圣日耳曼",
    "PSG": "巴黎圣日耳曼",
    "Angers": "昂热",
    "Marseille": "马赛",
    "Monaco": "摩纳哥",
    "Lyon": "里昂",
    "Lille": "里尔",
    "Nice": "尼斯",
    "Rennes": "雷恩",
    "Lens": "朗斯",
    "Montpellier": "蒙彼利埃",
    "Amiens": "亚眠",
    "Amiens SC": "亚眠",
    "Strasbourg": "斯特拉斯堡",
    "Toulouse": "图卢兹",
    "Nantes": "南特",
    "Reims": "兰斯",
    "Brest": "布雷斯特",
    "Le Havre": "勒阿弗尔",
    "Metz": "梅斯",
    "Lorient": "洛里昂",
    "Clermont": "克莱蒙",

    # 法乙
    "USL Dunkerque": "敦刻尔克",
    "Dunkerque": "敦刻尔克",
    "Laval": "拉瓦勒",
    "Rodez": "罗德兹",
    "Rodez AF": "罗德兹",

    # 欧冠/欧联常用
    "Bayern": "拜仁",
    "Dortmund": "多特蒙德",
    "Porto": "波尔图",
    "Benfica": "本菲卡",
    "Sporting CP": "葡萄牙体育",
    "Sporting Lisbon": "葡萄牙体育",
    "Ajax": "阿贾克斯",
    "PSV": "埃因霍温",
    "Feyenoord": "费耶诺德",
    "Celtic": "凯尔特人",
    "Rangers": "流浪者",
    "Galatasaray": "加拉塔萨雷",
    "Fenerbahce": "费内巴切",
    "Shakhtar Donetsk": "顿涅茨克矿工",
    "Salzburg": "萨尔茨堡红牛",
    "Dinamo Zagreb": "萨格勒布迪纳摩",
    # 澳大利亚A联赛
    "Sydney FC": "悉尼FC",
    "Perth Glory": "珀斯光荣",
    # 韩国K联赛
    "Ulsan Hyundai FC": "蔚山现代",
    "Gwangju FC": "光州FC",
    "FC Anyang": "安养FC",
    "Pohang Steelers": "浦项制铁",
    "Jeonbuk Hyundai Motors": "全北现代",
    "Seongnam FC": "城南FC",
    "Sangju Sangmu FC": "金泉尙午",
    "Incheon United": "仁川联",
    "Suwon Samsung Bluewings": "水原三星",
    "Daegu FC": "大邱FC",
    "Jeju United": "济州联",
    "Gangwon FC": "江原FC",
    "Seoul FC": "首尔FC",
    # 日本J联赛
    "Gamba Osaka": "大阪钢巴",
    "Fagiano Okayama": "冈山绿雉",
    "Nagoya Grampus": "名古屋鲸八",
    "Avispa Fukuoka": "福冈黄蜂",
    # 英冠/英超
    "Sunderland": "桑德兰",
    "Middlesbrough": "米德尔斯堡",
    "Oxford United": "牛津联",
    "Rotherham United": "罗瑟汉姆",
    "Wrexham": "雷克瑟姆",
    "Wrexham AFC": "雷克瑟姆",
    "Bristol City": "布里斯托城",
    "West Bromwich Albion": "西布罗姆维奇",
    "West Brom": "西布朗",
    "Watford": "沃特福德",
    # 德乙
    "Greuther Fürth": "菲尔特",
    "SpVgg Greuther Fürth": "菲尔特",
    "Darmstadt": "达姆施塔特",
    "SV Darmstadt 98": "达姆施塔特",
    "1. FC Kaiserslautern": "凯泽斯劳滕",
    "Kaiserslautern": "凯泽斯劳滕",
    "Eintracht Braunschweig": "布伦瑞克",
    "Braunschweig": "布伦瑞克",
    "Fortuna Düsseldorf": "杜塞尔多夫",
    "Fortuna Dusseldorf": "杜塞尔多夫",
    "Dynamo Dresden": "德累斯顿",
    "Dresden": "德累斯顿",
    # 意甲
    "Cremonese": "克雷莫纳",
    "US Cremonese": "克雷莫纳",
    "Como": "科莫",
    # 瑞典超
    "AIK": "索尔纳",
    "AIK Solna": "索尔纳",
    "Kalmar": "卡尔玛",
    "Kalmar FF": "卡尔玛",
    # 挪威超
    "Vålerenga": "瓦勒伦加",
    "Vålerenga Fotball": "瓦勒伦加",
    "Lillestrøm": "利勒斯特罗姆",
    "Lillestrøm SK": "利勒斯特罗姆",
    "Rosenborg": "罗森博格",
    "Bodø/Glimt": "博多格林特",
    "Molde": "莫尔德",
    "Sarpsborg": "萨尔普斯堡",
    "Sarpsborg 08": "萨尔普斯堡",
    "Tromsø": "特罗姆瑟",
    "Tromsø IL": "特罗姆瑟",
    "Tromso": "特罗姆瑟",
    "Viking": "维京",
    "Brann": "布兰",
    
    # 瑞典超扩展
    "Häcken": "赫根",
    "BK Hacken": "赫根",
    "GAIS": "加尔斯",
    "Malmö FF": "马尔默",
    "Malmo FF": "马尔默",
    "Djurgårdens IF": "尤尔加登",
    "Hammarby IF": "哈马比",
    "IFK Göteborg": "哥德堡",
    "Sirius": "天狼星",
    "IFK Sirius": "天狼星",
    "IK Sirius": "天狼星",
    
    # 荷甲
    "AZ Alkmaar": "阿尔克马尔",
    "NEC Nijmegen": "奈梅亨",
    "Ajax": "阿贾克斯",
    "PSV": "埃因霍温",
    "PSV Eindhoven": "埃因霍温",
    "Feyenoord": "费耶诺德",
    "Groningen": "格罗宁根",
    "FC Groningen": "格罗宁根",
    "FC Twente": "特温特",
    "Go Ahead Eagles": "前进之鹰",
    "PEC Zwolle": "兹沃勒",
    "Zwolle": "兹沃勒",
    
    # 葡超
    "Braga": "布拉加",
    "SC Braga": "布拉加",
    "Casa Pia": "卡萨比亚",
    "Casa Pia AC": "卡萨比亚",
    "Famalicão": "法马利康",
    "FC Famalicão": "法马利康",
    "Porto": "波尔图",
    "Benfica": "本菲卡",
    "Sporting CP": "葡萄牙体育",
    "Sporting Lisbon": "葡萄牙体育",
    "Moreirense": "摩里伦斯/库里伦斯",
    "Moreirense FC": "摩里伦斯/库里伦斯",
    "Estoril": "埃斯托里尔",
    "Estoril Praia": "埃斯托里尔",

    # 美职联
    "Los Angeles FC": "洛杉矶FC",
    "LAFC": "洛杉矶FC",
    "San Jose Earthquakes": "圣何塞地震",
    "San Jose": "圣何塞地震",
    "Seattle Sounders": "西雅图海湾人",
    "New York City FC": "纽约城",
    "Inter Miami": "国际迈阿密",
    
    # 日本J联赛扩展
    "Kawasaki Frontale": "川崎前锋",
    "Kashima Antlers": "鹿岛鹿角",
    "Kashiwa Reysol": "柏太阳神",
    "Urawa Red Diamonds": "浦和红钻",
    "Yokohama F. Marinos": "横滨水手",
    "Sanfrecce Hiroshima": "广岛三箭",
    "Cerezo Osaka": "大阪樱花",
    "Vissel Kobe": "神户胜利船",
    "FC Tokyo": "东京FC",
    
    # 美职联
    "Nashville SC": "纳什威尔SC",
    "Charlotte FC": "夏洛特FC",
    
    # 韩国K联赛扩展
    "Jeonbuk Hyundai Motors": "全北现代",
    "Pohang Steelers": "浦项制铁",
    "Suwon Samsung Bluewings": "水原三星",
    "FC Seoul": "首尔FC",
    "Daegu FC": "大邱FC",
    "Jeju United": "济州联",
    "Incheon United": "仁川联",
    "Gangwon FC": "江原FC",
    "Ulsan Hyundai": "蔚山现代",
    "Seongnam FC": "城南FC",
    
    # 意乙
    "Parma": "帕尔马",
    "Bari": "巴里",
    "Brescia": "布雷西亚",
    "Cosenza": "科森扎",
    "Crotone": "克罗托内",
    "Genoa": "热那亚",
    "Pisa": "比萨",
    "Lecce": "莱切",
    "Palermo": "巴勒莫",
    "Salernitana": "萨勒尼塔纳",
    "Sampdoria": "桑普多利亚",
    "Sassuolo": "萨索洛",
    "Venezia": "威尼斯",
    
    # 澳大利亚A联赛
    "Macarthur FC": "麦克阿瑟FC",
    "Wellington Phoenix FC": "惠灵顿凤凰",
    "Wellington Phoenix": "惠灵顿凤凰",
    "Newcastle Jets": "纽卡斯尔喷射机",
    "Newcastle Jets FC": "纽卡斯尔喷射机",
    "Central Coast Mariners": "中央海岸水手",
    "Western Sydney Wanderers": "西悉尼流浪者",
    "Melbourne Victory": "墨尔本胜利",
    "SC Preußen Münster": "普鲁士明斯特",
    "Preußen Münster": "普鲁士明斯特",
    "Arminia Bielefeld": "比勒菲尔德",
    # 芬兰超级联赛
    "TPS Turku": "TPS土尔库",
    "IF Gnistan": "格尼斯坦",
    "Gnistan": "格尼斯坦",
    # 沙特阿拉伯联赛
    "Al-Nassr": "阿尔纳泽马",
    "Al Nassr": "阿尔纳泽马",
    "Al-Taawoun": "布赖代合作",
    "Al Taawoun": "布赖代合作",
    "Al-Ahli": "阿尔阿赫利",
    "Al Ahli": "阿尔阿赫利",
    "Al-Najma": "阿尔纳吉马",
    "Al Najma": "阿尔纳吉马",
    "Al-Hazem": "哈森姆",
    "Al Hazem": "哈森姆",
    "Al-Riyadh": "利亚德体育",
    "Al Riyadh": "利亚德体育",
    # Portuguese League
    "Alverca": "艾华卡",
    "Arouca": "阿罗卡",
}

def translate_team_name(english_name: str) -> str:
    """
    将英文球队名称翻译为中文

    Args:
        english_name: 英文球队名称

    Returns:
        中文球队名称，如果没有对应翻译则返回原名称
    """
    # 精确匹配
    if english_name in TEAM_NAME_TRANSLATIONS:
        return TEAM_NAME_TRANSLATIONS[english_name]

    # 模糊匹配（包含关系）
    for en, cn in TEAM_NAME_TRANSLATIONS.items():
        if en.lower() in english_name.lower() or english_name.lower() in en.lower():
            return cn

    # 如果没有找到翻译，返回原名称
    return english_name


def translate_match_info(match_info: dict) -> dict:
    """
    翻译比赛信息中的队伍名称

    Args:
        match_info: 包含 home_team 和 away_team 的字典

    Returns:
        翻译后的比赛信息字典
    """
    translated = match_info.copy()
    translated["home_team_cn"] = translate_team_name(match_info.get("home_team", ""))
    translated["away_team_cn"] = translate_team_name(match_info.get("away_team", ""))
    return translated


# 测试
if __name__ == "__main__":
    test_teams = [
        "Manchester United",
        "Chelsea",
        "Real Madrid",
        "Barcelona",
        "Bayern Munich",
        "Paris Saint Germain"
    ]

    print("球队名称翻译测试:")
    for team in test_teams:
        print(f"  {team} -> {translate_team_name(team)}")
