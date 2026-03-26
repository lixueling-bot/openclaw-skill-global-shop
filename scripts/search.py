#!/usr/bin/env python3
"""
Global Shop - 并发搜索全球电商平台
用法: python3 search.py <关键词> [--count 数量]
"""

import asyncio
import json
import re
import sys
import urllib.parse
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

try:
    import httpx
except ImportError:
    print("安装依赖: pip3 install httpx")
    sys.exit(1)


@dataclass
class Product:
    platform: str
    platform_icon: str
    title: str
    price_amount: float
    price_currency: str
    price_display: str
    shipping: str
    rating: float
    reviews: int
    url: str
    image: str
    in_stock: bool
    seller: str
    original_keyword: str


PLATFORMS = {
    "amazon": {
        "name": "Amazon",
        "icon": "🇺🇸",
        "search_url": "https://www.amazon.com/s?k={keyword}&s=review_rank",
        "currency": "USD",
    },
    "ebay": {
        "name": "eBay",
        "icon": "🇺🇸",
        "search_url": "https://www.ebay.com/sch/i.html?_nkw={keyword}&_sop=12",
        "currency": "USD",
    },
    "aliexpress": {
        "name": "AliExpress",
        "icon": "🌐",
        "search_url": "https://www.aliexpress.com/wholesale?SearchText={keyword}&SortType=total_tranpro_desc",
        "currency": "USD",
    },
    "tmall": {
        "name": "天猫国际",
        "icon": "🇨🇳",
        "search_url": "https://list.tmall.com/search_product.htm?q={keyword}",
        "currency": "CNY",
    },
    "jd": {
        "name": "京东全球购",
        "icon": "🇨🇳",
        "search_url": "https://search.jd.com/Search?keyword={keyword}&click=1",
        "currency": "CNY",
    },
}


async def search_platform(client: httpx.AsyncClient, platform_key: str, keyword: str) -> List[Product]:
    """并发搜索单个平台"""
    platform = PLATFORMS[platform_key]
    url = platform["search_url"].format(keyword=urllib.parse.quote(keyword))
    
    try:
        response = await client.get(url, timeout=15.0, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        response.raise_for_status()
        
        # 调用对应平台的解析器
        parser = getattr(__import__('parse_' + platform_key, fromlist=['']), 'parse')
        return parser(response.text, keyword, platform)
    except Exception as e:
        print(f"⚠️ {platform['name']} 搜索失败: {e}", file=sys.stderr)
        return []


async def search_all(keyword: str, max_results_per_platform: int = 5) -> List[Product]:
    """并发搜索所有平台"""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [
            search_platform(client, platform_key, keyword)
            for platform_key in PLATFORMS.keys()
        ]
        results = await asyncio.gather(*tasks)
        
    # 合并所有结果
    all_products = []
    for platform_results in results:
        all_products.extend(platform_results[:max_results_per_platform])
    
    # 按综合评分排序
    all_products.sort(key=lambda p: (-p.rating, p.price_amount))
    
    return all_products


def format_results(products: List[Product], keyword: str) -> str:
    """格式化输出结果"""
    if not products:
        return f"❌ 未找到「{keyword}」的相关商品"
    
    lines = [
        f"🛍️ 全球最优选项 — **{keyword}**\n",
        "| # | 平台 | 价格 | 配送 | 评分 | 评论数 |",
        "|---|------|------|------|------|--------|"
    ]
    
    option_letters = list("ABCDEFGHIJ")
    
    for i, product in enumerate(products[:5]):
        letter = option_letters[i]
        lines.append(
            f"| [{letter}] | {product.platform_icon} {product.platform} | "
            f"{product.price_display} | {product.shipping} | "
            f"⭐{product.rating} | {product.reviews:,} |"
        )
    
    # 推荐首选
    if products:
        best = products[0]
        lines.append(f"\n💡 **推荐首选**：{best.platform_icon} {best.platform} — {best.price_display}")
        if best.shipping:
            lines.append(f"   └─ 配送：{best.shipping} | 评分：⭐{best.rating} | 评论：{best.reviews:,}")
    
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 search.py <关键词> [--count 数量]")
        sys.exit(1)
    
    keyword = sys.argv[1]
    count = 5
    if "--count" in sys.argv:
        idx = sys.argv.index("--count")
        if idx + 1 < len(sys.argv):
            count = int(sys.argv[idx + 1])
    
    print(f"🔍 正在搜索全球平台：「{keyword}」...", file=sys.stderr)
    
    products = asyncio.run(search_all(keyword, count))
    output = format_results(products, keyword)
    
    print(output)
    
    # 同时输出 JSON 格式供程序调用
    if products:
        print("\n<!--JSON_OUTPUT-->", file=sys.stderr)
        print(json.dumps([asdict(p) for p in products], ensure_ascii=False, indent=2), file=sys.stderr)


if __name__ == "__main__":
    main()
