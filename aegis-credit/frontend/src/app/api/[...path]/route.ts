import { NextRequest } from 'next/server';

const BACKEND = 'https://ptahsite-production.up.railway.app';

async function handler(request: NextRequest, { params }: { params: { path: string[] } }) {
  const pathStr = params.path.join('/');
  const search = request.nextUrl.search;
  const url = `${BACKEND}/api/${pathStr}${search}`;

  const headers = new Headers(request.headers);
  headers.delete('host');
  headers.delete('connection');

  const init: RequestInit = { method: request.method, headers };
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    (init as any).body = request.body;
    (init as any).duplex = 'half';
  }

  const upstream = await fetch(url, init);
  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete('transfer-encoding');

  return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const DELETE = handler;
export const PATCH = handler;
