import dash
from dash import html, dcc, callback, Output, Input
import plotly.graph_objects as go
import pandas as pd

from data_loader import national_df, generation_df, DATE_MIN, DATE_MAX, SOURCE_COLORS

dash.register_page(__name__, path="/", name="National Overview")

layout = html.Div([
    html.H4("National Grid Overview", className="mb-1"),
    html.P("System-wide generation, demand, and stability \u2014 select a date range to drill in.",
           className="text-muted"),

    dcc.DatePickerRange(
        id="ov-date-range",
        min_date_allowed=DATE_MIN.date(),
        max_date_allowed=DATE_MAX.date(),
        start_date=DATE_MIN.date(),
        end_date=DATE_MAX.date(),
        className="mb-3",
    ),

    html.Div(id="ov-kpi-cards", className="mb-4"),

    dash.dcc.Graph(id="ov-stacked-supply"),

    html.Div([
        html.Div(dash.dcc.Graph(id="ov-mix-donut"), style={"width": "48%", "display": "inline-block"}),
        html.Div(dash.dcc.Graph(id="ov-frequency"), style={"width": "48%", "display": "inline-block", "marginLeft": "4%"}),
    ]),
])


def _kpi_card(label, value, suffix="", color="#1f9e89"):
    return html.Div(
        [
            html.Div(label, className="text-muted small"),
            html.Div(f"{value}{suffix}", style={"fontSize": "1.6rem", "fontWeight": "700", "color": color}),
        ],
        style={
            "border": "1px solid #444", "borderRadius": "8px", "padding": "0.75rem 1rem",
            "display": "inline-block", "minWidth": "170px", "marginRight": "0.75rem", "marginBottom": "0.5rem",
        },
    )


@callback(
    Output("ov-kpi-cards", "children"),
    Output("ov-stacked-supply", "figure"),
    Output("ov-mix-donut", "figure"),
    Output("ov-frequency", "figure"),
    Input("ov-date-range", "start_date"),
    Input("ov-date-range", "end_date"),
)
def update_overview(start_date, end_date):
    mask = (national_df["timestamp"] >= start_date) & (national_df["timestamp"] <= end_date)
    df = national_df.loc[mask]

    peak_demand = df["demand_mw"].max()
    avg_loss_mw = (df["demand_with_losses_mw"] - df["demand_mw"]).mean()
    avg_freq = df["frequency_hz"].mean()
    stress_hours = int((df["unmet_demand_mw"] > 0).sum())
    renewable_share = (df["hydro_supply_mw"].sum() + df["solar_supply_mw"].sum()) / df["total_supply_mw"].replace(0, 1).sum() * 100

    cards = html.Div([
        _kpi_card("Peak Demand", f"{peak_demand:,.0f}", " MW", "#f4a623"),
        _kpi_card("Avg Transmission Loss", f"{avg_loss_mw:,.0f}", " MW", "#c0392b"),
        _kpi_card("Avg Frequency", f"{avg_freq:.2f}", " Hz", "#1f9e89"),
        _kpi_card("Renewable Share", f"{renewable_share:.1f}", " %", "#1f9e89"),
        _kpi_card("Hours Under Stress", f"{stress_hours:,}", "", "#c0392b" if stress_hours else "#1f9e89"),
    ])

    fig_stack = go.Figure()
    for col, source in [("hydro_supply_mw", "Hydro"), ("solar_supply_mw", "Solar"), ("thermal_supply_mw", "Thermal")]:
        fig_stack.add_trace(go.Scatter(
            x=df["timestamp"], y=df[col], name=source, stackgroup="supply",
            line=dict(width=0.5, color=SOURCE_COLORS[source]),
        ))
    fig_stack.add_trace(go.Scatter(
        x=df["timestamp"], y=df["demand_mw"], name="Demand", mode="lines",
        line=dict(width=2, color="white", dash="dot"),
    ))
    fig_stack.update_layout(
        title="Generation Mix vs Demand", template="plotly_dark",
        height=420, margin=dict(t=50, b=10), legend=dict(orientation="h", y=-0.2),
    )

    mix_totals = {
        "Hydro": df["hydro_supply_mw"].sum(),
        "Solar": df["solar_supply_mw"].sum(),
        "Thermal": df["thermal_supply_mw"].sum(),
    }
    fig_donut = go.Figure(go.Pie(
        labels=list(mix_totals.keys()), values=list(mix_totals.values()), hole=0.5,
        marker=dict(colors=[SOURCE_COLORS[k] for k in mix_totals]),
    ))
    fig_donut.update_layout(title="Energy Mix (period total)", template="plotly_dark", height=380, margin=dict(t=50))

    fig_freq = go.Figure()
    fig_freq.add_trace(go.Scatter(x=df["timestamp"], y=df["frequency_hz"], mode="lines",
                                   line=dict(color="#5dade2", width=1), name="Frequency"))
    fig_freq.add_hline(y=50.0, line_dash="dash", line_color="white", annotation_text="50 Hz nominal")
    fig_freq.update_layout(title="Grid Frequency Stability", template="plotly_dark", height=380,
                            yaxis_title="Hz", margin=dict(t=50))

    return cards, fig_stack, fig_donut, fig_freq
