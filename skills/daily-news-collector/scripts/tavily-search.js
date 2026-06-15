#!/usr/bin/env node
/**
 * Tavily Search — AI-optimized search API wrapper for news collection
 * Usage: node scripts/tavily-search.js "query" [max_results] [topic] [search_depth]
 *
 * Env: TAVILY_API_KEY required
 * Output: JSON with results array (title, url, content, score)
 */

const https = require('https');

const API_KEY = process.env.TAVILY_API_KEY;
if (!API_KEY) {
  console.error('Error: TAVILY_API_KEY environment variable not set');
  process.exit(1);
}

const query = process.argv[2];
const maxResults = parseInt(process.argv[3]) || 5;
const topic = process.argv[4] || 'general';
const searchDepth = process.argv[5] || 'basic';

if (!query) {
  console.error('Usage: node tavily-search.js "query" [max_results] [topic] [search_depth]');
  process.exit(1);
}

const payload = JSON.stringify({
  query,
  max_results: maxResults,
  topic,
  search_depth: searchDepth,
  include_answer: true,
  include_raw_content: false,
});

const req = https.request({
  hostname: 'api.tavily.com',
  path: '/search',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${API_KEY}`,
  },
}, (res) => {
  let body = '';
  res.on('data', (chunk) => body += chunk);
  res.on('end', () => {
    try {
      const data = JSON.parse(body);
      const output = {
        query: data.query,
        answer: data.answer || null,
        results: (data.results || []).map(r => ({
          title: r.title,
          url: r.url,
          content: r.content?.substring(0, 500),
          score: r.score,
        })),
      };
      console.log(JSON.stringify(output, null, 2));
    } catch (e) {
      console.error('Parse error:', e.message);
      console.error('Raw:', body.substring(0, 500));
      process.exit(1);
    }
  });
});

req.on('error', (e) => {
  console.error('Request error:', e.message);
  process.exit(1);
});

req.write(payload);
req.end();
