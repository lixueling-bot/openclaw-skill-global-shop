#!/usr/bin/env python3
"""平台账户加密存储与管理"""
import os
import json
from pathlib import Path
from typing import List, Optional

ACCOUNT_FILE = Path.home() / ".qclaw" / "global-shop" / "accounts.json"


def get_storage_dir() -> Path:
    """确保存储目录存在"""
    storage_dir = Path.home() / ".qclaw" / "global-shop"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def load_accounts() -> dict:
    """加载已存账户"""
    account_file = get_storage_dir() / "accounts.json"
    if not account_file.exists():
        return {"accounts": []}
    try:
        with open(account_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"accounts": []}


def save_accounts(data: dict) -> None:
    """保存账户数据（简化版：实际应加密存储）"""
    account_file = get_storage_dir() / "accounts.json"
    with open(account_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_account(platform: str, email: str, country: str = "US") -> dict:
    """添加平台账户"""
    accounts_data = load_accounts()
    
    account_id = f"acc_{len(accounts_data['accounts']) + 1:03d}"
    new_account = {
        "id": account_id,
        "platform": platform.lower(),
        "email": email,
        "country": country,
        "added_at": __import__('datetime').datetime.now().isoformat() + "Z"
    }
    
    accounts_data["accounts"].append(new_account)
    save_accounts(accounts_data)
    
    return new_account


def list_accounts(platform: Optional[str] = None) -> List[dict]:
    """列出账户"""
    accounts_data = load_accounts()
    accounts = accounts_data["accounts"]
    
    if platform:
        accounts = [a for a in accounts if a["platform"] == platform.lower()]
    
    return [
        {
            "id": a["id"],
            "platform": a["platform"],
            "email": a["email"],
            "country": a.get("country", ""),
        }
        for a in accounts
    ]


def remove_account(account_id: str) -> bool:
    """删除指定账户"""
    accounts_data = load_accounts()
    original_len = len(accounts_data["accounts"])
    accounts_data["accounts"] = [a for a in accounts_data["accounts"] if a["id"] != account_id]
    
    if len(accounts_data["accounts"]) < original_len:
        save_accounts(accounts_data)
        return True
    return False


def clear_all_accounts() -> None:
    """清除所有已存账户"""
    account_file = get_storage_dir() / "accounts.json"
    if account_file.exists():
        account_file.unlink()


def format_account_list(accounts: List[dict]) -> str:
    """格式化账户列表显示"""
    if not accounts:
        return "🔐 尚未保存任何平台账户\n\n使用「添加平台账户」来保存登录信息"
    
    lines = ["🔐 **已保存的平台账户**\n"]
    
    # 按平台分组
    platforms = {}
    for acc in accounts:
        p = acc["platform"]
        if p not in platforms:
            platforms[p] = []
        platforms[p].append(acc)
    
    for platform, accs in platforms.items():
        platform_emoji = {
            "amazon": "📦", "ebay": "🛒", "aliexpress": "🌐",
            "tmall": "🏮", "jd": "📱", "taobao": "🛍️"
        }.get(platform, "🌐")
        
        lines.append(f"{platform_emoji} **{platform.upper()}**")
        for acc in accs:
            lines.append(f"   └─ {acc['email']}")
        lines.append("")
    
    return "\n".join(lines).strip()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python3 accounts.py <add|list|remove|clear> [参数]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "add":
        if len(sys.argv) < 4:
            print("用法: python3 accounts.py add <平台> <邮箱> [国家]")
            sys.exit(1)
        account = add_account(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "US")
        print(f"✅ 已添加 {account['platform']}: {account['email']}")
    
    elif cmd == "list":
        accounts = list_accounts()
        print(format_account_list(accounts))
    
    elif cmd == "remove":
        if len(sys.argv) < 3:
            print("用法: python3 accounts.py remove <账户ID>")
            sys.exit(1)
        if remove_account(sys.argv[2]):
            print("✅ 已删除")
        else:
            print("❌ 未找到该账户")
    
    elif cmd == "clear":
        clear_all_accounts()
        print("✅ 已清除所有已存账户")
