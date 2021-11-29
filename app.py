import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from metric_definitions import metric_definitions


# FUNCTIONS


@st.cache()
def fetch_data(resource_id):
    """
    Fetch all data from Analyze Boston for a given resource id
    """
    # define urls
    boston_api_root = "https://data.boston.gov"
    search_endpont = "/api/3/action/datastore_search"
    limit = 32000
    full_url = (
        f"{boston_api_root}{search_endpont}?resource_id={resource_id}&limit={limit}"
    )

    # initial request
    r = requests.get(full_url)
    total_records = r.json()["result"]["total"]
    all_records = r.json()["result"]["records"]
    fields = [c["id"] for c in r.json()["result"]["fields"]]

    # page through
    while len(all_records) < total_records:
        next_url = r.json()["result"]["_links"]["next"]
        r = requests.get(boston_api_root + next_url)
        all_records.extend(r.json()["result"]["records"])

    # convert to dataframe and fix column order
    df = pd.DataFrame(all_records)
    df = df.reindex(columns=fields)
    return df


@st.cache()
def enhance_dataframe(df):
    """
    Fix datatypes and add features for the CityScore Full Metrics dataset
    """
    # set id as index
    df = df.set_index("_id")
    # fix datatypes
    df["score_calculated_ts"] = pd.to_datetime(df["score_calculated_ts"])
    df["target"] = pd.to_numeric(df["target"], errors="coerce")
    df["day_score"] = pd.to_numeric(df["day_score"], errors="coerce")
    df["day_numerator"] = pd.to_numeric(df["day_numerator"], errors="coerce")
    df["day_denominator"] = pd.to_numeric(df["day_denominator"], errors="coerce")
    df["week_score"] = pd.to_numeric(df["week_score"], errors="coerce")
    df["week_numerator"] = pd.to_numeric(df["week_numerator"], errors="coerce")
    df["week_denominator"] = pd.to_numeric(df["week_denominator"], errors="coerce")
    df["month_score"] = pd.to_numeric(df["month_score"], errors="coerce")
    df["month_numerator"] = pd.to_numeric(df["month_numerator"], errors="coerce")
    df["month_denominator"] = pd.to_numeric(df["month_denominator"], errors="coerce")
    df["quarter_score"] = pd.to_numeric(df["quarter_score"], errors="coerce")
    df["quarter_numerator"] = pd.to_numeric(df["quarter_numerator"], errors="coerce")
    df["quarter_denominator"] = pd.to_numeric(
        df["quarter_denominator"], errors="coerce"
    )
    df["latest_score_flag"] = df["latest_score_flag"].astype(int).astype(bool)
    # add date indicator columns
    df["day"] = df["score_calculated_ts"].dt.date - pd.DateOffset(1)
    df["day_start"] = df["day"]
    df["week"] = df["score_calculated_ts"].dt.isocalendar().week
    df["week_start"] = df["score_calculated_ts"].dt.to_period("W").dt.start_time
    df["month"] = df["score_calculated_ts"].dt.month
    df["month_start"] = df["score_calculated_ts"].dt.to_period("M").dt.to_timestamp()
    df["quarter"] = df["score_calculated_ts"].dt.quarter
    df["quarter_start"] = df["score_calculated_ts"].dt.to_period("Q").dt.to_timestamp()
    df["year"] = df["score_calculated_ts"].dt.year
    return df


@st.cache()
def df_to_csv(df):
    return df.to_csv().encode("utf-8")


prettify_names = {m["metric_name"]: m["metric_pretty"] for m in metric_definitions}
metric_pretty_list = [m["metric_pretty"] for m in metric_definitions]

# set up app
st.set_page_config(layout="wide")
st.title("City of Boston: CityScore")

# fetch data and fix datatypes
cityscore_fullmetrics = "dd657c02-3443-4c00-8b29-56a40cfe7ee4"
df = fetch_data(cityscore_fullmetrics)
df = enhance_dataframe(df)

# set up sidebar nav
with st.sidebar:
    st.subheader("Navigation")
    menu = st.selectbox(
        "What would you like to see?",
        [
            "Current Scores",
            "About the Metrics",
            "Historical Scores",
            "Show Me the Data",
        ],
    )

st.header(menu)
if menu == "Current Scores":
    df_current_scores = df[df["latest_score_flag"] == True]
    df_current_scores = (
        df_current_scores[
            [
                "metric_name",
                "score_calculated_ts",
                "day",
                "day_score",
                "week",
                "week_start",
                "week_score",
                "month",
                "month_score",
                "quarter",
                "quarter_score",
            ]
        ]
        .reset_index(drop=True)
        .sort_values(by=["metric_name"])
    )
    with st.container():
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        col1.metric("Day", df_current_scores["day"].max().strftime("%b %d, %Y"))
        col2.metric(
            "Week of", df_current_scores["week_start"].max().strftime("%b %d, %Y")
        )
        col3.metric("Month", df_current_scores["month"].max().astype(str))
        col4.metric("Quarter", df_current_scores["quarter"].max().astype(str))

    df_current_scores_display = df_current_scores[
        ["metric_name", "day_score", "week_score", "month_score", "quarter_score"]
    ]
    df_current_scores_display["metric_name"] = df_current_scores_display[
        "metric_name"
    ].map(prettify_names)
    df_current_scores_display = df_current_scores_display.set_index("metric_name")

    def style_under_1(score, props=""):
        return props if score < 1 else None

    df_current_scores_display = (
        df_current_scores_display.style.applymap(style_under_1, props="color:red;")
        .applymap(lambda metric: "opacity: 20%;" if pd.isna(metric) else None)
        .format("{:.3f}")
        .set_table_styles(
            [
                {
                    "selector": "th",
                    "props": [("background-color", "#288BE4"), ["color", "white"]],
                }
            ]
        )
    )
    st.table(df_current_scores_display)
elif menu == "About the Metrics":
    st.markdown(
        """[Source: boston.gov](https://www.boston.gov/sites/default/files/file/document_files/2019/04/cityscore_metric_definitions_targets_for_website.pdf)"""
    )
    with st.sidebar:
        see_definitions = st.radio(
            "View:", ["All metric descriptions", "Some metric descriptions"]
        )
        see_stats = st.checkbox("See metric summary statistics")
    if see_stats:
        st.subheader("Metric Summary Statistics")
        metric_summary_stats = df.groupby(["metric_name"]).agg(
            {
                "day": ["min", "max"],
                "day_score": ["count", "min", "max"],
                "week_score": ["count", "min", "max"],
                "month_score": ["count", "min", "max"],
                "quarter_score": ["count", "min", "max"],
            }
        )
        metric_summary_stats.index = metric_summary_stats.index.map(prettify_names)
        metric_summary_stats.columns = [
            ": ".join(col) for col in metric_summary_stats.columns.values
        ]
        metric_summary_stats["day: min"] = metric_summary_stats["day: min"].dt.strftime(
            "%Y-%m-%d"
        )
        metric_summary_stats["day: max"] = metric_summary_stats["day: max"].dt.strftime(
            "%Y-%m-%d"
        )
        st.dataframe(metric_summary_stats)
    st.subheader("Metric Definitions")
    metric_info = (
        df[["metric_name", "metric_logic", "target"]]
        .drop_duplicates(subset=["metric_name"])
        .reset_index(drop=True)
    )
    metric_info["metric_name_pretty"] = metric_info["metric_name"].map(prettify_names)
    # metric_info.to_json()
    if see_definitions == "All metric descriptions":
        for metric in metric_definitions:
            st.subheader(metric["metric_pretty"])
            st.markdown(metric["metric_description"])
            m = metric["metric_name"]
    elif see_definitions == "Some metric descriptions":
        choose_metric_definition = st.multiselect("Choose metrics:", metric_pretty_list)
        for metric in metric_definitions:
            if metric["metric_pretty"] in choose_metric_definition:
                st.subheader(metric["metric_pretty"])
                st.markdown(metric["metric_description"])
elif menu == "Historical Scores":
    with st.sidebar:
        time_unit = st.radio("Choose a time unit", ["day", "week", "month", "quarter"])
        metric_selected = st.selectbox("Choose a metric", metric_pretty_list)
        show_data = st.checkbox("Show the data")
    trimmed_df = df[["metric_name", f"{time_unit}_start", f"{time_unit}_score"]]
    trimmed_df["metric_name"] = trimmed_df["metric_name"].map(prettify_names)
    trimmed_df = trimmed_df[trimmed_df["metric_name"] == metric_selected]
    trimmed_df = trimmed_df.drop_duplicates().sort_values(by=[f"{time_unit}_start"])
    fig = px.line(
        trimmed_df,
        x=f"{time_unit}_start",
        y=f"{time_unit}_score",
        title=f"{time_unit.capitalize()} Score for {metric_selected}",
    )
    st.plotly_chart(fig, use_container_width=True)
    if show_data:
        st.dataframe(trimmed_df)
elif menu == "Show Me the Data":
    st.dataframe(df.sort_values(by=["score_calculated_ts"], ascending=False))
    today = df["day"].max().strftime("%Y-%m-%d")
    csv = df_to_csv(df)
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name=f"boston_cityscore_{today}.csv",
        mime="text/csv",
    )
