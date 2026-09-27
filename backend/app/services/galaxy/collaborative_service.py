import uuid
from typing import Any

import y_py as Y


class CollaborativeGalaxyService:
    """
    基于 Yjs (y-py) 的协作星图服务
    Collaborative Galaxy Service based on Yjs
    """

    def __init__(self, galaxy_id: str):
        self.galaxy_id = galaxy_id
        self.ydoc = Y.YDoc()
        self.galaxy_map = self.ydoc.get_map("galaxy")

    def add_node(self, user_id: str, node_data: dict[str, Any]):
        """
        添加节点 (CRDT 自动合并)
        Add node (CRDT auto-merge)
        """
        node_id = str(node_data.get("id", uuid.uuid4()))

        # y_py 0.6.2 stub 的 __enter__/__exit__ 缺 self（pybind11-stubgen 产物），
        # with 形态过不了 CI mypy；运行时 __exit__ 在正常/异常路径均提交事务，
        # 显式 begin + try/finally commit 与之等价。
        txn = self.ydoc.begin_transaction()
        try:
            # y_py 0.6.2 stub 把 __init__(dict: dict) 首参当 self，任何实参都被判
            # call-arg；运行时 YMap() 无参反而 TypeError——按真实 API 保留 dict
            # 实参并定点压制该 stub 假阳性。
            initial = {
                "id": node_id,
                "name": node_data.get("name", "New Node"),
                "contributors": [user_id],
                "mastery_scores": {user_id: node_data.get("mastery", 0)},
                "avg_mastery": node_data.get("mastery", 0),
            }
            node_map = Y.YMap(initial)  # type: ignore[call-arg, misc]
            self.galaxy_map.set(txn, node_id, node_map)
        finally:
            txn.commit()

    def update_mastery(self, user_id: str, node_id: str, score: float):
        """
        更新节点掌握度
        Update node mastery
        """
        node_id_str = str(node_id)

        # stub 的 YMap.get 把 fallback 声明为必填位参，运行时默认 None——
        # 显式传 None 语义不变，且满足 CI mypy。
        node_data = self.galaxy_map.get(node_id_str, None)

        if node_data and isinstance(node_data, Y.YMap):
            txn = self.ydoc.begin_transaction()
            try:
                mastery_scores = node_data.get("mastery_scores", None)
                if not isinstance(mastery_scores, dict):
                    mastery_scores = {}

                new_scores = dict(mastery_scores)
                new_scores[user_id] = score
                node_data.set(txn, "mastery_scores", new_scores)

                scores = list(new_scores.values())
                avg_mastery = sum(scores) / len(scores) if scores else 0
                node_data.set(txn, "avg_mastery", avg_mastery)
            finally:
                txn.commit()

    def get_state_vector(self) -> bytes:
        return Y.encode_state_vector(self.ydoc)

    def get_update(self) -> bytes:
        return Y.encode_state_as_update(self.ydoc)

    def apply_update(self, update: bytes):
        Y.apply_update(self.ydoc, update)
