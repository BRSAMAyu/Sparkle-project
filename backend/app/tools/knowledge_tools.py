from typing import Any, Optional
from uuid import UUID
from .base import BaseTool, ToolCategory, ToolResult
from .schemas import CreateKnowledgeNodeParams, LinkNodesParams, QueryKnowledgeParams
from app.services.galaxy_service import GalaxyService

class CreateKnowledgeNodeTool(BaseTool):
    """创建知识节点（生成学习卡片的基础）"""
    name = "create_knowledge_node"
    description = """在知识星图中创建一个新的知识节点/学习卡片。
    当用户想要记录或整理知识点时使用，例如：
    - "把刚才聊的 Rust 所有权整理成卡片"
    - "帮我创建一个关于傅里叶变换的知识点"
    - "记录这个概念到我的知识库"
    """
    category = ToolCategory.KNOWLEDGE
    parameters_schema = CreateKnowledgeNodeParams
    requires_confirmation = False
    
    async def execute(
        self, 
        params: CreateKnowledgeNodeParams, 
        user_id: str,
        db_session: Any,
        tool_call_id: Optional[str] = None
    ) -> ToolResult:
        try:
            galaxy_service = GalaxyService(db_session)
            
            # 1. [止血方案] 语义查重：避免创建重复的知识点
            existing_nodes = await galaxy_service.semantic_search_nodes(
                query=params.title,
                limit=1,
                threshold=0.15 # 严格阈值，Cosine Distance < 0.15 表示高度相似
            )
            
            if existing_nodes:
                node = existing_nodes[0]
                return ToolResult(
                    success=True, # 返回成功，但告知用户已关联
                    tool_name=self.name,
                    data={"node_id": str(node.id), "is_duplicate": True},
                    widget_type="knowledge_card",
                    widget_data={
                        "id": str(node.id),
                        "title": node.name,
                        "summary": node.description,
                        "tags": node.keywords,
                        "is_existing": True,
                        "message": "相似知识点已存在，已为您关联。"
                    }
                )

            # 2. 如果无重复，继续创建
            # Handle subject_id conversion (str -> int if possible)
            subject_id_int = None
            if params.subject_id:
                try:
                    subject_id_int = int(params.subject_id)
                except ValueError:
                    # If subject_id is a name, we might ignore it or try to find it.
                    # For now, ignore if not int
                    pass
            
            parent_node_uuid = None
            if params.parent_node_id:
                try:
                    parent_node_uuid = UUID(params.parent_node_id)
                except ValueError:
                    pass

            node = await galaxy_service.create_node(
                user_id=UUID(user_id),
                title=params.title,
                summary=params.summary,
                subject_id=subject_id_int,
                tags=params.tags,
                parent_node_id=parent_node_uuid
            )
            
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"node_id": str(node.id)},
                widget_type="knowledge_card",
                widget_data={
                    "id": str(node.id),
                    "title": node.name,
                    "summary": node.description,
                    "tags": node.keywords,
                    "mastery_level": 0, # Initial mastery
                    "created_at": datetime.utcnow().isoformat() if not hasattr(node, 'created_at') else node.created_at.isoformat()
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="创建知识节点失败，请检查参数"
            )

from datetime import datetime

class QueryKnowledgeTool(BaseTool):
    """查询知识图谱（LLM 先看再动）"""
    name = "query_knowledge"
    description = """搜索用户的知识图谱，查找已有的知识点。
    在创建新知识点之前，先调用此工具检查是否已存在相关内容。
    也可用于回答用户关于已学内容的问题。
    """
    category = ToolCategory.QUERY
    parameters_schema = QueryKnowledgeParams
    requires_confirmation = False
    
    async def execute(
        self, 
        params: QueryKnowledgeParams, 
        user_id: str,
        db_session: Any,
        tool_call_id: Optional[str] = None
    ) -> ToolResult:
        try:
            galaxy_service = GalaxyService(db_session)
            
            subject_id_int = None
            if params.subject_id:
                try:
                    subject_id_int = int(params.subject_id)
                except ValueError:
                    pass

            if params.use_vector_search:
                nodes = await galaxy_service.semantic_search(
                    user_id=UUID(user_id),
                    query=params.query,
                    subject_id=subject_id_int,
                    limit=params.limit
                )
                # nodes are SearchResultItem
                result_nodes = [
                    {
                        "id": str(item.node.id),
                        "title": item.node.name,
                        "summary": item.node.description[:200] if item.node.description else "",
                        "mastery_level": item.user_status.mastery_score if item.user_status else 0
                    }
                    for item in nodes
                ]
            else:
                nodes = await galaxy_service.keyword_search(
                    user_id=UUID(user_id),
                    query=params.query,
                    subject_id=subject_id_int,
                    limit=params.limit
                )
                # nodes are KnowledgeNode models
                result_nodes = [
                    {
                        "id": str(n.id),
                        "title": n.name,
                        "summary": n.description[:200] if n.description else "",
                        "mastery_level": 0 # We might need to fetch status, but for kw search keeping it simple
                    }
                    for n in nodes
                ]
            
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "count": len(result_nodes),
                    "nodes": result_nodes
                },
                widget_type=None  # 查询结果不直接渲染，供 LLM 参考
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e)
            )

class LinkNodesTool(BaseTool):
    """关联知识节点"""
    name = "link_knowledge_nodes"
    description = """建立两个知识点之间的关联关系。
    关系类型包括：
    - prerequisite: A 是 B 的前置知识
    - related: A 和 B 相关
    - derived: B 由 A 推导/衍生
    """
    category = ToolCategory.KNOWLEDGE
    parameters_schema = LinkNodesParams
    requires_confirmation = False
    
    async def execute(
        self, 
        params: LinkNodesParams, 
        user_id: str,
        db_session: Any,
        tool_call_id: Optional[str] = None
    ) -> ToolResult:
        try:
            galaxy_service = GalaxyService(db_session)
            edge = await galaxy_service.create_edge(
                user_id=UUID(user_id),
                source_id=UUID(params.source_node_id),
                target_id=UUID(params.target_node_id),
                relation_type=params.relation_type
            )
            
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "edge_id": str(edge.id) if hasattr(edge, 'id') else "new", # NodeRelation might not have ID if composite PK, but model has Base which usually has ID
                    "source_id": params.source_node_id,
                    "target_id": params.target_node_id,
                    "relation": params.relation_type
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="请确认两个节点 ID 是否正确"
            )
