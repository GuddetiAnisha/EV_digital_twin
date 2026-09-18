"""Launch from repository root: python -m streamlit run dashboard.py"""
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from ev_twin.config import ARTIFACT_DIR, DB_PATH, PROFILES, LABELS
from ev_twin.schemas import OperatingState, ScenarioRequest, MissionRequest, MissionSegment
from ev_twin.service import TwinService
from ev_twin.storage import PredictionStore

st.set_page_config(page_title="EMOB • Application-Aware Digital Twin", page_icon="⚡", layout="wide")
st.markdown("""<style>
.stApp {background: #081321; color: #e5edf7;}
[data-testid="stSidebar"] {background: #101e30;}
[data-testid="stMetric"] {background: #14273c; padding: 18px; border-radius: 12px; border-top: 3px solid #45d6b0;}
h1,h2,h3 {letter-spacing: -.025em;}
.eyebrow {color: #45d6b0; letter-spacing: .16em; font-size: .8rem; font-weight: 700;}
</style>""", unsafe_allow_html=True)


@st.cache_resource
def get_twin(artifact_stamp):
    return TwinService(ARTIFACT_DIR, PredictionStore(DB_PATH))


model_path = ARTIFACT_DIR / "models.joblib"
if not model_path.exists():
    st.error("Train the models first: python -m ev_twin.train")
    st.stop()
twin = get_twin(model_path.stat().st_mtime_ns)

with st.sidebar:
    st.markdown("### ⚡ Operating envelope")
    cycle = st.selectbox("Application / duty cycle", list(PROFILES), format_func=lambda key: LABELS[key])
    profile = PROFILES[cycle]
    model = st.selectbox("Estimator", ["best", "baseline", "random_forest", "gradient_boosting"])
    soc = st.slider("State of charge (%)", 0, 100, 75)
    capacity = st.number_input("Nominal battery capacity (kWh)", 20., 400., 160., 10.)
    reserve = st.slider("Reserve SOC (%)", 0, 40, 10)
    speed = st.slider("Moving speed (km/h)", 0., 80., profile["speed_kmh"], key=f"speed_{cycle}")
    load = st.slider("Load fraction", 0., 1., profile["load_fraction"], key=f"load_{cycle}")
    stops = st.slider("Stopped fraction of time", 0., .95, profile["stop_fraction"], key=f"stops_{cycle}")
    ambient = st.slider("Ambient temperature (°C)", -25, 45, 15)
    duration = st.slider("Planned mission (minutes)", 15, 480, 120, 15)
    with st.expander("Thermal system & vehicle details"):
        soh = st.slider("Battery state of health", .7, 1., .95)
        battery_temp = st.slider("Battery temperature (°C)", -20, 60, 24)
        coolant = st.slider("Coolant temperature (°C)", -20, 60, 22)
        thermal = st.slider("Thermal management power (kW)", 0., 15., 2.)
        auxiliary = st.slider("Auxiliary power (kW)", 0., 25., profile["auxiliary_power_kw"], key=f"aux_{cycle}")
        grade = st.slider("Road grade (%)", -8., 12., 0.)
        historical = st.number_input("Past mean consumption (kW)", .1, 250., 28.)

state = OperatingState(soc_pct=soc, reserve_soc_pct=reserve, battery_capacity_kwh=capacity,
    soh_fraction=soh, speed_kmh=speed, load_fraction=load, stop_fraction=stops,
    ambient_temp_c=ambient, battery_temp_c=battery_temp, coolant_temp_c=coolant,
    thermal_power_kw=thermal, auxiliary_power_kw=auxiliary, grade_pct=grade,
    historical_consumption_kw=historical, duty_cycle=cycle, mission_duration_min=duration)
result = twin.predict(state, model)

st.markdown('<div class="eyebrow">EMOB RESEARCH LAB / SOFTWARE DEMONSTRATOR</div>', unsafe_allow_html=True)
st.title("Application-aware EV digital twin")
st.caption("Mission planning • Energy analytics • Duty-cycle intelligence | Independent portfolio project inspired by the Volvo Penta EMOB thesis brief")
st.info("Synthetic operational data only. Research estimates have not been validated on Volvo Penta vehicles. Thermal states are scenario inputs.")
cols = st.columns(4)
for col, label, value in zip(cols, ["Remaining range", "Operating time", "Mission energy demand", "Battery power"],
    [f'{result["remaining_range_km"]:.1f} km', f'{result["remaining_operating_time_min"]:.0f} min', f'{result["expected_energy_consumption_kwh"]:.1f} kWh', f'{result["predicted_power_kw"]:.1f} kW']):
    col.metric(label, value)
st.caption(f'Estimator: {result["model"]} · Available above reserve: {result["available_energy_kwh"]:.1f} kWh · Model {result["model_version"]}')
if result["mission_feasible"]:
    st.success("Planned mission fits within the estimated energy budget.")
else:
    st.warning(f'Mission exceeds the energy budget by {result["energy_shortfall_kwh"]:.1f} kWh.')
for warning in result["warnings"][1:]:
    st.warning(warning)
if st.button("Save prediction to history", type="primary"):
    saved = twin.predict(state, model, persist=True)
    st.success(f'Saved prediction #{saved["history_id"]}')

overview, scenarios_tab, mission_tab, evaluation, history_tab = st.tabs(["Live twin", "What-if laboratory", "Mission simulator", "Model evidence", "Prediction history"])


def chart(fig):
    fig.update_layout(template="plotly_dark", paper_bgcolor="#081321", plot_bgcolor="#101e30", font_color="#e5edf7", margin=dict(l=20, r=20, t=45, b=20))
    st.plotly_chart(fig, width="stretch")


with overview:
    left, right = st.columns([1, 2])
    with left:
        gauge = go.Figure(go.Indicator(mode="gauge+number", value=soc, number={"suffix": "%"}, title={"text": "Battery state of charge"}, gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#45d6b0"}, "steps": [{"range": [0, reserve], "color": "#a64050"}], "threshold": {"line": {"color": "#ffb86b", "width": 3}, "value": reserve}}))
        chart(gauge)
    with right:
        # Static forecast under selected operating conditions, sampled into equal segments.
        request = MissionRequest(segments=[MissionSegment(state=state, duration_min=duration / 24) for _ in range(24)], model=model)
        trajectory = pd.DataFrame(twin.simulate_mission(request)["trajectory"])
        chart(px.line(trajectory, x="elapsed_min", y="soc_pct", markers=True, title="SOC forecast under selected conditions", labels={"elapsed_min": "Operating time (min)", "soc_pct": "SOC (%)"}))
    st.caption(f'Range sensitivity: {result["range_sensitivity_km"][0]:.1f}–{result["range_sensitivity_km"][1]:.1f} km. {result["sensitivity_note"]}')
    comparison = []
    for key, defaults in PROFILES.items():
        scenario = OperatingState.model_validate({**state.model_dump(), **defaults, "duty_cycle": key})
        estimate = twin.predict(scenario, model)
        comparison.append({"Application": LABELS[key], "Range (km)": estimate["remaining_range_km"], "Operating time (min)": estimate["remaining_operating_time_min"], "Power (kW)": estimate["predicted_power_kw"]})
    comparison = pd.DataFrame(comparison)
    chart(px.bar(comparison, x="Application", y="Operating time (min)", color="Power (kW)", color_continuous_scale="Teal", title="Application-aware operating endurance"))
    st.dataframe(comparison, hide_index=True, width="stretch")
    st.caption("Each application changes speed, load, stops, and auxiliary demand. Battery and thermal inputs remain those selected in the sidebar.")

with scenarios_tab:
    st.subheader("Explore one change at a time")
    variable = st.selectbox("Scenario variable", ["ambient_temp_c", "load_fraction", "speed_kmh", "thermal_power_kw"])
    values = {"ambient_temp_c": [-20, -10, 0, 10, 20, 30, 40], "load_fraction": [0., .2, .4, .6, .8, 1.], "speed_kmh": [0., 5., 10., 20., 30., 40., 50.], "thermal_power_kw": [0., 2., 4., 6., 8., 10., 12.] }[variable]
    variants = [OperatingState.model_validate({**state.model_dump(), variable: value}) for value in values]
    output = twin.scenarios(ScenarioRequest(base=state, scenarios=variants, model=model))
    sweep = pd.DataFrame([{variable: value, "Range (km)": item["remaining_range_km"], "Operating time (min)": item["remaining_operating_time_min"], "Power (kW)": item["predicted_power_kw"]} for value, item in zip(values, output["scenarios"])])
    a, b = st.columns(2)
    with a:
        chart(px.line(sweep, x=variable, y="Range (km)", markers=True))
    with b:
        chart(px.line(sweep, x=variable, y="Operating time (min)", markers=True))
    st.caption("Controlled sensitivity experiment: other inputs, including historical consumption and thermal power, are held fixed. These are model responses, not causal claims.")
    st.download_button("Download scenario results", sweep.to_csv(index=False), "scenario_results.csv", "text/csv")
    if st.button("Save scenario comparison"):
        output = twin.scenarios(ScenarioRequest(base=state, scenarios=variants, model=model, persist=True))
        st.success(f'Saved comparison #{output["history_id"]}')

with mission_tab:
    st.subheader("Build a mixed application mission")
    st.write("SOC carries between phases. The simulation stops at reserve and reports any unfinished mission.")
    phases = st.data_editor(pd.DataFrame({"duty_cycle": list(PROFILES), "duration_min": [30., 45., 60., 20.]}),
        column_config={"duty_cycle": st.column_config.SelectboxColumn(options=list(PROFILES), required=True), "duration_min": st.column_config.NumberColumn(min_value=1, max_value=480, required=True)}, hide_index=True, width="stretch")
    segments = [MissionSegment(state=OperatingState.model_validate({**state.model_dump(), **PROFILES[row.duty_cycle], "duty_cycle": row.duty_cycle}), duration_min=row.duration_min) for row in phases.itertuples()]
    mission = twin.simulate_mission(MissionRequest(segments=segments, model=model))
    chart(px.line(pd.DataFrame(mission["trajectory"]), x="elapsed_min", y="soc_pct", markers=True, title="Mixed-duty mission battery trajectory"))
    st.write(f'{"Completed" if mission["completed"] else "Stopped at reserve"} · {mission["elapsed_min"]:.1f} min · {mission["distance_km"]:.1f} km · {mission["energy_consumed_kwh"]:.1f} kWh')
    st.caption(mission["assumption"])

with evaluation:
    st.subheader("Held-out synthetic mission benchmark")
    report = twin.report
    rows = [{"Model": name, **scores["power_kw"]} for name, scores in report["test"].items()]
    table = pd.DataFrame(rows)
    st.dataframe(table, hide_index=True, width="stretch")
    chart(px.bar(table, x="Model", y="mae", color="Model", title="Mean absolute power error on held-out missions (kW)"))
    st.caption("60% train / 20% validation / 20% test by mission. Selection uses validation MAE only. Derived range/time targets assume constant observed window power, not measured future trip completion.")
    test_file = ARTIFACT_DIR / "test_predictions.csv"
    if test_file.exists():
        predictions = pd.read_csv(test_file)
        selected = report["selected_model"]
        chart(px.scatter(predictions, x="measured_power_kw", y=selected, color="duty_cycle", opacity=.45, title="Observed synthetic power vs predicted power", labels={"measured_power_kw": "Synthetic measured power (kW)", selected: "Predicted power (kW)"}))
    duty_scores = pd.DataFrame([{"Model": name, "Application": LABELS[cycle], **values} for name, cycles in report["test_by_duty_cycle_power_kw"].items() for cycle, values in cycles.items()])
    st.dataframe(duty_scores, hide_index=True, width="stretch")
    st.download_button("Download complete evaluation report", json.dumps(report, indent=2), "metrics.json", "application/json")

with history_tab:
    records = twin.store.history(100)
    if records:
        st.dataframe(pd.DataFrame([{"ID": r["id"], "UTC time": r["created_at"], "Type": r["kind"]} for r in records]), hide_index=True, width="stretch")
        st.download_button("Export prediction history", json.dumps(records, indent=2), "history.json", "application/json")
        with st.expander("Inspect latest saved input and result"):
            st.json(records[0])
    else:
        st.write("No saved runs yet. Use ‘Save prediction to history’ to record the current state and estimate.")
