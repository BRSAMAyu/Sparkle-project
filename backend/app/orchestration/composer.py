from typing import Any, Dict, List, Optional
from app.tools.base import ToolResult

class ResponseComposer:
    """
    响应组装器
    将 LLM 文本回复和工具执行结果组装成统一的 API 响应
    """
    
    def compose_response(
        self,
        llm_text: str,
        tool_results: List[ToolResult],
        requires_confirmation: bool = False,
        confirmation_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        组装最终响应
        
        Args:
            llm_text: LLM 生成的文本回复
            tool_results: 工具执行结果列表
            requires_confirmation: 是否需要用户确认
            confirmation_data: 确认操作的数据
            
        Returns:
            统一的 API 响应结构
        """
        # 提取所有需要渲染的组件
        widgets = []
        for result in tool_results:
            if result.success and result.widget_type:
                widgets.append({
                    "type": result.widget_type,
                    "data": result.widget_data
                })
        
        # 提取错误信息
        errors = [
            {
                "tool": r.tool_name,
                "message": r.error_message,
                "suggestion": r.suggestion
            }
            for r in tool_results if not r.success
        ]
        
        response = {
            "message": llm_text,
            "widgets": widgets,
            "tool_results": [r.model_dump() for r in tool_results],
            "has_errors": len(errors) > 0,
            "errors": errors if errors else None,
        }
        
        # 需要用户确认的操作
        if requires_confirmation:
            response["requires_confirmation"] = True
            response["confirmation_data"] = confirmation_data
        
        return response
