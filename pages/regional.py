import dash
from dash import html, dcc, callback, Output, Input
import plotly.graph_objects as go
import pandas as pd

from data_loader import regional_df, outage_df, REGIONS, DATE_MIN, DATE_MAX

dash.register_page(__name__, path="/regional", name="Regional Drill-down")

layout = html.Div([
    html.H4("Regional Drill-down", className="mb-1"),
    html.P("Click a region on the map to drill into its load curve, transmission losses, and outage history.",
           className="text-muted"),

    dcc.DatePickerRange(
        id="rg-date-range",
        min_date_allowed=DATE_MIN.date(),
        max_date_allowed=DATE_MAX.date(),
        start_date=DATE_MIN.date(),
        end_date=DATE_MAX.date(),
        className="mb-3",
    ),

    html.Div([
        html.Div(dcc.Graph(id="rg-map", clickData=None), style={"width": "38%", "display": "inline-block", "verticalAlign": "top"}),
        html.Div([
            html.Div(id="rg-selected-label", className="mb-2 fw-bold"),
            dcc.Graph(id="rg-load-curve"),
        ], style={"width": "60%", "display": "inline-block", "marginLeft": "2%", "verticalAlign": "top"}),
    ]),

    dcc.Graph(id="rg-loss-trend"),

    html.H6("Outage events affecting national supply (top 10 in range)", className="mt-3"),
    html.Div(id="rg-outage-table"),

    dcc.Store(id="rg-selected-region", data="Kampala Metro"),
])


@callback(Output("rg-map", "figure"), Input("rg-date-range", "start_date"), Input("rg-date-range", "end_date"))
def update_map(start_date, end_date):
    mask = (regional_df["timestamp"] >= start_date) & (regional_df["timestamp"] <= end_date)
    summary = regional_df.loc[mask].groupby("region").agg(
        demand_mw=("demand_mw", "mean"), lat=("lat", "first"), lon=("lon", "first"),
    ).reset_index()

    fig = go.Figure(go.Scattermap(
        lat=summary["lat"], lon=summary["lon"], mode="markers+text",
        marker=dict(size=summary["demand_mw"] / 4, color=summary["demand_mw"], colorscale="YlOrRd", showscale=True,
                    sizemin=18, colorbar=dict(title="Avg MW")),
        text=summary["region"], textposition="top center",
        customdata=summary["region"],
    ))
    fig.update_layout(
        map=dict(style="open-street-map", center=dict(lat=1.5, lon=32.3), zoom=5.4),
        template="plotly_dark", height=480, margin=dict(t=10, b=0, l=0, r=0),
    )
    return fig


@callback(Output("rg-selected-region", "data"), Input("rg-map", "clickData"))
def store_selected_region(click_data):
    if click_data and "points" in click_data and click_data["points"]:
        return click_data["points"][0].get("customdata", "Kampala Metro")
    return "Kampala Metro"


@callback(
    Output("rg-selected-label", "children"),
    Output("rg-load-curve", "figure"),
    Output("rg-loss-trend", "figure"),
    Output("rg-outage-table", "children"),
    Input("rg-selected-region", "data"),
    Input("rg-date-range", "start_date"),
    Input("rg-date-range", "end_date"),
)
def update_region_detail(region, start_date, end_date):
    mask = (regional_df["timestamp"] >= start_date) & (regional_df["timestamp"] <= end_date) & (regional_df["region"] == region)
    df = regional_df.loc[mask]

    label = f"Selected region: {region}  |  Avg demand {df['demand_mw'].mean():,.0f} MW  |  Avg loss {df['transmission_loss_pct'].mean():.1f}%"

    fig_load = go.Figure(go.Scatter(x=df["timestamp"], y=df["demand_mw"], mode="lines",
                                     line=dict(color="#f4a623", width=1)))
    fig_load.update_layout(title=f"{region} \u2014 Hourly Demand", template="plotly_dark", height=360,
                            yaxis_title="MW", margin=dict(t=50))

    fig_loss = go.Figure(go.Scatter(x=df["timestamp"], y=df["transmission_loss_pct"], mode="lines",
                                     line=dict(color="#c0392b", width=1)))
    fig_loss.update_layout(title=f"{region} \u2014 Transmission Loss %", template="plotly_dark", height=320,
                            yaxis_title="%", margin=dict(t=50))

    out_mask = (outage_df["start_time"] >= start_date) & (outage_df["start_time"] <= end_date)
    top_outages = outage_df.loc[out_mask].sort_values("duration_hrs", ascending=False).head(10)
    if top_outages.empty:
        table = html.P("No outages recorded in this range.", className="text-muted")
    else:
        rows = [html.Tr([html.Td(r["plant"]), html.Td(r["cause"]), html.Td(r["start_time"].strftime("%Y-%m-%d %H:%M")),
                          html.Td(f"{r['duration_hrs']} hrs"), html.Td(f"{r['mw_lost']:.0f} MW")])
                for _, r in top_outages.iterrows()]
        table = html.Table(
            [html.Thead(html.Tr([html.Th("Plant"), html.Th("Cause"), html.Th("Start"), html.Th("Duration"), html.Th("MW Lost")]))]
            + [html.Tbody(rows)],
            className="table table-dark table-sm table-striped",
        )

    return label, fig_load, fig_loss, table
