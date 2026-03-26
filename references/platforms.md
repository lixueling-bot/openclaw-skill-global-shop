# 平台搜索与解析规范

## 搜索执行流程

1. `search.py` 接收关键词（keyword）参数
2. 构建各平台搜索 URL（URLEncode 处理）
3. 使用 `web_fetch` 并发获取各平台搜索结果页
4. 调用对应平台的 `parse_*.py` 解析 HTML
5. 汇总所有结果，调用 `rank.py` 排序
6. 返回标准化商品列表

## 标准化商品数据格式

```json
{
  "platform": "Amazon",
  "platform_icon": "🇺🇸",
  "title": "Apple AirPods Pro (2nd Generation)",
  "price": {
    "amount": 199.99,
    "currency": "USD",
    "display": "$199.99"
  },
  "shipping": "3-5 business days",
  "rating": 4.7,
  "reviews": 23456,
  "sales_count": "2.3k",
  "url": "https://amazon.com/dp/B0BDHWDR12",
  "image": "https://m.media-amazon.com/images/I/...",
  "in_stock": true,
  "prime": true,
  "seller": "Apple Store",
  "original_keyword": "airpods pro"
}
```

## 各平台解析规则

### Amazon (parse_amazon.py)

- 搜索页：`s?k={keyword}&s=review_rank`
- 解析字段：`.s-main-slot .s-result-item`
- 价格正则：`\$[\d,]+\.?\d*`
- 评分：`.a-icon-star .a-icon-alt`
- 评论数：`[\d,]+ reviews`

### eBay (parse_ebay.py)

- 搜索页：`/sch/i.html?_nkw={keyword}&_sop=12`
- 解析字段：`.s-item`
- 价格：`.s-item__price`
- 评分：`.b-starrating`

### AliExpress (parse_aliexpress.py)

- 搜索页：`/wholesale?SearchText={keyword}&SortType=total_tranpro_desc`
- 解析字段：`.search-item`
- 价格：`.price`
- 评分：`.evaluation`

### 天猫国际 (parse_tmall.py)

- 搜索页：`/search?q={keyword}`
- 解析字段：`.product`
- 价格：`.price`
- 评分：`.tmall-flagship .productPrice`

### 京东全球购 (parse_jd.py)

- 搜索页：`/search?keyword={keyword}&click=1`
- 解析字段：`.gl-item`
- 价格：`.p-price`
- 评分：`.p-score`

## 搜索结果字段要求

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| platform | string | ✅ | 平台名称 |
| title | string | ✅ | 商品标题 |
| price | object | ✅ | 价格对象 |
| url | string | ✅ | 商品链接 |
| rating | float | ✅ | 评分 0-5 |
| shipping | string | ❌ | 配送时间 |
| reviews | int | ❌ | 评论数 |
| in_stock | bool | ✅ | 是否现货 |

## 错误处理

- 单个平台解析失败不影响其他平台
- 解析失败记录到日志，返回可用结果
- 所有平台都失败时返回空列表并提示用户
