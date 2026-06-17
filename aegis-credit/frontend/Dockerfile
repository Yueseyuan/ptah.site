FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --prefer-offline || npm ci

COPY . .

ARG NEXT_PUBLIC_API_URL=http://localhost:8082
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NODE_OPTIONS="--max-old-space-size=3072"
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

EXPOSE 3000
ENV PORT=3000
CMD ["npm", "start"]
