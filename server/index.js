import express from 'express';
import fetch from 'node-fetch';
import cors from 'cors';
import yahooFinance from 'yahoo-finance2';

const app = express();
app.use(cors());
app.use(express.json());

app.get('/api/options/:symbol', async (req, res) => {
    const { symbol } = req.params;
    const { date } = req.query;
    try {
        const url = `https://query2.finance.yahoo.com/v7/finance/options/${encodeURIComponent(symbol)}${date ? `?date=${encodeURIComponent(String(date))}` : ''}`;
        const headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://finance.yahoo.com/',
            'Origin': 'https://finance.yahoo.com'
        };

        const upstream = await fetch(url, { headers });
        let text = await upstream.text();

        // If Yahoo rejects with Invalid Crumb, try to obtain a crumb by requesting the options page
        if (!upstream.ok && upstream.status === 401 && text && text.includes('Invalid Crumb')) {
            console.log('Upstream returned Invalid Crumb; attempting crumb fetch flow');
            const pageUrl = `https://finance.yahoo.com/quote/${encodeURIComponent(symbol)}/options`;
            const pageRes = await fetch(pageUrl, { headers });
            const setCookieHeader = pageRes.headers.get('set-cookie') || '';
            const rawCookies = [];
            if (setCookieHeader) {
                // single header case
                rawCookies.push(setCookieHeader.split(';')[0]);
            } else if (pageRes.headers.raw && pageRes.headers.raw()['set-cookie']) {
                // node-fetch exposes raw headers
                pageRes.headers.raw()['set-cookie'].forEach((c) => rawCookies.push(c.split(';')[0]));
            }
            const cookieHeader = rawCookies.join('; ');
            const pageText = await pageRes.text();

            // Try to extract crumb from page JS
            let crumbMatch = pageText.match(/"CrumbStore":\{"crumb":"([^"]+)"\}/);
            if (!crumbMatch) crumbMatch = pageText.match(/"crumb":"([^"]+)"/);

            let crumb;
            if (!crumbMatch) {
                console.warn('Failed to extract crumb from options page; attempting /v1/test/getcrumb fallback');
                try {
                    const gcRes = await fetch('https://query1.finance.yahoo.com/v1/test/getcrumb', { headers });
                    const gcText = await gcRes.text();
                    if (gcRes.ok && gcText) {
                        crumb = gcText.trim();
                        console.log('Obtained crumb from getcrumb endpoint');
                    } else {
                        console.error('getcrumb endpoint failed', gcRes.status, gcText && gcText.slice ? gcText.slice(0, 200) : gcText);
                    }
                } catch (gcErr) {
                    console.error('getcrumb fetch failed', gcErr);
                }
            } else {
                crumb = crumbMatch[1];
            }

            // If we didn't get a crumb from the page or getcrumb endpoint, try yahoo-finance2 as a fallback
            if (!crumb) {
                console.warn('Failed to obtain crumb from Yahoo; falling back to yahoo-finance2 library');
                try {
                    const yfOptions = await yahooFinance.options(symbol, { date: date ? Number(date) : undefined });
                    return res.json(yfOptions);
                } catch (yfErr) {
                    console.error('yahoo-finance2 fallback failed', yfErr);
                    return res.status(502).json({ error: 'Failed to obtain data from Yahoo (all methods failed)', details: String(yfErr) });
                }
            }

            // Unescape common escapes
            crumb = crumb.replace(/\\u002F/g, '/');

            const urlWithCrumb = url + (url.includes('?') ? '&' : '?') + `crumb=${encodeURIComponent(crumb)}`;
            const headersWithCookie = { ...headers };
            if (cookieHeader) headersWithCookie['Cookie'] = cookieHeader;

            const retryRes = await fetch(urlWithCrumb, { headers: headersWithCookie });
            const retryText = await retryRes.text();
            if (!retryRes.ok) {
                console.error('Retry upstream error', retryRes.status, retryText);
                return res.status(retryRes.status).json({ error: `Upstream returned ${retryRes.status}`, body: retryText });
            }
            try {
                const data2 = JSON.parse(retryText);
                return res.json(data2);
            } catch (parseErr) {
                console.error('Failed to parse retry upstream JSON', parseErr, retryText.slice(0, 200));
                return res.status(502).json({ error: 'Invalid JSON from upstream (retry)' });
            }
        }

        if (!upstream.ok) {
            console.error('Upstream error', upstream.status, text);
            return res.status(upstream.status).json({ error: `Upstream returned ${upstream.status}`, body: text });
        }

        let data;
        try {
            data = JSON.parse(text);
        } catch (parseErr) {
            console.error('Failed to parse upstream JSON', parseErr, text.slice(0, 200));
            return res.status(502).json({ error: 'Invalid JSON from upstream' });
        }
        res.json(data);
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: 'Failed to fetch options data' });
    }
});

const port = process.env.PORT || 5178;
app.listen(port, () => console.log(`Options proxy listening on http://localhost:${port}`));
