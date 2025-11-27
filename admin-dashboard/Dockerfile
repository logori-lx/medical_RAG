# ==========================================
# 阶段 1: 构建阶段 (Build Stage)
# ==========================================
FROM node:22-alpine as build-stage

# 设置工作目录
WORKDIR /app

# 优先复制 package.json 以利用 Docker 缓存
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制源代码
COPY . .

# 执行构建 (生成 dist 文件夹)
RUN npm run build

# ==========================================
# 阶段 2: 生产环境 (Production Stage)
# ==========================================
FROM nginx:stable-alpine as production-stage

# 复制构建好的 dist 文件到 Nginx 目录
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 复制自定义的 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]