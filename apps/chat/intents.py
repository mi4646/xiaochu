"""意图枚举：路由层用它分发到不同 handler。"""
from enum import Enum


class Intent(str, Enum):
    RECIPE = "recipe"            # 输菜名 → 出菜谱（单/多菜）
    RECOMMEND = "recommend"      # "今晚吃什么" → 推荐菜
    INGREDIENT = "ingredient"    # "冰箱里有 X" → 反查菜
    COOKING_QA = "cooking_qa"    # "怎么做不柴" → 技巧问答
    CHITCHAT = "chitchat"        # 兜底闲聊
