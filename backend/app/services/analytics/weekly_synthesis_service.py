from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
try:
    from jinja2 import Environment, FileSystemLoader
    import weasyprint
    import matplotlib
    matplotlib.use('Agg')
except ImportError:
    pass # Dependencies might not be installed in the environment yet
import os

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.analytics.weekly_stats_service import WeeklyStatsService
from app.services.analytics.blindspot_analyzer import BlindspotAnalyzer
from app.services.llm_service import LLMService

class WeeklySynthesisService:
    """
    Weekly Synthesis Service
    Orchestrates the generation of the Weekly Learning Report.
    """

    def __init__(self, db: AsyncSession, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service
        self.stats_service = WeeklyStatsService(db)
        self.blindspot_analyzer = BlindspotAnalyzer(db)
        
        # Setup Jinja2 for PDF generation
        template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

    async def generate_report(self, user_id: str, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate full weekly report data and PDF.
        """
        if not end_date:
            end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        # 1. Gather Data
        stats = await self.stats_service.get_weekly_summary(user_id, start_date, end_date)
        daily_trend = await self.stats_service.get_daily_activity_trend(user_id, start_date, end_date)
        blindspots = await self.blindspot_analyzer.analyze_blindspots(user_id, limit=3)
        
        # 2. LLM Synthesis
        synthesis = await self._generate_llm_insights(stats, blindspots)
        
        report_data = {
            "user_id": user_id,
            "week_of": start_date.strftime("%Y-%m-%d"),
            "stats": stats,
            "daily_trend": daily_trend,
            "blindspots": blindspots,
            "ai_insight": synthesis.get("insight", "No insight generated."),
            "ai_suggestion": synthesis.get("suggestion", "Keep learning!"),
            "generated_at": datetime.utcnow().isoformat()
        }

        # 3. Generate PDF (Optional: can be triggered separately or here)
        # pdf_path = await self._render_pdf(report_data)
        # report_data["pdf_path"] = pdf_path

        return report_data

    async def generate_pdf(self, report_data: Dict[str, Any], output_path: str) -> str:
        """
        Render report data to PDF.
        """
        template = self.jinja_env.get_template('weekly_report.html')
        html_content = template.render(data=report_data)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        weasyprint.HTML(string=html_content).write_pdf(output_path)
        return output_path

    async def _generate_llm_insights(self, stats: Dict[str, Any], blindspots: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Use LLM to generate qualitative insights.
        """
        prompt = f"""
        Analyze this weekly learning data and provide a brief insight and a constructive suggestion.
        
        Stats:
        - Study Time: {stats.get('total_study_minutes')} mins
        - Focus Sessions: {stats.get('focus_sessions_count')}
        - Mastery Gained: {stats.get('mastery_gain')}
        - Tasks Completed: {stats.get('tasks_completed')}
        
        Identified Blindspots (Knowledge Gaps):
        {json.dumps(blindspots, indent=2)}
        
        Output format (JSON):
        {{
            "insight": "One sentence summary of performance.",
            "suggestion": "One actionable tip to address blindspots or improve consistency."
        }}
        """
        
        try:
            # Mocking LLM call for now as per instructions "Basic LLM generation logic (mocked or connected...)"
            # If real connection is needed, use self.llm_service.complete(prompt)
            # For MVP stability, let's use a mock or simple call if configured.
            
            # response = await self.llm_service.chat_completion(messages=[{"role": "user", "content": prompt}])
            # return json.loads(response)
            
            # Return Mock for speed/reliability in this MVP step
            return {
                "insight": f"You spent {stats.get('total_study_minutes')} minutes learning this week, with good focus consistency.",
                "suggestion": f"Try to tackle the '{blindspots[0]['node_name']}' concept next, as it seems to be a blocker." if blindspots else "Great job! Try exploring a new subject next week."
            }
        except Exception as e:
            print(f"LLM Generation failed: {e}")
            return {
                "insight": "Data analysis complete.",
                "suggestion": "Continue your learning streak."
            }
