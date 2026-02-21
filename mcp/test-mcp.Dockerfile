FROM python:3.11-slim

WORKDIR /app

COPY dist/*.whl /app/
RUN WHEEL_PATH="$(ls /app/*.whl | head -n1)" && \
    python -m pip install --no-cache-dir "${WHEEL_PATH}[mcp]"

RUN python -c "import specleft.mcp"

COPY tests/mcp/e2e_stdio.py /app/e2e_stdio.py

ENTRYPOINT ["python", "/app/e2e_stdio.py"]
