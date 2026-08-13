FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

# Vite nhúng biến VITE_* vào bundle lúc build, không đọc được lúc chạy.
# Vì vậy địa chỉ backend phải truyền vào từ build-arg.
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_WS_URL=""
ARG VITE_USE_MOCK=false
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_WS_URL=$VITE_WS_URL \
    VITE_USE_MOCK=$VITE_USE_MOCK

COPY . .
RUN npm run build

FROM nginx:alpine
# Cấu hình fallback SPA — thiếu file này thì deep link sẽ trả 404.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
