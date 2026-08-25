# L99DZ100G tester backend

First runnable backend for a Raspberry Pi 4 fixture. It provides the ST-SPI
driver, a conservative register map, device identification, register dump,
test engine and REST API. GPIO, CAN and LIN are hardware abstraction interfaces
only in this version.

The SPI implementation follows STMicroelectronics **DS11546 Rev 5**: 32-bit
frames, CPOL=0/CPHA=0, 2-bit opcode, 6-bit address and 24-bit application
payload. The register address ranges and identification constants come from
tables 71 and 75-77. Datasheet:
https://www.st.com/resource/en/datasheet/l99dz100gp.pdf

## Run locally

```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\pytest
.venv\Scripts\uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for the generated API console. Mock SPI is
the safe default.

## Raspberry Pi / Docker

Enable SPI on the Pi and set `L99_SPI_BACKEND=spidev` in the environment before
starting Compose. The compose file passes `/dev/spidev0.0` into the container.
The exact bus/device/speed remain configurable. Do not use the write or clear
endpoints on hardware until the fixture-specific test sequence and safety
interlocks have been reviewed.

```sh
L99_SPI_BACKEND=spidev docker compose up --build -d
```

Useful endpoints: `/health`, `/api/v1/device-info`, `/api/v1/registers`,
`/api/v1/tests`, and interactive documentation at `/docs`.

## Current scope

The map intentionally includes register addresses and access modes only. Named
bit fields and fixture tests will be added from reviewed datasheet tables in a
later iteration. No GPIO, CAN, LIN or output actuation is performed yet.
