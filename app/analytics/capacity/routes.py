# app/analytics/capacity/routes.py

from __future__ import annotations

from flask import render_template, request
from flask_login import login_required

from app.analytics.capacity.service import get_capacity_page_context


@login_required
def capacity() -> str:
    context = get_capacity_page_context(
        query_args=request.args,
    )

    return render_template(
        'analytics/capacity/index.html',
        **context,
    )
