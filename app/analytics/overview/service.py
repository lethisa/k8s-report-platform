class AnalyticsOverviewService:
    def get_overview(self):

        return {
            'avg_cpu_usage': 68,
            'avg_memory_usage': 72,
            'avg_storage_usage': 61,
            'cluster_health_score': 92,
            'active_alerts': 3,
            'generated_reports': 48,
        }
