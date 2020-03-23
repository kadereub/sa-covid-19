import os
import numpy as np
import pandas as pd
import json

import dash
import dash_core_components as dcc
import dash_html_components as html

import plotly.graph_objs as go
import plotly.express as px

app = dash.Dash(
    __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}]
)

server = app.server
app.config.suppress_callback_exceptions = True
app.title = "SA-COVID-19"

# Load Coronavirus Data and GeoJson
downloads_path = os.path.expanduser('_data')
raw_data = pd.read_csv(os.path.join(downloads_path, "sa-coronavirus-data.csv"))
with open(os.path.join(downloads_path, "south-africa-provinces-GeoJson.json")) as json_file:
    provinces = json.load(json_file)


def clean_data(data):
    """
    Cleans the imported raw coronavirus data, to be used in the Dashboard plots
    """
    covid_data = data.copy(deep=True)
    covid_data["Age"].fillna(covid_data["Age"].mean())
    age_bins = [0, 17, 35, 50, 65, covid_data["Age"].max()]
    covid_data["Date"] = pd.to_datetime(covid_data["Date"], infer_datetime_format=True)
    covid_data["Gender"] = covid_data["Gender"].str.lower().str.title()
    covid_data["Province"] = covid_data["Province"].str.lower().str.title()
    covid_data.loc[covid_data["Province"] == "Kwazulu-Natal", "Province"] = "KwaZulu-Natal"
    covid_data["Age"] = covid_data["Age"].fillna(covid_data["Age"].mean())
    covid_data['Age Group'] = pd.cut(covid_data['Age'], bins=age_bins)
    return covid_data


def generate_choropleth_map_chart(covid_data, fc):
    """
    Plot a South African map of provinces with number of cases.

    Args:
        covid_data (pandas.DataFrame): The processed covid-19 data.
        fc (dict): THe loaded GeoJson object used to create the SA map.

    Returns:
        plotly.graph_objs._figure.Figure: A figure and layout of the SA map.
    """
    tst = covid_data.groupby(["Province"], as_index=False)["Case No."].count()
    tst.columns = ["Province", "#Confirmed Cases"]
    fig = px.choropleth(tst, geojson=fc, color="#Confirmed Cases",
                        locations="Province", featureidkey="properties.NAME_1",
                        projection="mercator",
                        color_continuous_scale=px.colors.sequential.Viridis
                        )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )
    # fig.show(config={'scrollZoom': False})
    return fig


def generate_confirmed_cases_plot(covid_data, f, yf):
    ts_data = covid_data.groupby(["Date"], as_index=False)["Case No."].max()
    ts_data.columns = ["Date", "#Confirmed Cases"]
    fig = go.Figure()
    # Add traces
    fig.add_trace(go.Scatter(x=ts_data.Date, y=ts_data["#Confirmed Cases"],
                             mode='markers',
                             name='Actual',
                             marker=dict(size=8)
                             )
                  )
    fig.add_trace(go.Scatter(x=xf, y=np.cumsum(np.exp(f(yf))),
                             mode='lines+markers',
                             name='Forecast',
                             marker=dict(size=5, opacity=0.5),
                             line=dict(width=2, dash='dot')
                             ),
                  )
    return fig

def generate_heatmap_plot(covid_data):
    ts_data = covid_data.groupby(["Date", "Province"], as_index=False)["Case No."].count()
    ts_data.columns = ["Date", "Province", "#New Cases"]
    ts_data["#New Cases"].fillna(0, inplace=True)

    fig = go.Figure(data=go.Heatmap(
        z=ts_data["#New Cases"],
        x=ts_data["Date"],
        y=ts_data["Province"],
        colorscale='Viridis', hoverongaps=False))

    return fig


def generate_bar_plot(covid_data):
    ts_data = covid_data.groupby(["Age Group", "Province"], as_index=False)["Case No."].count()  # .fillna(0)
    ts_data.columns = ["Age Group", "Province", "#Confirmed Cases"]
    ts_data["Age Group"] = ts_data["Age Group"].astype(str)

    fig = px.bar(ts_data, x="Province", y="#Confirmed Cases", color='Age Group',
                 barmode='group', color_discrete_sequence=px.colors.sequential.Viridis_r)
    return fig

# Clean Data
covid_data = clean_data(raw_data)
ts_data = covid_data.groupby(["Date"], as_index=False)["Case No."].count()
ts_data.columns = ["Date", "#Confirmed Cases"]

# Fit a Polynomial to the log values, i.e if exponential then polynomial will refelct this
z = np.polyfit(ts_data.index.values, np.log(ts_data["#Confirmed Cases"].values), 2)
f = np.poly1d(z)
xf = ts_data.Date.append(pd.Series([ts_data.Date.values[-1] + pd.Timedelta(1, "D"),
                                    ts_data.Date.values[-1] + pd.Timedelta(2, "D")])
                                    , ignore_index=True)
yf = xf.index.values

scatter_fig = generate_confirmed_cases_plot(covid_data, f, yf)
map_fig = generate_choropleth_map_chart(covid_data, provinces)
heatmap_fig = generate_heatmap_plot(covid_data)
bar_fig = generate_bar_plot(covid_data)

app.layout = html.Div(

    id="mainContainer", children=[
        html.Div(id="output-clientside"),
        html.Div(
            [
                html.Div(
                    [
                        html.A(
                            html.Img(
                                src=app.get_asset_url("virus_icon.png"),
                                id="plotly-image",
                                style={
                                    "height": "60px",
                                    "width": "auto",
                                    "margin-bottom": "25px",
                                },
                        ), href="https://www.who.int/emergencies/diseases/novel-coronavirus-2019")
                    ],
                    className="one-third column",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3(
                                    "COVID-19 Tracker for South Africa",
                                    style={"margin-bottom": "0px"},
                                ),
                                html.H5(
                                    "For further government information"),
                                html.H5(
                                html.A("SA Coronavirus Website",
                                       href="https://sacoronavirus.co.za/category/press-releases-and-notices/"),
                                    style={"margin-top": "0px"}
                                )
                            ]
                        )
                    ],
                    className="one-half column",
                    id="title",
                ),
                html.Div(
                    [
                        html.A(
                            html.Button("About COVID-19", id="learn-more-button"),
                            href="https://sacoronavirus.co.za/information-about-the-virus-2/",
                        )
                    ],
                    className="one-third column",
                    id="button",
                ),
            ],
            id="header",
            className="row flex-display",
            style={"margin-bottom": "25px"},
        ),

        html.Div(
            children=[
                html.Div(
                    [
                        html.Div(
                            [html.H6(covid_data.Date.max().strftime("%d-%b"), id="gasText"), html.P("Last Updated")],
                            id="gas",
                            className="mini_container",
                        ),
                        html.Div(
                            [html.H6(covid_data.shape[0], id="well_text"), html.P("#Total Cases")],
                            id="wells",
                            className="mini_container",
                        ),
                        html.Div(
                            [html.H6(covid_data.groupby(["Date"], as_index=True)["Case No."].count().values[-1],
                                     id="oilText"), html.P("#New Cases")],
                            id="oil",
                            className="mini_container",
                        ),
                        html.Div(
                            [html.H6(covid_data.groupby(["Province"], as_index=True)["Case No."].count().idxmax(axis=0),
                                     id="waterText"), html.P("Most Cases")],
                            id="water",
                            className="mini_container",
                        ),
                    ],
                    id="info-container",
                    className="row container-display",
                )
            ],
            id="right-column",
            className="eight-columns",
        ),

        html.Br(),

        html.Div(className="graph-title",
                 children=[
                     html.H5(children='''
        Provincial Confirmed Cases
    ''')]
                 ),

    html.Div(
    className="plot-container plotly",
    children=[
        dcc.Graph(
            figure=map_fig,
            config={'scrollZoom': False}
        )]
    ),

    html.Br(),
    html.Br(),

    html.Div(className="graph-title",
             children=[
                 html.H5(children='''
            Total Confirmed Cases in South Africa
        ''')]
             ),

    html.Div(
        className="plot-container plotly",
        children=[
            dcc.Graph(
                figure=scatter_fig,
            )]
    ),

    html.Br(),
    html.Br(),

    html.Div(className="graph-title",
             children=[
                 html.H5(children='''
         Number of New Cases by Province per Day
     ''')]
             ),

    html.Div(
        className="plot-container plotly",
        children=[
            dcc.Graph(
                figure=heatmap_fig,
            )]
    ),

    html.Br(),
    html.Br(),

    html.Div(className="graph-title",
             children=[
                 html.H5(children='''
     Total Number of Confirmed Cases by Age and Province
 ''')]
             ),

    html.Div(
        className="plot-container plotly",
        children=[
            dcc.Graph(
                figure=bar_fig,
            )]
    ),

    html.Br(),
    html.Br(),
    html.Br(),

    html.Div(
        style={"position": "dynamic", "left": 0, "bottom":0, "width": "100%"},
        children=[
        html.P('''
        This website and its contents herein, including all data, mapping, and analysis (“Website”), all rights reserved, is provided to the public strictly for educational purposes only. 
        The Website relies upon publicly available data from the South African Department of Health's COVID-19 Online Resource & News Portal. 
        Reliance on the Website for medical guidance or use of the Website in commerce is strictly prohibited.
        Please note this is aimed at only visualizing the covid-19 data in South Africa, the data is updated manually and thus may not always be timely. 
        For the most recent information on COVID-19 please see the Government website above. Say safe, and wash thy hands!
        ''',
        style={"text-align":"center", "font-weight": "bold"}
        ),
        html.Br()
        ]
    )

])

if __name__ == '__main__':
    app.run_server(
        debug=True, port=8050,
        dev_tools_hot_reload=False, use_reloader=False
    )