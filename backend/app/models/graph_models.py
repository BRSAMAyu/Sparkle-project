"""
图数据模型定义

定义知识星图的顶点和边模型
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class VertexType(Enum):
    """顶点类型"""
    KNOWLEDGE_NODE = "KnowledgeNode"  # 知识节点
    USER = "User"                      # 用户
    SUBJECT = "Subject"                # 学科/星域
    TASK = "Task"                      # 任务


class EdgeType(Enum):
    """边类型"""
    PREREQUISITE = "PREREQUISITE"      # 前置依赖
    RELATED = "RELATED"                # 相关
    APPLIES_TO = "APPLIES_TO"          # 应用
    COMPOSED_OF = "COMPOSED_OF"        # 组成
    EVOLVES_TO = "EVOLVES_TO"          # 演化
    INTERESTED_IN = "INTERESTED_IN"    # 用户兴趣
    STUDIED = "STUDIED"                # 学习过
    MASTERED = "MASTERED"              # 已掌握


@dataclass
class KnowledgeVertex:
    """知识节点顶点"""
    id: str
    name: str
    description: str
    importance: int = 1
    sector: str = "VOID"
    keywords: List[str] = field(default_factory=list)
    source_type: str = "seed"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "importance": str(self.importance),
            "sector": self.sector,
            "keywords": ",".join(self.keywords),
            "source_type": self.source_type,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class UserVertex:
    """用户顶点"""
    id: str
    username: str
    nickname: str
    flame_level: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "nickname": self.nickname,
            "flame_level": str(self.flame_level),
            "created_at": self.created_at.isoformat()
        }


@dataclass
class SubjectVertex:
    """学科/星域顶点"""
    id: str
    name: str
    sector_code: str
    hex_color: str
    glow_color: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "sector_code": self.sector_code,
            "hex_color": self.hex_color,
            "glow_color": self.glow_color
        }


@dataclass
class RelationEdge:
    """关系边"""
    source_id: str
    target_id: str
    edge_type: EdgeType
    strength: float = 0.5
    created_by: str = "seed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strength": str(self.strength),
            "created_by": self.created_by
        }


@dataclass
class UserInterestEdge:
    """用户兴趣边"""
    user_id: str
    knowledge_id: str
    strength: float = 0.5
    last_accessed: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strength": str(self.strength),
            "last_accessed": self.last_accessed.isoformat()
        }


@dataclass
class StudyRecordEdge:
    """学习记录边"""
    user_id: str
    knowledge_id: str
    study_minutes: int = 0
    mastery_delta: float = 0.0
    last_study: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "study_minutes": str(self.study_minutes),
            "mastery_delta": str(self.mastery_delta),
            "last_study": self.last_study.isoformat()
        }


@dataclass
class GraphQueryResult:
    """图查询结果"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    path: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class GraphSchema:
    """图谱 Schema 管理器"""

    @staticmethod
    def get_vertex_labels() -> List[str]:
        """获取所有顶点标签"""
        return [v.value for v in VertexType]

    @staticmethod
    def get_edge_labels() -> List[str]:
        """获取所有边标签"""
        return [e.value for e in EdgeType]

    @staticmethod
    def get_sector_mapping() -> Dict[str, Dict[str, str]]:
        """6+1 星域映射"""
        return {
            "COSMOS": {
                "name": "理性星域",
                "color": "#00BFFF",
                "glow": "#87CEEB",
                "domains": ["数学", "物理", "化学", "天文", "逻辑学"]
            },
            "TECH": {
                "name": "造物星域",
                "color": "#C0C0C0",
                "glow": "#E8E8E8",
                "domains": ["计算机", "工程", "AI", "建筑", "制造"]
            },
            "ART": {
                "name": "灵感星域",
                "color": "#FF00FF",
                "glow": "#FFB6C1",
                "domains": ["设计", "音乐", "绘画", "文学", "ACG"]
            },
            "CIVILIZATION": {
                "name": "文明星域",
                "color": "#FFD700",
                "glow": "#FFF8DC",
                "domains": ["历史", "经济", "政治", "社会学", "法律"]
            },
            "LIFE": {
                "name": "生活星域",
                "color": "#32CD32",
                "glow": "#90EE90",
                "domains": ["健身", "烹饪", "医学", "心理", "理财"]
            },
            "WISDOM": {
                "name": "智慧星域",
                "color": "#FFFFFF",
                "glow": "#F0F8FF",
                "domains": ["哲学", "宗教", "方法论", "元认知"]
            },
            "VOID": {
                "name": "暗物质区",
                "color": "#2F4F4F",
                "glow": "#696969",
                "domains": ["未归类", "跨领域", "新兴概念"]
            }
        }

    @staticmethod
    def get_edge_descriptions() -> Dict[str, str]:
        """边类型描述"""
        return {
            "PREREQUISITE": "前置依赖 - 学习A需要先掌握B",
            "RELATED": "相关 - 语义或逻辑上相关",
            "APPLIES_TO": "应用 - A应用于B",
            "COMPOSED_OF": "组成 - A由B组成",
            "EVOLVES_TO": "演化 - A演化为B",
            "INTERESTED_IN": "用户兴趣 - 用户对A感兴趣",
            "STUDIED": "学习过 - 用户学习过A",
            "MASTERED": "已掌握 - 用户已掌握A"
        }
