# Sophia Frontend

This is the frontend application for the Sophia project, built with React, TypeScript, and Material-UI.

## Environment Configuration

The frontend can be configured to connect to different API servers using environment variables.

### Development

For local development, the frontend will automatically connect to the API server running on the same host. No additional configuration is needed.

### Production

For production deployment, you need to set the `VITE_API_BASE_URL` environment variable to point to your API server.

#### Using Docker Compose

1. Create a `.env` file in the `infra/` directory based on `env.sample.txt`
2. Set the `VITE_API_BASE_URL` variable to your production API URL:

```bash
# For example, if your API is running on a different server:
VITE_API_BASE_URL=https://api.yourdomain.com

# Or if it's on the same server but different port:
VITE_API_BASE_URL=http://your-server.com:8080
```

3. Rebuild and deploy:

```bash
cd infra/
docker-compose down
docker-compose up --build -d
```

#### Manual Docker Build

If building the frontend manually:

```bash
cd services/frontend/
docker build --build-arg VITE_API_BASE_URL=https://api.yourdomain.com -t sophia-frontend .
```

### Environment Variables

- `VITE_API_BASE_URL`: The base URL for the API server (defaults to `http://localhost:8080`)

## Development

```bash
npm install
npm run dev
```

## Building

```bash
npm run build
```

## Testing

```bash
npm test
```