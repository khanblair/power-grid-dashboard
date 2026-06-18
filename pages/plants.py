import dash
from dash import html, dcc, callback, Output, Input
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from data_loader import generation_df, outage_df, water_df, PLANTS, HYDRO_PLANTS, SOURCE_COLORS, DATE_MIN, DATE_MAX

dash.register_page(__name__, path="/plants", name="Plant Performance")

layout = html.Div([
    html.H4("Plant Performance & Maintenance", className="mb-1"),
    html.P("Capacity factors, outage history, and (for hydro) correlation with reservoir water levels.",
           className="text-muted"),

    dcc.Graph(id="pl-capacity-factor"),

    html.H6("Outage timeline (2025)", className="mt-3"),
    dcc.Graph(id="pl-gantt"),

    html.Div([
        html.Label("Select a hydro plant to inspect water-level correlation:", className="me-2"),
        dcc.Dropdown(
            id="pl-hydro-select",
            options=[{"label": p, "value": p} for p in HYDRO_PLANTS],
            value=HYDRO_PLANTS[0] if HYDRO_PLANTS else None,
            style={"width": "320px", "color": "#000"},
        ),
    ], className="mt-4 mb-2 d-flex align-items-center"),

    dcc.Graph(id="pl-water-correlation"),
])


@callback(Output("pl-capacity-factor", "figure"), Input("pl-hydro-select", "value"))
def update_capacity_factor(_):
    cap_lookup = generation_df.groupby("plant")["capacity_mw"].first()
    avg_output = generation_df.groupby("plant")["output_mw"].mean()
    source_lookup = generation_df.groupby("plant")["source"].first()
    cf = (avg_output / cap_lookup * 100).sort_values(ascending=True)

    colors = [SOURCE_COLORS[source_lookup[p]] for p in cf.index]
    fig = go.Figure(go.Bar(x=cf.values, y=cf.index, orientation="h", marker_color=colors,
                            text=[f"{v:.1f}%" for v in cf.values], textposition="outside"))
    fig.update_layout(title="Average Capacity Factor by Plant (full year)", template="plotly_dark",
                       height=380, margin=dict(t=50, l=140), xaxis_title="Capacity factor (%)")
    return fig


@callback(Output("pl-gantt", "figure"), Input("pl-hydro-select", "value"))
def update_gantt(_):
    df = outage_df.copy()
    if df.empty:
        return go.Figure()
    fig = px.timeline(
        df, x_start="start_time", x_end="end_time", y="plant", color="source",
        color_discrete_map=SOURCE_COLORS, hover_data=["cause", "duration_hrs", "mw_lost"],
    )
    fig.update_yaxes(categoryorder="array", categoryarray=sorted(df["plant"].unique(), reverse=True))
    fig.update_layout(template="plotly_dark", height=360, margin=dict(t=20))
    return fig


@callback(Output("pl-water-correlation", "figure"), Input("pl-hydro-select", "value"))
def update_water_correlation(plant):
    if not plant:
        return go.Figure()
    plant_df = generation_df[generation_df["plant"] == plant].copy()
    plant_df["date"] = plant_df["timestamp"].dt.normalize()
    daily_output = plant_df.groupby("date")["output_mw"].mean().reset_index()
    merged = daily_output.merge(water_df, on="date", how="left")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=merged["date"], y=merged["output_mw"], name=f"{plant} avg daily output (MW)",
                              line=dict(color="#1f9e89", width=1.5), yaxis="y1"))
    fig.add_trace(go.Scatter(x=merged["date"], y=merged["water_level_index"], name="Water level index",
                              line=dict(color="#5dade2", width=1.5, dash="dot"), yaxis="y2"))
    fig.update_layout(
        title=f"{plant}: Output vs Reservoir Water Level (drought correlation)",
        template="plotly_dark", height=400, margin=dict(t=50),
        yaxis=dict(title="MW", side="left"),
        yaxis2=dict(title="Water level index", overlaying="y", side="right"),
        legend=dict(orientation="h", y=-0.2),
    )
    return fig
