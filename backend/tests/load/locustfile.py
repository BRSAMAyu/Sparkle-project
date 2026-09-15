"""
Locust Load Testing Script for Sparkle API
Sparkle API负载测试脚本

Run with:
  locust -f backend/tests/load/locustfile.py --host=http://localhost:8080

Or use the provided orchestration script:
  ./scripts/run-load-tests.sh locust
"""

import time
import json
import random
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


# Test data
USER_IDS = [f"user_{i}" for i in range(100)]
SESSION_IDS = [f"session_{i}" for i in range(50)]
SAMPLE_QUERIES = [
    "Explain quantum computing",
    "What is machine learning?",
    "Help me understand calculus",
    "Write a Python function",
    "Explain the theory of relativity",
]


class SparkleUser(HttpUser):
    """
    Simulates a typical Sparkle user interacting with the system
    模拟典型Sparkle用户与系统交互
    """

    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    def on_start(self):
        """Called when a user starts"""
        # Initialize user session
        self.user_id = random.choice(USER_IDS)
        self.session_id = random.choice(SESSION_IDS)
        self.client.headers.update({
            "Content-Type": "application/json",
            "User-Agent": f"Locust/{self.user_id}",
        })

    @task(3)
    def send_chat_message(self):
        """
        Send a chat message (most common operation)
        发送聊天消息（最常见操作）
        """
        query = random.choice(SAMPLE_QUERIES)

        response = self.client.post(
            "/api/v1/chat/stream",
            json={
                "user_id": self.user_id,
                "session_id": self.session_id,
                "content": query,
                "stream": True,
            },
            catch_response=True,
        )

        if response.status_code == 200:
            # Success
            response.success()
        elif response.status_code == 429:
            # Rate limited - expected under load
            response.success()
        else:
            response.failure(f"Got status code {response.status_code}")

    @task(2)
    def get_chat_history(self):
        """
        Retrieve chat history
        获取聊天历史
        """
        response = self.client.get(
            f"/api/v1/chat/history?session_id={self.session_id}",
            catch_response=True,
        )

        if response.status_code in [200, 404]:
            response.success()
        else:
            response.failure(f"Got status code {response.status_code}")

    @task(1)
    def submit_feedback(self):
        """
        Submit response feedback
        提交响应反馈
        """
        response = self.client.post(
            "/api/v1/chat/feedback",
            json={
                "user_id": self.user_id,
                "response_id": f"response_{random.randint(1, 1000)}",
                "rating": random.randint(1, 5),
                "comment": "Load test feedback",
            },
            catch_response=True,
        )

        if response.status_code in [200, 201, 404]:
            response.success()
        else:
            response.failure(f"Got status code {response.status_code}")

    @task(1)
    def get_user_profile(self):
        """
        Get user profile
        获取用户配置文件
        """
        response = self.client.get(
            f"/api/v1/users/{self.user_id}",
            name="/api/v1/users/[user_id]",
            catch_response=True,
        )

        if response.status_code in [200, 404]:
            response.success()
        else:
            response.failure(f"Got status code {response.status_code}")

    @task(1)
    def health_check(self):
        """
        Health check endpoint
        健康检查端点
        """
        response = self.client.get("/health", catch_response=True)

        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Got status code {response.status_code}")


class WebSocketChatUser(HttpUser):
    """
    Simulates WebSocket chat connections
    模拟WebSocket聊天连接
    """

    wait_time = between(5, 10)

    def on_start(self):
        """Initialize WebSocket connection"""
        self.user_id = random.choice(USER_IDS)
        self.session_id = random.choice(SESSION_IDS)

    @task
    def websocket_connection(self):
        """
        Simulate WebSocket connection (via HTTP upgrade check)
        模拟WebSocket连接（通过HTTP升级检查）
        """
        # Note: This is a simplified test
        # Real WebSocket testing requires websockets library
        response = self.client.get(
            "/ws/chat",
            headers={
                "Upgrade": "websocket",
                "Connection": "Upgrade",
            },
            catch_response=True,
        )

        if response.status_code in [101, 426]:  # Switching Protocols or Upgrade Required
            response.success()
        else:
            response.failure(f"Got status code {response.status_code}")


class GalaxyUser(HttpUser):
    """
    Simulates knowledge graph (Galaxy) interactions
    模拟知识星图交互
    """

    wait_time = between(2, 8)

    def on_start(self):
        """Initialize Galaxy user"""
        self.user_id = random.choice(USER_IDS)

    @task(3)
    def get_galaxy_nodes(self):
        """
        Get knowledge graph nodes
        获取知识星图节点
        """
        response = self.client.get(
            f"/api/v1/galaxy/nodes?user_id={self.user_id}&limit=50",
            name="/api/v1/galaxy/nodes",
            catch_response=True,
        )

        if response.status_code in [200, 404]:
            response.success()
        else:
            response.failure(f"Got status code {response.status_code}")

    @task(2)
    def get_galaxy_edges(self):
        """
        Get knowledge graph edges
        获取知识星图边
        """
        response = self.client.get(
            f"/api/v1/galaxy/edges?user_id={self.user_id}&limit=100",
            name="/api/v1/galaxy/edges",
            catch_response=True,
        )

        if response.status_code in [200, 404]:
            response.success()
        else:
            response.failure(f"Got status code {response.status_code}")

    @task(1)
    def search_knowledge(self):
        """
        Search knowledge base
        搜索知识库
        """
        query = random.choice(SAMPLE_QUERIES)
        response = self.client.post(
            "/api/v1/galaxy/search",
            json={
                "user_id": self.user_id,
                "query": query,
                "limit": 20,
            },
            catch_response=True,
        )

        if response.status_code in [200, 404]:
            response.success()
        else:
            response.failure(f"Got status code {response.status_code}")


class PlanSubmissionUser(HttpUser):
    """
    Simulates plan submission and review workflow
    模拟计划提交和审查工作流
    """

    wait_time = between(10, 30)

    def on_start(self):
        """Initialize plan user"""
        self.user_id = random.choice(USER_IDS)

    @task(2)
    def submit_plan(self):
        """
        Submit a learning plan
        提交学习计划
        """
        plan_data = {
            "user_id": self.user_id,
            "title": f"Load Test Plan {random.randint(1, 1000)}",
            "goal": "Test goal",
            "steps": [
                {"title": f"Step {i}", "duration_days": 1}
                for i in range(1, 6)
            ],
        }

        response = self.client.post(
            "/api/v1/plans",
            json=plan_data,
            catch_response=True,
        )

        if response.status_code in [200, 201, 400]:
            response.success()
        else:
            response.failure(f"Got status code {response.status_code}")

    @task(1)
    def get_plan_review(self):
        """
        Get plan review status
        获取计划审查状态
        """
        plan_id = f"plan_{random.randint(1, 100)}"
        response = self.client.get(
            f"/api/v1/plans/{plan_id}/review",
            name="/api/v1/plans/[plan_id]/review",
            catch_response=True,
        )

        if response.status_code in [200, 404]:
            response.success()
        else:
            response.failure(f"Got status code {response.status_code}")

    @task(1)
    def submit_plan_feedback(self):
        """
        Submit plan review feedback
        提交计划审查反馈
        """
        plan_id = f"plan_{random.randint(1, 100)}"
        response = self.client.post(
            f"/api/v1/plans/{plan_id}/review",
            json={
                "user_id": self.user_id,
                "approved": random.choice([True, False]),
                "comment": "Load test feedback",
            },
            catch_response=True,
        )

        if response.status_code in [200, 404, 400]:
            response.success()
        else:
            response.failure(f"Got status code {response.status_code}")


# Event handlers for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """
    Custom event handler for request logging
    自定义请求日志事件处理程序
    """
    if exception:
        print(f"Request failed: {name} - {exception}")
    else:
        # Log slow requests
        if response_time > 1000:  # > 1 second
            print(f"Slow request: {name} took {response_time}ms")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Called when the test stops
    测试停止时调用
    """
    if isinstance(environment.runner, MasterRunner):
        print("\n=== Load Test Summary ===")
        print(f"Total requests: {environment.stats.total.num_requests}")
        print(f"Failures: {environment.stats.total.num_failures}")
        print(f"Median response time: {environment.stats.total.median_response_time}ms")
        print(f"95th percentile: {environment.stats.total.get_response_time_percentile(0.95)}ms")
        print(f"Requests/s: {environment.stats.total.total_rps}")
        print("=======================\n")
