import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.job_service import JobService
from app.models.job import Job, JobStatus

@pytest.mark.asyncio
class TestJobService:
    async def test_startup_recovery_resets_stale_jobs(self):
        """Test that RUNNING jobs are reset to FAILED on startup"""
        service = JobService()
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock a job that was left in RUNNING state
        mock_job = MagicMock(spec=Job)
        mock_job.id = "job-123"
        mock_job.status = JobStatus.RUNNING
        
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_job]
        mock_db.execute.return_value = mock_result
        
        # Execute recovery
        await service.startup_recovery(mock_db)
        
        # Verify job was updated
        assert mock_job.status == JobStatus.FAILED
        assert "服务重启" in mock_job.error_message
        assert mock_job.completed_at is not None
        
        # Verify changes were committed
        mock_db.commit.assert_awaited_once()

    async def test_startup_recovery_no_stale_jobs(self):
        """Test that nothing happens if no stale jobs exist"""
        service = JobService()
        mock_db = AsyncMock(spec=AsyncSession)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        await service.startup_recovery(mock_db)
        
        # Should return early without committing
        mock_db.commit.assert_not_awaited()