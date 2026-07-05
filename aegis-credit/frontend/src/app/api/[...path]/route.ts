import { NextRequest } from 'next/server';

const BACKEND = process.env.BACKEND_URL || 'https://ptahsite-production.up.railway.app';

const SKIP = new Set(['host', 'connection', 'transfer-encoding', 'te', 'trailer', 'upgrade']);

async function handler(request: NextRequest, { params }: { params: { path: string[] } }) {
  const pathStr = params.path.join('/');
  const search = request.nextUrl.search;
  const url = `${BACKEND}/api/${pathStr}${search}`;

  // Build headers by explicit iteration — new Headers(request.headers) can silently
  // drop the Authorization header on some Next.js/Node runtimes.
  const outHeaders: Record<string, string> = {};
  request.headers.forEach((value, key) => {
    if (!SKIP.has(key.toLowerCase())) {
      outHeaders[key] = value;
    }
  });

  const init: RequestInit = { method: request.method, headers: outHeaders };
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    (init as any).body = request.body;
    (init as any).duplex = 'half';
  }

  const upstream = await fetch(url, init);

  const resHeaders: Record<string, string> = {};
  upstream.headers.forEach((value, key) => {
    if (key.toLowerCase() !== 'transfer-encoding') {
      resHeaders[key] = value;
    }
  });

  return new Response(upstream.body, { status: upstream.status, headers: resHeaders });
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const DELETE = handler;
export const PATCH = handler;
