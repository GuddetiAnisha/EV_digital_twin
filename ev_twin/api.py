from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from .config import ARTIFACT_DIR, DB_PATH, PROFILES
from .schemas import PredictionRequest, ScenarioRequest, MissionRequest
from .service import TwinService
from .storage import PredictionStore


def create_app(artifact_dir=ARTIFACT_DIR, db_path=DB_PATH):
    @asynccontextmanager
    async def lifespan(app):
        app.state.store = PredictionStore(db_path)
        try:
            app.state.twin = TwinService(artifact_dir, app.state.store)
        except FileNotFoundError:
            app.state.twin = None
        yield

    app = FastAPI(title="Application-Aware EV Digital Twin", version="1.0.0", lifespan=lifespan,
                  description="Software-only synthetic research demonstrator. No affiliation with Volvo Penta.")

    def service():
        if app.state.twin is None:
            raise HTTPException(503, "Models missing. Run python -m ev_twin.train and restart the API.")
        return app.state.twin

    @app.get("/health")
    def health():
        return {"status": "ready" if app.state.twin else "models_missing", "synthetic_data": True}

    @app.get("/duty-cycles")
    def cycles():
        return PROFILES

    @app.get("/metrics")
    def metrics():
        return service().report

    @app.post("/predict")
    def predict(request: PredictionRequest):
        return service().predict(request.state, request.model, request.persist)

    @app.post("/scenarios")
    def scenarios(request: ScenarioRequest):
        return service().scenarios(request)

    @app.post("/simulate")
    def simulate(request: MissionRequest):
        return service().simulate_mission(request)

    @app.get("/history")
    def history(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
        return app.state.store.history(limit, offset)

    return app


app = create_app()
