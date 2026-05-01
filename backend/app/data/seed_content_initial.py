"""
Seed Content Initial Data
种子内容库初始数据 - 预设官方库和内容

包含三个官方库：
1. 数学基础示例库 (few_shot) - 一元二次方程求解、几何证明示例
2. 常见问题回复模板 (template) - 如何开始学习、功能介绍
3. Python编程练习题库 (teaching) - 列表操作、函数定义练习
"""
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert

from app.models.seed_content import (
    DifficultyLevel,
    ItemType,
    LibraryCategory,
    LibraryVisibility,
    SeedItem,
    SeedLibrary,
)

# 官方库定义
OFFICIAL_LIBRARIES: list[dict[str, Any]] = [
    {
        "name": "数学基础示例库",
        "description": "数学问题求解的标准示例，用于 AI 辅助教学",
        "category": LibraryCategory.FEW_SHOT,
        "visibility": LibraryVisibility.OFFICIAL,
        "language": "zh",
        "tags": ["数学", "代数", "几何", "few-shot"],
        "is_official": True,
        "is_featured": True,
        "quality_score": 9.0,
        "items": [
            {
                "item_type": ItemType.EXAMPLE,
                "title": "一元二次方程求解示例",
                "subject": "数学",
                "difficulty_level": DifficultyLevel.BEGINNER,
                "tags": ["代数", "方程", "求解"],
                "order_index": 1,
                "content_data": {
                    "input": "求解方程：x² - 5x + 6 = 0",
                    "output": """# 解题步骤

**第一步：识别方程类型**
这是一元二次方程，标准形式为 ax² + bx + c = 0
这里 a=1, b=-5, c=6

**第二步：选择求解方法**
可以使用因式分解法：
x² - 5x + 6 = 0
寻找两个数，乘积为6，和为-5
这两个数是-2和-3

**第三步：因式分解**
(x - 2)(x - 3) = 0

**第四步：求解**
x - 2 = 0 → x₁ = 2
x - 3 = 0 → x₂ = 3

**答案：** x₁ = 2，x₂ = 3""",
                    "explanation": "这是一个使用因式分解法求解一元二次方程的标准示例。展示了完整的解题思路和步骤。",
                },
            },
            {
                "item_type": ItemType.EXAMPLE,
                "title": "几何证明示例 - 三角形内角和",
                "subject": "数学",
                "difficulty_level": DifficultyLevel.INTERMEDIATE,
                "tags": ["几何", "证明", "三角形"],
                "order_index": 2,
                "content_data": {
                    "input": "证明：任意三角形的内角和等于180°",
                    "output": """# 证明过程

**已知：** 任意三角形 ABC

**求证：** ∠A + ∠B + ∠C = 180°

**证明：**

1. 过顶点 C 作 AB 的平行线，与 AC、BC 的延长线相交

2. 根据平行线性质：
   - 内错角相等：∠1 = ∠A
   - 同位角相等：∠2 = ∠B

3. 平角等于180°：
   ∠1 + ∠C + ∠2 = 180°

4. 代换得：
   ∠A + ∠C + ∠B = 180°

**结论：** 三角形的内角和等于180° ∎""",
                    "explanation": "使用辅助线和平行线性质证明三角形内角和定理，展示了几何证明的标准格式。",
                },
            },
            {
                "item_type": ItemType.EXAMPLE,
                "title": "函数图像分析示例",
                "subject": "数学",
                "difficulty_level": DifficultyLevel.INTERMEDIATE,
                "tags": ["函数", "图像", "分析"],
                "order_index": 3,
                "content_data": {
                    "input": "分析函数 f(x) = x² - 4x + 3 的图像性质",
                    "output": """# 函数分析

**函数类型：** 二次函数（抛物线）

**1. 开口方向**
二次项系数为 1 > 0，开口向上

**2. 顶点坐标**
使用公式：x = -b/(2a) = -(-4)/(2×1) = 2
y = f(2) = 2² - 4×2 + 3 = 4 - 8 + 3 = -1
顶点为 (2, -1)

**3. 对称轴**
x = 2

**4. 与坐标轴交点**
- 与 y 轴交点：(0, 3)
- 与 x 轴交点：x² - 4x + 3 = 0
  (x-1)(x-3) = 0
  x₁ = 1, x₂ = 3
  交点为 (1, 0) 和 (3, 0)

**5. 单调性**
- (-∞, 2)：单调递减
- (2, +∞)：单调递增

**6. 值域**
y ≥ -1，即 [-1, +∞)""",
                    "explanation": "系统地分析二次函数的各项性质，包括开口、顶点、交点等关键特征。",
                },
            },
        ],
    },
    {
        "name": "常见问题回复模板",
        "description": "系统常见问题的标准回复模板",
        "category": LibraryCategory.REPLY_TEMPLATE,
        "visibility": LibraryVisibility.OFFICIAL,
        "language": "zh",
        "tags": ["faq", "模板", "回复"],
        "is_official": True,
        "is_featured": True,
        "quality_score": 8.5,
        "items": [
            {
                "item_type": ItemType.TEMPLATE,
                "title": "如何开始学习",
                "subject": "系统使用",
                "tags": ["getting_started", "onboarding"],
                "order_index": 1,
                "content": """欢迎来到星火 AI 学习助手！🎓

**快速开始指南**

1. **选择学科** - 在主页选择你想学习的学科（数学、物理、编程等）

2. **开始对话** - 直接向我提问，我会根据你的水平提供个性化的解答

3. **使用工具** - 我可以帮你：
   - 📝 解答题目和知识点
   - 📊 分析学习数据
   - 🎯 制定学习计划
   - 📚 推荐学习资源

**小贴士**
- 描述问题时尽量详细，我会更好地理解你的需求
- 不要害羞，多问问题是最好的学习方式
- 可以随时请求我放慢速度或换种方式解释

现在，你有什么想了解的吗？""",
            },
            {
                "item_type": ItemType.TEMPLATE,
                "title": "功能介绍",
                "subject": "系统使用",
                "tags": ["features", "introduction"],
                "order_index": 2,
                "content": """**星火 AI 学习助手功能介绍** ✨

🔍 **智能问答**
- 支持数学、物理、编程等多学科问题
- 逐步推导，让你理解每个步骤

📊 **学习分析**
- 追踪你的学习进度
- 识别薄弱环节，针对性练习

🎯 **个性化计划**
- 根据你的水平定制学习路径
- 智能推荐练习题和学习资源

💡 **多种学习模式**
- 自由问答模式
- 结构化课程模式
- 专项练习模式

📝 **学习记录**
- 自动保存学习历史
- 支持复习和回顾

有什么具体想了解的功能吗？""",
            },
            {
                "item_type": ItemType.TEMPLATE,
                "title": "学习建议提示",
                "subject": "学习方法",
                "tags": ["study_tips", "guidance"],
                "order_index": 3,
                "content": """**给学习者的建议** 💡

1. **循序渐进**
   不要急于求成，扎实的基础是进步的关键

2. **主动提问**
   不懂就问，每个问题都是学习的机会

3. **及时复习**
   利用间隔重复巩固记忆效果

4. **联系实际**
   尝试将学到的知识应用到实际问题中

5. **保持耐心**
   学习是一个过程，享受每一点进步

6. **多样化学习**
   结合不同方式学习：阅读、练习、讨论

需要针对某个学科的具体建议吗？""",
            },
        ],
    },
    {
        "name": "Python编程练习题库",
        "description": "Python编程练习题和示例，涵盖基础到进阶",
        "category": LibraryCategory.TEACHING_CONTENT,
        "visibility": LibraryVisibility.OFFICIAL,
        "language": "zh",
        "tags": ["编程", "Python", "练习", "代码"],
        "is_official": True,
        "is_featured": False,
        "quality_score": 8.8,
        "items": [
            {
                "item_type": ItemType.EXERCISE,
                "title": "列表操作基础练习",
                "subject": "编程",
                "difficulty_level": DifficultyLevel.BEGINNER,
                "tags": ["Python", "列表", "基础"],
                "order_index": 1,
                "content": """# 列表操作基础练习

**题目：** 给定一个数字列表 [3, 1, 4, 1, 5, 9, 2, 6]
1. 计算列表中所有数字的和
2. 找出列表中的最大值
3. 去除重复元素""",
                "content_data": {
                    "solution": """# 解答

```python
numbers = [3, 1, 4, 1, 5, 9, 2, 6]

# 1. 计算和
total = sum(numbers)
print(f"总和: {total}")  # 输出: 总和: 31

# 2. 找最大值
maximum = max(numbers)
print(f"最大值: {maximum}")  # 输出: 最大值: 9

# 3. 去除重复
unique = list(set(numbers))
print(f"去重后: {unique}")  # 输出: 去重后: [1, 2, 3, 4, 5, 6, 9]
```""",
                    "explanation": "- sum() 函数计算列表元素总和\n- max() 函数找出最大值\n- set() 去重后再转回 list",
                },
            },
            {
                "item_type": ItemType.EXERCISE,
                "title": "函数定义练习 - 阶乘计算",
                "subject": "编程",
                "difficulty_level": DifficultyLevel.INTERMEDIATE,
                "tags": ["Python", "函数", "递归"],
                "order_index": 2,
                "content": """# 函数定义练习

**题目：** 编写一个函数 factorial(n)，计算 n 的阶乘

要求：
1. 使用递归方式实现
2. 添加输入验证
3. 处理边界情况""",
                "content_data": {
                    "solution": '''# 解答

```python
def factorial(n):
    """
    计算 n 的阶乘

    Args:
        n: 非负整数

    Returns:
        n 的阶乘

    Raises:
        ValueError: 当 n 为负数时
    """
    # 输入验证
    if not isinstance(n, int) or n < 0:
        raise ValueError("阶乘只能计算非负整数")

    # 基础情况
    if n == 0 or n == 1:
        return 1

    # 递归情况
    return n * factorial(n - 1)

# 测试
print(factorial(5))  # 输出: 120
print(factorial(0))  # 输出: 1
```''',
                    "explanation": "递归的关键是：1) 基础情况（n=0或1时返回1）2) 递归调用（n * factorial(n-1)）",
                },
            },
            {
                "item_type": ItemType.KNOWLEDGE,
                "title": "Python 字典操作要点",
                "subject": "编程",
                "difficulty_level": DifficultyLevel.BEGINNER,
                "tags": ["Python", "字典", "知识点"],
                "order_index": 3,
                "content": """# Python 字典操作要点

## 创建字典
```python
# 空字典
d1 = {}
d2 = dict()

# 带初始值
d3 = {'name': 'Alice', 'age': 25}
```

## 访问元素
```python
# 使用键访问
value = d3['name']  # 'Alice'

# 使用 get() 方法（安全）
value = d3.get('name', 'Unknown')  # 键不存在时返回默认值
```

## 添加/修改元素
```python
d3['city'] = 'Beijing'  # 添加
d3['age'] = 26  # 修改
```

## 删除元素
```python
# 删除指定键
del d3['age']

# 弹出并返回值
city = d3.pop('city')
```

## 常用方法
- `keys()` - 所有键
- `values()` - 所有值
- `items()` - 所有键值对
- `update()` - 合并字典""",
            },
            {
                "item_type": ItemType.FLASHCARD,
                "title": "Python 列表推导式闪卡",
                "subject": "编程",
                "difficulty_level": DifficultyLevel.INTERMEDIATE,
                "tags": ["Python", "列表推导式", "闪卡"],
                "order_index": 4,
                "content_data": {
                    "front": """**问题：** 如何用列表推导式将 [1, 2, 3, 4, 5] 中每个数字平方？""",
                    "back": """**答案：**
```python
numbers = [1, 2, 3, 4, 5]
squared = [x**2 for x in numbers]
# 结果: [1, 4, 9, 16, 25]
```

**带条件的列表推导式：**
```python
# 只保留偶数的平方
even_squared = [x**2 for x in numbers if x % 2 == 0]
# 结果: [4, 16]
```""",
                },
            },
        ],
    },
]


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def initialize_seed_libraries(db_session) -> int:
    """
    初始化种子内容库数据

    Args:
        db_session: SQLAlchemy 异步会话

    Returns:
        创建的内容项数量
    """
    from sqlalchemy import select

    # 检查是否已初始化
    existing = await db_session.execute(
        select(SeedLibrary).where(SeedLibrary.is_official)
    )
    if existing.scalars().first():
        logger = __import__("loguru").logger
        logger.info("Seed libraries already initialized")
        return 0

    logger = __import__("loguru").logger
    item_count = 0

    for lib_data in OFFICIAL_LIBRARIES:
        # 提取 items 数据 (使用 get 避免修改原数据)
        items_data = lib_data.get("items", [])
        # 创建库的副本，避免修改全局常量
        lib_attrs = {k: v for k, v in lib_data.items() if k != "items"}

        # 创建库
        library = SeedLibrary(**lib_attrs)
        db_session.add(library)
        await db_session.flush()

        # 创建内容项
        for item_data in items_data:
            normalized_item_data = dict(item_data)
            normalized_item_data["library_id"] = library.id
            # 处理枚举类型
            if "item_type" in normalized_item_data:
                normalized_item_data["item_type"] = normalized_item_data["item_type"].value
            if "difficulty_level" in normalized_item_data and normalized_item_data["difficulty_level"]:
                normalized_item_data["difficulty_level"] = normalized_item_data["difficulty_level"].value

            item = SeedItem(**normalized_item_data)
            await db_session.execute(
                insert(SeedItem.__table__).values(
                    id=item.id or uuid.uuid4(),
                    library_id=item.library_id,
                    item_type=item.item_type,
                    title=item.title,
                    content=item.content,
                    content_data=item.content_data,
                    subject=item.subject,
                    difficulty_level=item.difficulty_level,
                    tags=item.tags,
                    order_index=item.order_index or 0,
                    is_active=True if item.is_active is None else item.is_active,
                    created_at=item.created_at or _utcnow(),
                    updated_at=item.updated_at or _utcnow(),
                    deleted_at=item.deleted_at,
                )
            )
            item_count += 1

        logger.info(f"Created official library: {library.name} with {len(items_data)} items")

    await db_session.commit()
    logger.info(f"Seed libraries initialized: {item_count} items created")

    return item_count


if __name__ == "__main__":
    # 用于手动初始化
    import asyncio

    from app.db.session import get_db

    async def main():
        async for db in get_db():
            await initialize_seed_libraries(db)
            break

    asyncio.run(main())
