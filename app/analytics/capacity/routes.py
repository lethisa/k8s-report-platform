from __future__ import annotations

from flask import render_template, request
from flask_login import login_required

from app.analytics.capacity.service import (
    get_capacity_page_context,
    get_storage_section_context,
    get_tenant_quota_section_context,
    get_workload_mapping_section_context,
)


@login_required
def capacity() -> str:
    context = get_capacity_page_context(
        query_args=request.args,
    )

    return render_template(
        'analytics/capacity.html',
        **context,
    )


@login_required
def capacity_storage() -> str:
    context = get_storage_section_context(
        query_args=request.args,
    )

    return render_template(
        'analytics/capacity/partials/_storage_section.html',
        **context,
    )


@login_required
def capacity_tenant_quota() -> str:
    context = get_tenant_quota_section_context(
        query_args=request.args,
    )

    return render_template(
        'analytics/capacity/partials/_tenant_quota_section.html',
        **context,
    )


@login_required
def capacity_workload_mapping() -> str:
    context = get_workload_mapping_section_context(
        query_args=request.args,
    )

    return render_template(
        'analytics/capacity/partials/_workload_mapping_section.html',
        **context,
    )
