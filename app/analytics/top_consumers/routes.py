# app/analytics/top_consumers/routes.py

from __future__ import annotations

from flask import render_template, request
from flask_login import login_required

from app.analytics.top_consumers.service import get_top_consumers_context


@login_required
def top_consumers() -> str:
    context = get_top_consumers_context(
        query_args=request.args,
    )

    return render_template(
        'analytics/top_consumers/index.html',
        **context,
    )


@login_required
def top_consumers_section() -> str:
    context = get_top_consumers_context(
        query_args=request.args,
    )

    return render_template(
        'analytics/top_consumers/partials/_consumer_section.html',
        **context,
    )


@login_required
def top_consumers_table() -> str:
    context = get_top_consumers_context(
        query_args=request.args,
    )

    return render_template(
        'analytics/top_consumers/partials/_consumer_table.html',
        **context,
    )
