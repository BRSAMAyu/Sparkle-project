#!/usr/bin/env python3
"""
批量翻译 app_zh.arb 中所有剩余的未翻译英文字符串
"""

import json
import re

# 翻译映射表 - 完整的英中翻译
TRANSLATIONS = {
    # 社区相关
    "communityNoNewNotifications": "暂无新通知",
    "communityNoPendingRequests": "暂无待处理请求",
    "communityWantsToBeYourFriend": "想和你成为好友",
    "communityNoRecommendationsAvailable": "暂无推荐",
    "communityRequestSent": "请求已发送",
    "communitySendFriendRequest": "发送好友请求",
    "communitySendMessage": "发送消息",
    "communityNewPost": "发布动态",
    "communityCreateGroup": "创建群组",
    "communityMyCommunity": "我的社群",
    "communityDiscoverGroups": "发现群组",
    "communityDemoteToMember": "降为成员",
    "communityPromoteToAdmin": "升为管理员",
    "communityEditAnnouncement": "编辑公告",
    "communityUnknownType": "未知类型",
    "communityTranslationDemo": "翻译演示",

    # 计划相关
    "planGrowthPlans": "成长计划",
    "planNewPlan": "新建计划",
    "planMySprint": "我的冲刺",

    # 通知相关
    "notificationNoNew": "暂无新通知",

    # 其他
    "unknownType": "未知类型",
    "translationDemo": "翻译演示",
}

def is_english_only(text):
    """检查文本是否只包含英文和基本符号"""
    # 排除已包含中文的文本
    if re.search(r'[\u4e00-\u9fff]', text):
        return False
    # 检查是否主要是英文
    if re.match(r'^[A-Za-z0-9\s\.\,\!\?\:\;\-\+\(\)\[\]\'\"]+$', text):
        return True
    return False

def needs_translation(key, value):
    """判断键值对是否需要翻译"""
    # 跳过元数据字段
    if key.startswith('@'):
        return False
    if not isinstance(value, str):
        return False
    # 检查值是否是英文
    if not is_english_only(value):
        return False
    # 排除一些特殊值
    if value in ['Google', 'Apple', 'Sparkle', 'Ocean', 'Forest', 'English',
                 'WebSocket', 'PostgreSQL', 'pgvector', 'Flutter', 'Python',
                 'GraphRAG', 'Sprint', 'Growth Plan', 'Legacy', 'Token',
                 'Prompt Tokens', 'Completion Tokens', 'Diff', 'AI', 'Lv.',
                 'Qwen3', 'Go Gateway', 'Python Agent Engine']:
        return False
    return True

def translate_file():
    """翻译文件中的英文字符串"""
    input_file = '/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/l10n/app_zh.arb'

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 找出需要翻译的键
    to_translate = {}
    for key, value in data.items():
        if needs_translation(key, value):
            to_translate[key] = value

    print(f"发现 {len(to_translate)} 个需要翻译的字符串")

    # 使用映射表翻译
    translated_count = 0
    for key, original_value in to_translate.items():
        if key in TRANSLATIONS:
            data[key] = TRANSLATIONS[key]
            translated_count += 1
            print(f"✅ {key}: '{original_value}' -> '{TRANSLATIONS[key]}'")
        else:
            # 尝试智能翻译
            # 将 CamelCase 转换为空格分隔的单词
            words = re.findall(r'[A-Z][a-z]+|[A-Z]+(?=[A-Z]|$)', key)
            if words:
                # 生成占位符翻译（使用中文提示）
                placeholder = f"[待翻译: {' '.join(words)}]"
                print(f"⚠️  {key}: '{original_value}' -> 需要手动翻译")

    # 写回文件
    with open(input_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 翻译完成！共翻译了 {translated_count} 个字符串")

if __name__ == '__main__':
    translate_file()
