#!/usr/bin/env python3
"""FlowMatrix Implementation Kit – Social Listening & Sentiment Spike Pipeline

Run with --dry-run to execute against mock_data.json (no real API keys needed).
All code uses the Python standard library only.
"""
import argparse
import json
import os
import sys
import urllib.request
from unittest import mock

MOCK_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_data.json")


def _mock_urlopen(mock_responses):
    class _Resp:
        def __init__(self, payload, status=200):
            self._payload = payload
            self.status = status

        def read(self, amount=-1):
            return self._payload if amount is None or amount < 0 else self._payload[:amount]

        def getcode(self):
            return self.status

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _open(request, *args, **kwargs):
        url = getattr(request, "full_url", None) or str(request)
        for key, payload in mock_responses.items():
            if key in url:
                body = (
                    payload.encode("utf-8")
                    if isinstance(payload, str)
                    else json.dumps(payload).encode("utf-8")
                )
                return _Resp(body)
        return _Resp(b"{}")

    return _open


def run_workflow():
    import json
    import urllib.request
    import urllib.parse

    def fetch_mentions():
        url = 'https://api.twitter.com/2/tweets/search/recent'
        query = {'query': 'your_brand_name'}
        headers = {'Authorization': 'Bearer YOUR_X_API_TOKEN'}
        request_url = f'{url}?{urllib.parse.urlencode(query)}'
        req = urllib.request.Request(request_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            return [item['text'] for item in data['data']]

    mentions = fetch_mentions()

    import json
    import urllib.request

    def analyze_sentiment(mentions):
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {'Authorization': 'Bearer YOUR_OPENAI_API_KEY', 'Content-Type': 'application/json'}
        records = []
        for mention in mentions:
            prompt = f'Analyze the sentiment of the following text: {mention}'
            data = json.dumps({'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': prompt}]})
            req = urllib.request.Request(url, data.encode('utf-8'), headers)
            with urllib.request.urlopen(req) as response:
                content = json.loads(response.read())['choices'][0]['message']['content']
                sentiment = float(content)
                records.append({'text': mention, 'sentiment': sentiment})
        return records

    analyzed = analyze_sentiment(mentions)

    from collections import Counter

    def cluster_topics(analyzed):
        keywords = Counter()
        for record in analyzed:
            words = record['text'].split()
            keywords.update(words)
        return keywords.most_common(10)

    clusters = cluster_topics(analyzed)

    import json
    import urllib.request


    def persist_trends(clusters):
        url = 'https://YOUR_SUPABASE_URL/rest/v1/your_table_name'
        headers = {
            'apikey': 'YOUR_SUPABASE_KEY',
            'Authorization': 'Bearer YOUR_SUPABASE_KEY',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        for keyword, count in clusters:
            data = json.dumps({'keyword': keyword, 'count': count})
            req = urllib.request.Request(url, data.encode('utf-8'), headers)
            with urllib.request.urlopen(req) as response:
                if response.status not in (200, 201, 204):
                    raise Exception('Failed to upsert data')

    persist_trends(clusters)

    import json
    import urllib.request
    import statistics


    def alert_on_spikes(analyzed):
        sentiments = [record['sentiment'] for record in analyzed]
        mean = statistics.mean(sentiments)
        stdev = statistics.stdev(sentiments)
        threshold = 2.0  # Define z-score threshold for spikes
        for sentiment in sentiments:
            z_score = (sentiment - mean) / stdev
            if z_score >= threshold:
                send_alert(sentiment)


    def send_alert(sentiment):
        url = 'YOUR_SLACK_WEBHOOK_URL'
        data = json.dumps({'text': f'Sentiment spike detected: {sentiment}'})
        req = urllib.request.Request(url, data.encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                raise Exception('Failed to send alert')

    alert_on_spikes(analyzed)


def main():
    parser = argparse.ArgumentParser(description="Social Listening & Sentiment Spike Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Run against mock_data.json")
    args = parser.parse_args()
    if args.dry_run:
        with open(MOCK_DATA, encoding="utf-8") as fh:
            mock_responses = json.load(fh)
        with mock.patch("urllib.request.urlopen", side_effect=_mock_urlopen(mock_responses)):
            run_workflow()
    else:
        run_workflow()


if __name__ == "__main__":
    main()
