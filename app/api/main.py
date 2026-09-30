"""Read-only HTTP API for application version 0.1."""

from fastapi import FastAPI, HTTPException

from app.services.scenarios import (
    get_scenario,
    list_scenarios,
    list_sources,
    profile_scenario,
)


app = FastAPI(
    title="Semantic Data Architecture",
    version="0.1.0",
    description="API locale de démonstration du profilage et du matching sémantique.",
)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/scenarios")
def scenarios():
    return [scenario.public_dict() for scenario in list_scenarios()]


@app.get("/scenarios/{identifier}")
def scenario(identifier: str):
    try:
        return get_scenario(identifier).public_dict()
    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/scenarios/{identifier}/sources")
def sources(identifier: str):
    try:
        return [source.public_dict() for source in list_sources(identifier)]
    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/scenarios/{identifier}/profiles")
def profiles(identifier: str):
    try:
        return profile_scenario(identifier)
    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

