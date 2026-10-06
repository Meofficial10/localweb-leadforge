FROM node:20-slim AS build
WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
RUN npm install
COPY . .
RUN npm run build

FROM node:20-slim
WORKDIR /app
COPY --from=build /app/.next ./.next
COPY --from=build /app/package.json ./
COPY --from=build /app/node_modules ./node_modules
EXPOSE 3000
CMD ["npm", "start"]
