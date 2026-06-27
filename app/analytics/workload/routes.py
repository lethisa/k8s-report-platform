# app/analytics/workload/routes.py

from __future__ import annotations

from flask import render_template, request
from flask_login import login_required

from app.analytics.workload.service import get_workload_analysis_context


@login_required
def workload() -> str:
    context = get_workload_analysis_context(
        query_args=request.args,
    )

    return render_template(
        'analytics/workload/index.html',
        **context,
    )


@login_required
def workload_tenant_quota() -> str:
    context = get_workload_analysis_context(
        query_args=request.args,
    )

    return render_template(
        'analytics/workload/partials/_tenant_quota_section.html',
        **context,
    )


@login_required
def workload_resource_mapping() -> str:
    context = get_workload_analysis_context(
        query_args=request.args,
    )

    return render_template(
        'analytics/workload/partials/_workload_mapping_section.html',
        **context,
    )
