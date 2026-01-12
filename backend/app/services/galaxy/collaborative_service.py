import y_py as Y
from typing import Dict, Any, List, Optional
import uuid

class CollaborativeGalaxyService:
    """
    基于 Yjs (y-py) 的协作星图服务
    Collaborative Galaxy Service based on Yjs
    """

    def __init__(self, galaxy_id: str):
        self.galaxy_id = galaxy_id
        self.ydoc = Y.YDoc()
        self.galaxy_map = self.ydoc.get_map("galaxy")

    def add_node(self, user_id: str, node_data: Dict[str, Any]):
        """
        添加节点 (CRDT 自动合并)
        Add node (CRDT auto-merge)
        """
        node_id = str(node_data.get("id", uuid.uuid4()))
        
        with self.ydoc.begin_transaction() as txn:
            node_map = Y.YMap({
                "id": node_id,
                "name": node_data.get("name", "New Node"),
                "contributors": [user_id],
                "mastery_scores": {user_id: node_data.get("mastery", 0)},
                "avg_mastery": node_data.get("mastery", 0)
            })
            self.galaxy_map.set(txn, node_id, node_map)

    def update_mastery(self, user_id: str, node_id: str, score: float):
        """
        更新节点掌握度
        Update node mastery
        """
        node_id_str = str(node_id)
        
        # get might not need txn
        node_data = self.galaxy_map.get(node_id_str)
        
        if node_data and isinstance(node_data, Y.YMap):
            with self.ydoc.begin_transaction() as txn:
                mastery_scores = node_data.get("mastery_scores")
                if not isinstance(mastery_scores, dict):
                    mastery_scores = {}
                
                new_scores = dict(mastery_scores)
                new_scores[user_id] = score
                node_data.set(txn, "mastery_scores", new_scores)

                scores = list(new_scores.values())
                avg_mastery = sum(scores) / len(scores) if scores else 0
                node_data.set(txn, "avg_mastery", avg_mastery)

    def get_state_vector(self) -> bytes:
        return Y.encode_state_vector(self.ydoc)

    def get_update(self) -> bytes:
        return Y.encode_state_as_update(self.ydoc)

    def apply_update(self, update: bytes):
        Y.apply_update(self.ydoc, update)
