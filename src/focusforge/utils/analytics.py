"""Analytics and graph generation using Plotly."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import List, Tuple
import json


def create_daily_usage_chart(app_data: List[Tuple[str, float]], web_data: List[Tuple[str, float]]) -> str:
    """
    Create daily usage pie charts.
    
    Args:
        app_data: List of (app_name, seconds) tuples
        web_data: List of (domain, seconds) tuples
        
    Returns:
        JSON string of the figure
    """
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{'type': 'pie'}, {'type': 'pie'}]],
        subplot_titles=('App Usage', 'Website Usage')
    )
    
    # App usage pie chart
    if app_data:
        apps, app_times = zip(*app_data[:10])  # Top 10
        fig.add_trace(
            go.Pie(
                labels=apps,
                values=[t/60 for t in app_times],  # Convert to minutes
                hole=0.3,
                marker=dict(
                    colors=['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe',
                           '#fa709a', '#fee140', '#30cfd0', '#a8edea', '#fed6e3']
                )
            ),
            row=1, col=1
        )
    
    # Website usage pie chart
    if web_data:
        sites, web_times = zip(*web_data[:10])
        fig.add_trace(
            go.Pie(
                labels=sites,
                values=[t/60 for t in web_times],
                hole=0.3,
                marker=dict(
                    colors=['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe',
                           '#fa709a', '#fee140', '#30cfd0', '#a8edea', '#fed6e3']
                )
            ),
            row=1, col=2
        )
    
    fig.update_layout(
        height=400,
        showlegend=True,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig.to_json()


def create_weekly_trend_chart(daily_stats: List[dict]) -> str:
    """
    Create weekly productivity trend chart.
    
    Args:
        daily_stats: List of daily stat dictionaries
        
    Returns:
        JSON string of the figure
    """
    dates = [stat['date'] for stat in daily_stats]
    productive_hours = [stat.get('productive_hours', 0) for stat in daily_stats]
    distracted_hours = [stat.get('distracted_hours', 0) for stat in daily_stats]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=dates,
        y=productive_hours,
        name='Productive',
        marker_color='#43e97b',
        marker_line_color='#38f9d7',
        marker_line_width=2
    ))
    
    fig.add_trace(go.Bar(
        x=dates,
        y=distracted_hours,
        name='Distracted',
        marker_color='#fa709a',
        marker_line_color='#fee140',
        marker_line_width=2
    ))
    
    fig.update_layout(
        title='Weekly Productivity Trend',
        xaxis_title='Date',
        yaxis_title='Hours',
        barmode='stack',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350,
        font=dict(family='Arial', size=12)
    )
    
    return fig.to_json()


def create_focus_sessions_chart(sessions: List[dict]) -> str:
    """
    Create focus sessions timeline.
    
    Args:
        sessions: List of focus session dictionaries
        
    Returns:
        JSON string of the figure
    """
    if not sessions:
        return create_empty_chart("No focus sessions yet")
    
    names = [s['name'] for s in sessions]
    durations = [s['duration_minutes'] for s in sessions]
    success_rates = [s.get('success_rate', 0) for s in sessions]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=names,
        y=durations,
        marker=dict(
            color=success_rates,
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title='Success Rate')
        ),
        text=[f"{d}m" for d in durations],
        textposition='outside'
    ))
    
    fig.update_layout(
        title='Focus Sessions',
        xaxis_title='Session',
        yaxis_title='Duration (minutes)',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350
    )
    
    return fig.to_json()


def create_productivity_score_gauge(score: float) -> str:
    """
    Create productivity score gauge.
    
    Args:
        score: Productivity score (0-100)
        
    Returns:
        JSON string of the figure
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Productivity Score", 'font': {'size': 24}},
        delta={'reference': 70, 'increasing': {'color': "#43e97b"}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': "#667eea"},
            'bgcolor': "rgba(255,255,255,0.1)",
            'borderwidth': 2,
            'bordercolor': "white",
            'steps': [
                {'range': [0, 30], 'color': 'rgba(250, 112, 154, 0.3)'},
                {'range': [30, 70], 'color': 'rgba(254, 225, 64, 0.3)'},
                {'range': [70, 100], 'color': 'rgba(67, 233, 123, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': 85
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': "white", 'family': "Arial"},
        height=300
    )
    
    return fig.to_json()


def create_empty_chart(message: str) -> str:
    """Create an empty chart with a message."""
    fig = go.Figure()
    
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=20, color="gray")
    )
    
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=300
    )
    
    return fig.to_json()
