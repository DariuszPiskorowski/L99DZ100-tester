import os
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.core.device import L99DZ100
from app.core.engine import TestEngine
from app.mock import MockSpiPort
from app.spi import SpidevPort


def make_spi():
    if os.getenv("L99_SPI_BACKEND", "mock") == "spidev":
        return SpidevPort(int(os.getenv("L99_SPI_BUS", "0")), int(os.getenv("L99_SPI_DEVICE", "0")),
                          int(os.getenv("L99_SPI_SPEED_HZ", "500000")))
    return MockSpiPort()


spi = make_spi()
device = L99DZ100(spi)
engine = TestEngine(device)
app = FastAPI(title="L99DZ100G Tester", version="0.1.0")


class WriteRequest(BaseModel):
    value: int = Field(ge=0, le=0xFFFFFF)


class ClearRequest(BaseModel):
    mask: int = Field(ge=0, le=0xFFFFFF)


@app.get("/health")
def health():
    return {"status": "ok", "spi_backend": os.getenv("L99_SPI_BACKEND", "mock")}


@app.get("/api/v1/device-info")
def device_info():
    return device.device_info()


@app.get("/api/v1/registers")
def register_dump():
    return device.dump()


@app.get("/api/v1/registers/{address}")
def read_register(address: int):
    try:
        return device.read(address).as_dict()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.put("/api/v1/registers/{address}")
def write_register(address: int, request: WriteRequest):
    try:
        return device.write(address, request.value).as_dict()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/v1/registers/{address}/read-clear")
def clear_register(address: int, request: ClearRequest):
    try:
        return device.read_clear(address, request.mask).as_dict()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/v1/tests")
def list_tests():
    return {"tests": engine.names()}


@app.post("/api/v1/tests/{name}")
def run_test(name: str):
    try:
        return asdict(engine.run(name))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

