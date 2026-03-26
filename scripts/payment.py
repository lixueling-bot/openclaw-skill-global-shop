#!/usr/bin/env python3
"""支付卡加密存储与管理"""
import os
import json
import base64
import hashlib
from pathlib import Path
from typing import List, Optional

CARD_FILE = Path.home() / ".qclaw" / "global-shop" / "cards.json"


def get_storage_dir() -> Path:
    """确保存储目录存在"""
    storage_dir = Path.home() / ".qclaw" / "global-shop"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def load_cards() -> dict:
    """加载已存卡"""
    card_file = get_storage_dir() / "cards.json"
    if not card_file.exists():
        return {"cards": []}
    try:
        with open(card_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"cards": []}


def save_cards(data: dict) -> None:
    """保存卡数据（简化版：实际应加密存储）"""
    card_file = get_storage_dir() / "cards.json"
    with open(card_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_card(nickname: str, last4: str, brand: str, expiry: str, cardholder: str) -> dict:
    """添加新卡"""
    cards_data = load_cards()
    
    card_id = f"card_{len(cards_data['cards']) + 1:03d}"
    new_card = {
        "id": card_id,
        "nickname": nickname,
        "last4": last4,
        "brand": brand.lower(),
        "expiry": expiry,
        "cardholder": cardholder,
        "added_at": __import__('datetime').datetime.now().isoformat() + "Z"
    }
    
    cards_data["cards"].append(new_card)
    save_cards(cards_data)
    
    return new_card


def list_cards() -> List[dict]:
    """列出所有已存卡"""
    cards_data = load_cards()
    return [
        {
            "id": c["id"],
            "nickname": c.get("nickname", f"{c['brand']} ****{c['last4']}"),
            "brand": c["brand"],
            "last4": c["last4"],
            "expiry": c.get("expiry", ""),
            "cardholder": c.get("cardholder", ""),
        }
        for c in cards_data["cards"]
    ]


def remove_card(card_id: str) -> bool:
    """删除指定卡"""
    cards_data = load_cards()
    original_len = len(cards_data["cards"])
    cards_data["cards"] = [c for c in cards_data["cards"] if c["id"] != card_id]
    
    if len(cards_data["cards"]) < original_len:
        save_cards(cards_data)
        return True
    return False


def clear_all_cards() -> None:
    """清除所有已存卡"""
    card_file = get_storage_dir() / "cards.json"
    if card_file.exists():
        card_file.unlink()


def format_card_list(cards: List[dict]) -> str:
    """格式化卡列表显示"""
    if not cards:
        return "💳 尚未保存任何信用卡\n\n使用「添加信用卡」来保存您的支付方式"
    
    lines = ["💳 **已保存的信用卡**\n"]
    for i, card in enumerate(cards, 1):
        brand_emoji = {"visa": "💳", "mastercard": "💳", "amex": "💳", "discover": "💳"}.get(card["brand"], "💳")
        lines.append(f"{i}. {brand_emoji} {card['nickname']}")
        lines.append(f"   └─ {card['brand'].upper()} **** {card['last4']} (到期: {card.get('expiry', 'N/A')})")
    
    lines.append("\n💡 说「删除信用卡 [序号]」可移除已存卡")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python3 payment.py <add|list|remove|clear> [参数]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "add":
        if len(sys.argv) < 7:
            print("用法: python3 payment.py add <昵称> <末4位> <品牌> <到期> <持卡人>")
            sys.exit(1)
        card = add_card(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
        print(f"✅ 已添加: {card['brand'].upper()} **** {card['last4']}")
    
    elif cmd == "list":
        cards = list_cards()
        print(format_card_list(cards))
    
    elif cmd == "remove":
        if len(sys.argv) < 3:
            print("用法: python3 payment.py remove <卡ID>")
            sys.exit(1)
        if remove_card(sys.argv[2]):
            print("✅ 已删除")
        else:
            print("❌ 未找到该卡")
    
    elif cmd == "clear":
        clear_all_cards()
        print("✅ 已清除所有已存信用卡")
