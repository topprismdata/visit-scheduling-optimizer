"""
全国城市地貌与路网特征分类器 (City Terrain & Circuity Classifier)
文献基础:
1. Newell (1980) 交通网络拓扑与迂回系数 (Circuity Factors)
2. Ballou et al. (2002) 城市/郊区/山区实际行车距离对欧几里得距离的膨胀比率经验分布
3. 中国地理地理分界线与路网形态特征:
   - 平原/棋盘网 (Plain Grid): 绕行小, c ≈ 1.20 ~ 1.23
   - 珠三角/水网河汊 (Waterway Delta): 桥梁汇流与沿河绕行, c ≈ 1.28 ~ 1.30
   - 山地/重丘/高原 (Mountainous): 沿山谷盘山绕行大, c ≈ 1.33 ~ 1.38
   - 城乡混合/标准近郊 (Suburban Mix): c ≈ 1.26 ~ 1.28 (黄金默认值 1.27)
"""

from typing import Tuple

PLAIN_GRID_CITIES = {
    "成都市", "北京市", "西安市", "郑州市", "石家庄市", "太原市", "济南市", 
    "天津市", "长春市", "哈尔滨市", "沈阳市", "合肥市", "南京市", "南昌市", 
    "长沙市", "上海市", "苏州市", "无锡市", "常州市", "徐州市", "南通市",
    "保定市", "唐山市", "邯郸市", "沧州市", "廊坊市", "德州市", "聊城市",
    "临沂市", "菏泽市", "商丘市", "新乡市", "安阳市", "焦作市", "许昌市",
    "大庆市", "鞍山市", "锦州市", "吉林市", "开封市", "洛阳市", "平顶山市"
}

MOUNTAIN_CITIES = {
    "重庆市", "贵阳市", "昆明市", "大连市", "青岛市", "烟台市", "威海市",
    "兰州市", "西宁市", "银川市", "乌鲁木齐市", "延安市", "遵义市", "安顺市",
    "六盘水市", "曲靖市", "玉溪市", "大理白族自治州", "攀枝花市", "绵阳市",
    "宜宾市", "泸州市", "乐山市", "南充市", "达州市", "广元市", "巴中市",
    "承德市", "张家口市", "秦皇岛市", "朔州市", "大同市", "阳泉市", "长治市",
    "呼和浩特市", "包头市", "鄂尔多斯市", "通化市", "延边朝鲜族自治州", "西双版纳傣族自治州"
}

WATER_DELTA_CITIES = {
    "广州市", "深圳市", "佛山市", "东莞市", "中山市", "珠海市", "江门市", 
    "惠州市", "汕头市", "湛江市", "海口市", "三亚市", "福州市", "厦门市", 
    "泉州市", "漳州市", "莆田市", "杭州市", "宁波市", "温州市", "绍兴市", 
    "嘉兴市", "湖州市", "金华市", "台州市", "武汉市", "荆州市", "宜昌市", "襄阳市",
    "岳阳市", "常德市", "九江市", "芜湖市", "马鞍山市", "安庆市", "潮州市", "揭阳市"
}

def get_city_terrain_and_circuity(city_name: str) -> Tuple[str, float]:
    """
    根据城市名称智能返回其地貌类型与经验标定的路网迂回系数。
    返回: (terrain_type, circuity_factor)
    """
    if not city_name:
        return "suburban_mix", 1.27

    for c in PLAIN_GRID_CITIES:
        if c in city_name or city_name in c:
            return "urban_plain_grid", 1.22

    for c in MOUNTAIN_CITIES:
        if c in city_name or city_name in c:
            return "mountainous_rugged", 1.35

    for c in WATER_DELTA_CITIES:
        if c in city_name or city_name in c:
            return "waterway_delta", 1.29

    # 默认城乡近郊混合地貌
    return "suburban_mix", 1.27
