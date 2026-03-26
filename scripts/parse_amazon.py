#!/usr/bin/env python3
"""Amazon 搜索结果解析器"""
import re
from typing import List
from dataclasses import dataclass


@dataclass
class AmazonProduct:
    platform: str = "Amazon"
    platform_icon: str = "🇺🇸"
    title: str = ""
    price_amount: float = 0.0
    price_currency: str = "USD"
    price_display: str = ""
    shipping: str = ""
    rating: float = 0.0
    reviews: int = 0
    url: str = ""
    image: str = ""
    in_stock: bool = True
    seller: str = ""
    original_keyword: str = ""


def parse(html: str, keyword: str, platform_info: dict) -> List[AmazonProduct]:
    products = []
    
    # 提取商品卡片
    # Amazon 商品通常在 .s-result-item 中
    cards = re.findall(
        r'<div[^>]*data-asin="([A-Z0-9]{10})"[^>]*>.*?</div>\s*</div>',
        html, re.DOTALL
    )
    
    # 简化解析：从搜索结果中提取关键信息
    # 匹配价格
    price_pattern = r'\$[\d,]+\.?\d*'
    # 匹配评分
    rating_pattern = r'([\d.]+) out of 5 stars'
    # 匹配评论数
    reviews_pattern = r'([\d,]+) ratings'
    
    # 提取所有商品块
    items = re.findall(
        r'<div[^>]*class="[^"]*s-result-item[^"]*"[^>]*>(.*?)</div>\s*</div>',
        html, re.DOTALL
    )[:10]
    
    for i, item_html in enumerate(items):
        try:
            # 标题
            title_match = re.search(r'<span[^>]*class="[^"]*a-text-normal[^"]*"[^>]*>(.*?)</span>', item_html, re.DOTALL)
            title = re.sub(r'<[^>]+>', '', title_match.group(1) if title_match else '')[:100]
            
            # 价格
            price_match = re.search(price_pattern, item_html)
            price_str = price_match.group() if price_match else "$0"
            price_amount = float(price_str.replace('$', '').replace(',', ''))
            
            # 评分
            rating_match = re.search(rating_pattern, item_html)
            rating = float(rating_match.group(1)) if rating_match else 0.0
            
            # 评论数
            reviews_match = re.search(reviews_pattern, item_html)
            reviews = int(reviews_match.group(1).replace(',', '')) if reviews_match else 0
            
            # URL
            asin_match = re.search(r'data-asin="([A-Z0-9]{10})"', item_html)
            asin = asin_match.group(1) if asin_match else ''
            url = f"https://amazon.com/dp/{asin}" if asin else ""
            
            # Prime 标识
            prime = 'prime' in item_html.lower()
            shipping = "Prime" if prime else "3-5 days"
            
            if title and price_amount > 0:
                products.append(AmazonProduct(
                    title=title,
                    price_amount=price_amount,
                    price_display=price_str,
                    rating=rating,
                    reviews=reviews,
                    url=url,
                    shipping=shipping,
                    original_keyword=keyword
                ))
        except Exception:
            continue
    
    return products


if __name__ == "__main__":
    # 测试用
    import sys
    with open(sys.argv[1] if len(sys.argv) > 1 else 'test.html') as f:
        html = f.read()
    products = parse(html, "test", {"name": "Amazon", "icon": "🇺🇸", "currency": "USD"})
    import json
    print(json.dumps([p.__dict__ for p in products], indent=2))
