import sys
import os
import unittest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

class TestP4Services(unittest.TestCase):
    
    def test_routing_service(self):
        print("Testing Routing Service...")
        try:
            from services.routing.main import app
            client = TestClient(app)
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "healthy", "service": "routing"})
            print("✅ Routing Service initialized and healthy.")
        except ImportError as e:
            self.fail(f"Failed to import Routing Service: {e}")
        except Exception as e:
            self.fail(f"Routing Service health check failed: {e}")

    def test_learning_service(self):
        print("Testing Learning Service...")
        try:
            from services.learning.main import app
            client = TestClient(app)
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "healthy", "service": "learning"})
            print("✅ Learning Service initialized and healthy.")
        except ImportError as e:
            self.fail(f"Failed to import Learning Service: {e}")
        except Exception as e:
            self.fail(f"Learning Service health check failed: {e}")

    def test_visualization_service(self):
        print("Testing Visualization Service...")
        try:
            from services.visualization.main import app
            client = TestClient(app)
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "healthy", "service": "visualization"})
            print("✅ Visualization Service initialized and healthy.")
        except ImportError as e:
            self.fail(f"Failed to import Visualization Service: {e}")
        except Exception as e:
            self.fail(f"Visualization Service health check failed: {e}")

if __name__ == '__main__':
    # Patch redis to avoid connection errors during import/startup
    with patch('app.core.cache.cache_service.init_redis', new_callable=AsyncMock), \
         patch('services.visualization.main.manager.init_redis', new_callable=AsyncMock):
        unittest.main()
