# Build the React interface and serve it with the Flask API.
FROM node:22-alpine AS ui-build
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 FLASK_HOST=0.0.0.0 FLASK_PORT=5000
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY assignments/ ./assignments/
COPY docs/ ./docs/
COPY --from=ui-build /web/dist ./frontend/dist
EXPOSE 5000
CMD ["python", "-m", "backend.app"]
