"""
Dynamic Tool Registry
动态工具注册表，支持运行时工具发现和注册
"""
import importlib
import inspect
from typing import Dict, List, Optional, Any, Type
from loguru import logger
from dataclasses import dataclass

from app.tools.base import BaseTool, ToolCategory


@dataclass
class ToolInfo:
    """工具元数据"""
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    category: ToolCategory
    module_path: str
    class_name: str


class DynamicToolRegistry:
    """
    动态工具注册表
    支持从模块自动发现工具和手动注册
    """
    
    _instance = None
    _tools: Dict[str, BaseTool] = {}
    _tool_info: Dict[str, ToolInfo] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
            cls._instance._tool_info = {}
        return cls._instance
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        手动注册单个工具
        
        Args:
            tool: 工具实例
        """
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} ({tool.category.value})")
    
    def register_from_module(self, module_path: str, class_name: str = None) -> bool:
        """
        从模块动态注册工具
        
        Args:
            module_path: 模块路径，如 'app.tools.task_tools'
            class_name: 具体类名，如果为 None 则注册模块中所有 BaseTool 子类
            
        Returns:
            bool: 是否成功
        """
        try:
            module = importlib.import_module(module_path)
            
            if class_name:
                # 注册指定类
                tool_class = getattr(module, class_name)
                if self._is_valid_tool_class(tool_class):
                    instance = tool_class()
                    self.register_tool(instance)
                    return True
            else:
                # 注册模块中所有工具类
                registered = 0
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if self._is_valid_tool_class(obj):
                        instance = obj()
                        self.register_tool(instance)
                        registered += 1
                
                if registered > 0:
                    logger.info(f"Auto-registered {registered} tools from {module_path}")
                    return True
                else:
                    logger.warning(f"No valid tools found in {module_path}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to register tools from {module_path}: {e}")
            return False
    
    def register_from_package(self, package_path: str, recursive: bool = True) -> int:
        """
        从包自动发现并注册所有工具
        
        Args:
            package_path: 包路径，如 'app.tools'
            recursive: 是否递归扫描子模块
            
        Returns:
            int: 注册的工具数量
        """
        try:
            import pkgutil
            import importlib
            
            package = importlib.import_module(package_path)
            total_registered = 0
            
            for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
                full_module_path = f"{package_path}.{modname}"
                
                if ispkg and recursive:
                    # 递归处理子包
                    total_registered += self.register_from_package(full_module_path, recursive)
                else:
                    # 注册模块
                    if self.register_from_module(full_module_path):
                        # 统计注册数量
                        module_tools = [
                            t for t in self._tools.values() 
                            if t.__module__ == full_module_path
                        ]
                        total_registered += len(module_tools)
            
            logger.info(f"Auto-discovered {total_registered} tools from {package_path}")
            return total_registered
            
        except Exception as e:
            logger.error(f"Failed to scan package {package_path}: {e}")
            return 0
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        获取工具实例
        
        Args:
            name: 工具名称
            
        Returns:
            Optional[BaseTool]: 工具实例
        """
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """获取所有工具实例"""
        return list(self._tools.values())
    
    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """
        按分类获取工具
        
        Args:
            category: 工具分类
            
        Returns:
            List[BaseTool]: 工具列表
        """
        return [t for t in self._tools.values() if t.category == category]
    
    def get_openai_tools_schema(self) -> List[dict]:
        """
        获取 OpenAI Function Calling 格式的工具模式
        
        Returns:
            List[dict]: 工具模式列表
        """
        return [tool.to_openai_schema() for tool in self._tools.values()]
    
    def get_tools_description(self, category: Optional[ToolCategory] = None) -> str:
        """
        生成工具描述文本（用于 System Prompt）
        
        Args:
            category: 可选，按分类筛选
            
        Returns:
            str: 格式化的工具描述
        """
        tools = self._tools.values()
        if category:
            tools = [t for t in tools if t.category == category]
        
        if not tools:
            return "暂无可用工具"
        
        lines = ["你可以使用以下工具来帮助用户：\n"]
        for tool in tools:
            lines.append(f"- **{tool.name}**: {tool.description}")
            if tool.parameters_schema:
                lines.append(f"  参数: {tool.parameters_schema}")
        
        return "\n".join(lines)
    
    def get_tool_info(self, name: str) -> Optional[ToolInfo]:
        """
        获取工具元数据
        
        Args:
            name: 工具名称
            
        Returns:
            Optional[ToolInfo]: 工具信息
        """
        if name in self._tool_info:
            return self._tool_info[name]
        
        tool = self._tools.get(name)
        if tool:
            info = ToolInfo(
                name=tool.name,
                description=tool.description,
                parameters_schema=tool.parameters_schema,
                category=tool.category,
                module_path=tool.__class__.__module__,
                class_name=tool.__class__.__name__
            )
            self._tool_info[name] = info
            return info
        
        return None
    
    def list_tools(self, verbose: bool = False) -> List[Dict[str, Any]]:
        """
        列出所有工具信息
        
        Args:
            verbose: 是否包含详细信息
            
        Returns:
            List[Dict[str, Any]]: 工具信息列表
        """
        result = []
        for tool in self._tools.values():
            info = {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
            }
            if verbose:
                info["parameters"] = tool.parameters_schema
                info["module"] = tool.__class__.__module__
                info["class"] = tool.__class__.__name__
            result.append(info)
        return result
    
    def unregister_tool(self, name: str) -> bool:
        """
        注销工具
        
        Args:
            name: 工具名称
            
        Returns:
            bool: 是否成功
        """
        if name in self._tools:
            del self._tools[name]
            if name in self._tool_info:
                del self._tool_info[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False
    
    def clear_all(self) -> None:
        """清空所有工具"""
        self._tools.clear()
        self._tool_info.clear()
        logger.info("All tools cleared")
    
    def _is_valid_tool_class(self, obj: Type) -> bool:
        """
        检查是否是有效的工具类
        
        Args:
            obj: 要检查的对象
            
        Returns:
            bool: 是否是有效工具类
        """
        try:
            return (
                inspect.isclass(obj) and 
                issubclass(obj, BaseTool) and 
                obj != BaseTool and
                not inspect.isabstract(obj)
            )
        except TypeError:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取注册表统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        categories = {}
        for tool in self._tools.values():
            cat = tool.category.value
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total_tools": len(self._tools),
            "categories": categories,
            "tools": [t.name for t in self._tools.values()]
        }


# 全局单例
dynamic_tool_registry = DynamicToolRegistry()