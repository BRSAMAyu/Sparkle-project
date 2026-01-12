import asyncio
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.analytics.weekly_synthesis_service import WeeklySynthesisService
from app.services.llm_service import LLMService

async def test_report_generation():
    # Mock DB session
    mock_db = AsyncMock()
    
    # Mock LLM Service
    mock_llm = MagicMock(spec=LLMService)
    
    # Initialize service
    service = WeeklySynthesisService(mock_db, mock_llm)
    
    # Mock dependencies
    service.stats_service.get_weekly_summary = AsyncMock(return_value={
        "total_study_minutes": 450,
        "focus_sessions_count": 12,
        "mastery_gain": 0.15,
        "tasks_completed": 8
    })
    service.stats_service.get_daily_activity_trend = AsyncMock(return_value=[
        {"date": "2026-01-01", "minutes": 60},
        {"date": "2026-01-02", "minutes": 90}
    ])
    service.blindspot_analyzer.analyze_blindspots = AsyncMock(return_value=[
        {"node_name": "Quantum Mechanics", "mastery": 0.3}
    ])

    # 1. Generate Report Data
    user_id = "test-user-uuid"
    print(f"Generating report for user: {user_id}")
    report_data = await service.generate_report(user_id)
    print("Report data generated successfully.")
    
    # 2. Generate PDF
    output_path = os.path.join(os.path.dirname(__file__), '..', 'test_weekly_report.pdf')
    print(f"Generating PDF at: {output_path}")
    
    try:
        await service.generate_pdf(report_data, output_path)
        if os.path.exists(output_path):
            print(f"SUCCESS: PDF generated at {output_path}")
            print(f"File size: {os.path.getsize(output_path)} bytes")
        else:
            print("FAILED: PDF file not found after generation.")
    except Exception as e:
        print(f"FAILED: PDF generation crashed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_report_generation())
