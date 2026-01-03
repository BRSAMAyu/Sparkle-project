import asyncio
from typing import Dict, Any, Callable, List, Optional, Union, Coroutine
from dataclasses import dataclass, field
import inspect
from loguru import logger

# ==========================================
# 1. 核心数据结构 (Core Data Structures)
# ==========================================

@dataclass
class WorkflowState:
    """
    工作流状态黑板
    在节点间传递的共享状态
    """
    messages: List[Dict[str, str]] = field(default_factory=list)
    context_data: Dict[str, Any] = field(default_factory=dict)
    next_step: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    is_finished: bool = False

    def update(self, new_data: Dict[str, Any]):
        """更新上下文数据"""
        self.context_data.update(new_data)

    def append_message(self, role: str, content: str):
        """追加消息"""
        self.messages.append({"role": role, "content": content})


# ==========================================
# 2. 图引擎 (Graph Engine)
# ==========================================

class StateGraph:
    """
    轻量级状态图引擎
    支持：
    - 节点注册
    - 静态边
    - 条件边 (动态路由)
    - 异步执行
    """
    def __init__(self):
        self.nodes: Dict[str, Callable] = {}
        self.edges: Dict[str, Union[str, Callable]] = {}
        self.entry_point: Optional[str] = None
        self._compiled = False

    def add_node(self, name: str, action: Callable[[WorkflowState], Coroutine[Any, Any, WorkflowState]]):
        """注册节点"""
        self.nodes[name] = action
        return self

    def add_edge(self, from_node: str, to_node: str):
        """添加静态边"""
        self.edges[from_node] = to_node
        return self

    def add_conditional_edge(self, from_node: str, router: Callable[[WorkflowState], str]):
        """添加条件边 (动态路由)"""
        self.edges[from_node] = router
        return self

    def set_entry_point(self, node_name: str):
        """设置入口节点"""
        self.entry_point = node_name
        return self

    def compile(self):
        """编译图 (简单检查)"""
        if not self.entry_point:
            raise ValueError("Entry point not set")
        if self.entry_point not in self.nodes:
            raise ValueError(f"Entry point '{self.entry_point}' not found in nodes")
        self._compiled = True
        return self

    async def invoke(self, initial_state: WorkflowState) -> WorkflowState:
        """执行图"""
        if not self._compiled:
            self.compile()

        # compile() 确保了 entry_point 不为 None
        assert self.entry_point is not None
        current_node_name: str = self.entry_point
        state = initial_state
        steps = 0
        max_steps = 20  # 防止死循环

        logger.info(f"🚀 Starting graph execution from '{current_node_name}'")

        while current_node_name != "__end__" and steps < max_steps:
            steps += 1
            logger.info(f"📍 executing node: {current_node_name}")
            
            # 1. 执行当前节点
            node_func = self.nodes[current_node_name]
            
            try:
                # 支持异步和同步函数
                if inspect.iscoroutinefunction(node_func):
                    new_state = await node_func(state)
                else:
                    new_state = node_func(state)
                
                # 状态通常是原地修改的，但支持返回新状态
                if new_state:
                    state = new_state

            except Exception as e:
                logger.error(f"❌ Error in node '{current_node_name}': {e}")
                state.errors.append(f"Node {current_node_name} failed: {str(e)}")
                # 简单的错误恢复：结束
                break

            # 2. 决定下一跳
            if current_node_name in self.edges:
                edge = self.edges[current_node_name]
                
                if isinstance(edge, str):
                    # 静态边
                    next_node = edge
                elif callable(edge):
                    # 条件边 (Router)
                    next_node = edge(state)
                    logger.info(f"🔀 Router decided next step: {next_node}")
                else:
                    logger.warning(f"Unknown edge type for {current_node_name}")
                    next_node = "__end__"
            else:
                # 没有出边，结束
                next_node = "__end__"

            current_node_name = next_node

        if steps >= max_steps:
            logger.warning("⚠️ Max steps reached, stopping execution")

        logger.info("🏁 Graph execution finished")
        return state


# ==========================================
# 3. 示例场景：错题诊断循环 (POC)
# ==========================================

async def analyze_node(state: WorkflowState) -> WorkflowState:
    """ProblemSolver Agent"""
    logger.info("🤖 Analyzing problem...")
    # 模拟 LLM 分析
    state.append_message("analyzer", "分析结果：用户在[积分变换]上有概念混淆")
    state.context_data["weak_point"] = "integration_transform"
    state.context_data["understanding_level"] = 0.5
    return state

async def teacher_node(state: WorkflowState) -> WorkflowState:
    """Teacher Agent"""
    logger.info("👨‍🏫 Explaining concept...")
    level = state.context_data.get("difficulty", "normal")
    state.append_message("teacher", f"正在以 {level} 难度讲解积分变换...")
    return state

async def check_understanding_node(state: WorkflowState) -> WorkflowState:
    """模拟用户反馈 (Human Loop)"""
    logger.info("🤔 Checking understanding...")
    # 这里模拟用户反馈，实际应该等待用户输入
    # 假设第一次不理解，第二次理解了
    if state.context_data.get("attempt", 0) == 0:
        state.context_data["user_feedback"] = "confused"
        state.context_data["attempt"] = 1
        state.append_message("user", "我还是看不懂公式")
    else:
        state.context_data["user_feedback"] = "understood"
        state.append_message("user", "哦！现在我明白了")
    return state

def router_logic(state: WorkflowState) -> str:
    """路由逻辑"""
    feedback = state.context_data.get("user_feedback", "")
    if feedback == "confused":
        return "simplifier"
    elif feedback == "understood":
        return "practice"
    else:
        return "__end__"

async def simplifier_node(state: WorkflowState) -> WorkflowState:
    """Simplifier Agent"""
    logger.info("📉 Simplifying explanation...")
    state.context_data["difficulty"] = "easy"
    state.append_message("simplifier", "别担心，我们用一个简单的例子来类比...")
    return state

async def practice_node(state: WorkflowState) -> WorkflowState:
    """Generator Agent"""
    logger.info("✍️ Generating practice...")
    state.append_message("practice", "既然理解了，来做道题试试！")
    return state

# ==========================================
# 4. 运行演示
# ==========================================

async def main():
    # 1. 定义图
    graph = StateGraph()
    
    # 2. 添加节点
    graph.add_node("analyzer", analyze_node)
    graph.add_node("teacher", teacher_node)
    graph.add_node("check_understanding", check_understanding_node)
    graph.add_node("simplifier", simplifier_node)
    graph.add_node("practice", practice_node)
    
    # 3. 添加边
    # Start -> Analyzer -> Teacher -> Check -> [Router]
    graph.set_entry_point("analyzer")
    graph.add_edge("analyzer", "teacher")
    graph.add_edge("teacher", "check_understanding")
    
    # Router: Check -> (Simplifier OR Practice)
    graph.add_conditional_edge("check_understanding", router_logic)
    
    # Simplifier -> Teacher (Loop back!)
    graph.add_edge("simplifier", "teacher")
    
    # Practice -> End
    graph.add_edge("practice", "__end__")
    
    # 4. 运行
    print("\n=== Starting Workflow Execution ===\n")
    initial_state = WorkflowState()
    final_state = await graph.invoke(initial_state)
    
    print("\n=== Execution History ===")
    for msg in final_state.messages:
        print(f"[{msg['role'].upper()}]: {msg['content']}")

if __name__ == "__main__":
    asyncio.run(main())
