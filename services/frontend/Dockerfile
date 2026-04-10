FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm cache clean --force
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY . .

# Accept build arguments for API base URL and frontend password
ARG VITE_API_BASE_URL
ARG VITE_FRONTEND_PASSWD
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_FRONTEND_PASSWD=$VITE_FRONTEND_PASSWD

RUN npm run build

# Pin nginx version to avoid unexpected entrypoint/behavior differences across environments
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]



