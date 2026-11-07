# Customer Audit Report

Generated: 2026-11-07 10:04 UTC

## Summary

| Product type | Checked | OK | Auto-healed | Failed |
| --- | ---: | ---: | ---: | ---: |
| APIs | 106 | 38/106 OK | 12 | 68 |
| Alternatives | 113 | 113/113 OK | 38 | 0 |
| Workflows | 86 | 69/86 OK | 0 | 17 |

- `npm run build`: OK
- git commit & push: OK

## Remaining issues

### api:ably-realtime-api
- API sandbox failed: unittest failed:

..E
======================================================================
ERROR: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-1xgukdik/test_mock.py", line 53, in test_successful_call_and_auth_header
    result = api_client.request_json('https://rest.ably.io/time', **kwargs)
TypeError: request_json() missing 1 required positional argument: 'config'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:airtable-api
- requests.http: does not use the endpoint host 'api.airtable.com'

### api:aiven-kafka-api
- API sandbox failed: unittest failed:

WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
ERROR:root:Max retries exceeded
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-hqo8v_bc/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-hqo8v_bc/api_client.py", line 50, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:api-ai-image-generator
- api_client.py does not mention the API title
- API sandbox failed: unittest failed:

..E
======================================================================
ERROR: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-wp4qewa5/test_mock.py", line 53, in test_successful_call_and_auth_header
    result = api_client.request_json('https://api.deepai.org/api/text2img', **kwargs)
TypeError: request_json() missing 1 required positional argument: 'data'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:asana-api
- API sandbox failed: unittest failed:

WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
ERROR:root:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-75xtahtt/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-75xtahtt/api_client.py", line 67, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.002s

FAILED (errors=1)


### api:asana-automation-api
- API sandbox failed: unittest failed:

WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
ERROR:root:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-igrq3k5t/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-igrq3k5t/api_client.py", line 70, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:aws-lambda-api
- API sandbox failed: unittest failed:

..E
======================================================================
ERROR: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-xyxbu9d5/test_mock.py", line 53, in test_successful_call_and_auth_header
    result = api_client.request_json('https://lambda.us-east-1.amazonaws.com', **kwargs)
TypeError: request_json() missing 1 required positional argument: 'uri'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:aws-polly-api
- API sandbox failed: unittest failed:

..E
======================================================================
ERROR: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-mnomvrrl/test_mock.py", line 53, in test_successful_call_and_auth_header
    result = api_client.request_json('https://polly.us-east-1.amazonaws.com', **kwargs)
TypeError: request_json() missing 1 required positional argument: 'uri'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:aws-rekognition-api
- requests.http: does not use the endpoint host 'rekognition.us-west-2.amazonaws.com'
- API sandbox failed: unittest failed:

..E
======================================================================
ERROR: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-gm10l_zr/test_mock.py", line 53, in test_successful_call_and_auth_header
    result = api_client.request_json('https://rekognition.us-west-2.amazonaws.com', **kwargs)
TypeError: request_json() missing 1 required positional argument: 'url'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:aws-s3-api
- API sandbox failed: unittest failed:

..E
======================================================================
ERROR: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-_a6tv6og/test_mock.py", line 53, in test_successful_call_and_auth_header
    result = api_client.request_json('https://s3.amazonaws.com', **kwargs)
TypeError: request_json() missing 1 required positional argument: 'uri'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:aws-ses-api
- requests.http: does not use the endpoint host 'email.us-east-1.amazonaws.com'
- API sandbox failed: unittest failed:

..E
======================================================================
ERROR: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-tmuuo489/test_mock.py", line 53, in test_successful_call_and_auth_header
    result = api_client.request_json('https://email.us-east-1.amazonaws.com', **kwargs)
TypeError: request_json() missing 1 required positional argument: 'url'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:aws-transcribe-api
- requests.http: does not use the endpoint host 'transcribe.us-east-1.amazonaws.com'
- API sandbox failed: unittest failed:

..E
======================================================================
ERROR: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-pm7m34mx/test_mock.py", line 53, in test_successful_call_and_auth_header
    result = api_client.request_json('https://transcribe.us-east-1.amazonaws.com', **kwargs)
TypeError: request_json() missing 1 required positional argument: 'url'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:braintree-payments-api
- api_client.py does not implement the endpoint host 'api.braintreegateway.com'
- requests.http: does not use the endpoint host 'api.braintreegateway.com'

### api:clerk-authentication-api
- api_client.py does not mention the API title
- API kit file 'requests.http' is <= 100 bytes

### api:convertkit-api
- api_client.py contains a generic placeholder domain

### api:deepgram-speech-api
- API sandbox failed: ying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
ERROR:root:Max attempts reached. Request failed.
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-zqvedcco/test_mock.py", line 78, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-zqvedcco/test_mock.py", line 54, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: DeepgramResponse(status='success', data={'ok': True}) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:discord-bot-api
- API sandbox failed: api_client.py --dry-run failed:
usage: api_client.py [-h] channel_id message_content
api_client.py: error: the following arguments are required: channel_id, message_content

### api:finnhub-stock-api
- API sandbox failed: api_client.py --dry-run failed:
usage: api_client.py [-h] symbol
api_client.py: error: the following arguments are required: symbol

### api:github-copilot-api
- api_client.py does not implement the endpoint host 'api.github.com'
- requests.http: does not use the endpoint host 'api.github.com'
- API kit file 'requests.http' is <= 100 bytes

### api:google-gemini-api
- api_client.py contains a generic placeholder domain

### api:google-sheets-api
- requests.http: does not use the endpoint host 'sheets.googleapis.com'

### api:hubspot-crm-api
- requests.http: does not use the endpoint host 'api.hubapi.com'

### api:ibm-cloud-object-storage-api
- API sandbox failed: unittest failed:

..E
======================================================================
ERROR: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-0rqnbgyr/test_mock.py", line 53, in test_successful_call_and_auth_header
    result = api_client.request_json('https://s3.us.cloud-object-storage.appdomain.cloud', **kwargs)
TypeError: request_json() missing 1 required positional argument: 'url'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:ibm-watson-assistant-api
- requests.http: does not use the endpoint host 'api.us-south.assistant.watson.cloud.ibm.com'
- API sandbox failed: P Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-5r9llxl8/test_mock.py", line 78, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-5r9llxl8/test_mock.py", line 54, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: WatsonAssistantResponse(status_code=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:ibm-watson-text-to-speech-api
- api_client.py does not implement the endpoint host 'api.us-south.text-to-speech.watson.cloud.ibm.com'
- requests.http: does not use the endpoint host 'api.us-south.text-to-speech.watson.cloud.ibm.com'

### api:jira-rest-api
- requests.http: does not use the endpoint host '{your-domain}.atlassian.net'

### api:klaviyo-api
- api_client.py contains a generic placeholder domain

### api:launchdarkly-feature-api
- API sandbox failed: unittest failed:

WARNING:root:HTTPError 500: Retrying in 1 seconds...
WARNING:root:HTTPError 500: Retrying in 2 seconds...
WARNING:root:HTTPError 500: Retrying in 4 seconds...
WARNING:root:HTTPError 500: Retrying in 8 seconds...
WARNING:root:HTTPError 500: Retrying in 16 seconds...
ERROR:root:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-c91e169y/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-c91e169y/api_client.py", line 64, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:linear-graphql-api
- api_client.py does not implement the endpoint host 'api.linear.app'
- requests.http: does not use the endpoint host 'api.linear.app'

### api:microsoft-azure-cognitive-services-api
- API sandbox failed: unittest failed:

..F
======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-k7wl0uda/test_mock.py", line 54, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: CognitiveServiceResponse(status_code=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=1)


### api:microsoft-graph-api
- api_client.py contains a generic placeholder domain
- API sandbox failed: unittest failed:

F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-orv3z59a/test_mock.py", line 78, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-orv3z59a/test_mock.py", line 54, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: GraphAPIResponse(status_code=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:mongodb-atlas-api
- api_client.py does not implement the endpoint host 'data.mongodb-api.com'
- requests.http: does not use the endpoint host 'data.mongodb-api.com'
- API sandbox failed: ARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-vspg1eo8/test_mock.py", line 78, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-vspg1eo8/test_mock.py", line 54, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: ApiResponse(status_code=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.002s

FAILED (failures=2)


### api:neon-postgres-api
- test_mock.py: does not use the endpoint host 'neon.tech'

### api:notion-api-for-automation
- api_client.py does not implement the endpoint host 'api.notion.com'
- requests.http: does not use the endpoint host 'api.notion.com'

### api:notion-api-for-automation-v2
- api_client.py does not implement the endpoint host 'api.notion.com'
- requests.http: does not use the endpoint host 'api.notion.com'

### api:notion-forms-api
- api_client.py does not implement the endpoint host 'api.notion.com'
- requests.http: does not use the endpoint host 'api.notion.com'

### api:openai-embeddings-api
- API sandbox failed: unittest failed:

..E
======================================================================
ERROR: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-jrcem0bw/test_mock.py", line 53, in test_successful_call_and_auth_header
    result = api_client.request_json('https://api.openai.com/v1/embeddings', **kwargs)
TypeError: request_json() missing 1 required positional argument: 'method'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:openai-gpt-4-api
- API sandbox failed: unittest failed:

WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
ERROR:root:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-9ewq58tk/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-9ewq58tk/api_client.py", line 48, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:paypal-payments-api
- api_client.py does not implement the endpoint host 'api.paypal.com'
- requests.http: does not use the endpoint host 'api.paypal.com'

### api:pdf-co-api
- api_client.py does not implement the endpoint host 'api.pdf.co'
- api_client.py contains a generic placeholder domain
- requests.http: does not use the endpoint host 'api.pdf.co'

### api:pinecone-vector-api
- api_client.py does not mention the API title
- API kit file 'requests.http' is <= 100 bytes
- API sandbox failed: unittest failed:

..E
======================================================================
ERROR: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-8xzpzxej/test_mock.py", line 53, in test_successful_call_and_auth_header
    result = api_client.request_json('https://docs.pinecone.io', **kwargs)
TypeError: request_json() missing 1 required positional argument: 'endpoint'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:plaid-financial-api
- api_client.py does not implement the endpoint host 'production.plaid.com'
- requests.http: does not use the endpoint host 'production.plaid.com'
- API kit file 'requests.http' is <= 100 bytes
- API sandbox failed: r 500: server error. Retrying in 16 seconds...
WARNING:api_client:HTTPError 500: server error. Retrying in 32 seconds...
ERROR:api_client:Max retries exceeded.
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-_72fwlg2/test_mock.py", line 78, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-_72fwlg2/test_mock.py", line 54, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: ApiResponse(status='success', data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.002s

FAILED (failures=2)


### api:planetscale-database-api
- test_mock.py: does not use the endpoint host 'planetscale.com'

### api:salesforce-rest-api
- API sandbox failed: unittest failed:

WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
ERROR:root:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-9oexzyb2/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-9oexzyb2/api_client.py", line 58, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.002s

FAILED (errors=1)


### api:sendgrid-email-api
- api_client.py contains a generic placeholder domain

### api:sendinblue-email-api
- api_client.py does not implement the endpoint host 'api.sendinblue.com'
- api_client.py contains a generic placeholder domain
- requests.http: does not use the endpoint host 'api.sendinblue.com'
- API kit file 'requests.http' is <= 100 bytes

### api:sendinblue-sms-api
- api_client.py does not implement the endpoint host 'api.sendinblue.com'
- requests.http: does not use the endpoint host 'api.sendinblue.com'
- API kit file 'requests.http' is <= 100 bytes

### api:sentry-error-api
- API sandbox failed: unittest failed:

WARNING:api_client:HTTPError 500: server error. Retrying...
WARNING:api_client:HTTPError 500: server error. Retrying...
WARNING:api_client:HTTPError 500: server error. Retrying...
WARNING:api_client:HTTPError 500: server error. Retrying...
WARNING:api_client:HTTPError 500: server error. Retrying...
ERROR:api_client:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-dft5uzy_/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-dft5uzy_/api_client.py", line 64, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.002s

FAILED (errors=1)


### api:sentry-performance-api
- API kit file 'requests.http' is <= 100 bytes
- API sandbox failed: unittest failed:

WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
ERROR:root:Max retries exceeded
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-ciqh60qu/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-ciqh60qu/api_client.py", line 50, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.002s

FAILED (errors=1)


### api:shopify-admin-api
- requests.http: does not use the endpoint host '{shop}.myshopify.com'
- API kit file 'requests.http' is <= 100 bytes

### api:slack-web-api
- API sandbox failed: unittest failed:

WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
ERROR:root:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-bwgl1z71/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-bwgl1z71/api_client.py", line 61, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:squarespace-api
- API sandbox failed: unittest failed:

F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-ma1vit4v/test_mock.py", line 78, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-ma1vit4v/test_mock.py", line 54, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: ApiResponse(status_code=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:stability-ai-image-api
- API sandbox failed: RNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-io0pc2yz/test_mock.py", line 78, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-io0pc2yz/test_mock.py", line 54, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: ApiResponse(status='success', data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:supabase-database-api
- api_client.py contains a generic placeholder domain

### api:telegram-bot-api
- requests.http: does not use the endpoint host 'api.telegram.org'
- API kit file 'requests.http' is <= 100 bytes
- API sandbox failed: unittest failed:

WARNING:root:HTTPError 500: server error. Retrying in 2 seconds...
WARNING:root:HTTPError 500: server error. Retrying in 4 seconds...
WARNING:root:HTTPError 500: server error. Retrying in 8 seconds...
WARNING:root:HTTPError 500: server error. Retrying in 16 seconds...
WARNING:root:HTTPError 500: server error. Retrying in 32 seconds...
ERROR:root:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-xkcd10rc/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-xkcd10rc/api_client.py", line 53, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:tibber-api
- api_client.py does not implement the endpoint host 'api.tibber.com'
- requests.http: does not use the endpoint host 'api.tibber.com'
- API kit file 'requests.http' is <= 100 bytes
- API sandbox failed: unittest failed:

WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
ERROR:root:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-f7y7uafn/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-f7y7uafn/api_client.py", line 47, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:tinkr-api
- api_client.py does not implement the endpoint host 'api.tink.com'
- requests.http: does not use the endpoint host 'api.tink.com'
- API kit file 'requests.http' is <= 100 bytes

### api:together-ai-api
- API sandbox failed: unittest failed:

WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
ERROR:root:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-9e4nmtsk/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-9e4nmtsk/api_client.py", line 58, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:twilio-conversations-api
- api_client.py does not implement the endpoint host 'conversations.twilio.com'
- requests.http: does not use the endpoint host 'conversations.twilio.com'
- API sandbox failed: unittest failed:

WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
ERROR:root:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-ve6tydul/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-ve6tydul/api_client.py", line 64, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:twilio-messaging-api
- requests.http: does not use the endpoint host 'api.twilio.com'
- API kit file 'requests.http' is <= 100 bytes
- API sandbox failed: unittest failed:

WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
ERROR:root:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-cxbmfekj/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-cxbmfekj/api_client.py", line 58, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:twilio-video-api
- API sandbox failed: unittest failed:

WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
ERROR:root:Max retries exceeded
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-1bwa2fha/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-1bwa2fha/api_client.py", line 65, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:twitch-analytics-api
- api_client.py does not implement the endpoint host 'api.twitch.tv'
- requests.http: does not use the endpoint host 'api.twitch.tv'

### api:twitch-api-kraken
- api_client.py does not implement the endpoint host 'api.twitch.tv'
- requests.http: does not use the endpoint host 'api.twitch.tv'

### api:twitch-helix-api
- api_client.py does not implement the endpoint host 'api.twitch.tv'
- requests.http: does not use the endpoint host 'api.twitch.tv'
- API kit file 'requests.http' is <= 100 bytes

### api:upstash-redis-api
- API sandbox failed: unittest failed:

F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-hcjei9wm/test_mock.py", line 78, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-hcjei9wm/test_mock.py", line 54, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: RedisResponse(status='success', data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:vercel-blob-api
- API kit file 'requests.http' is <= 100 bytes
- API sandbox failed: unittest failed:

..E
======================================================================
ERROR: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-lp38y28y/test_mock.py", line 53, in test_successful_call_and_auth_header
    result = api_client.request_json('https://blob.vercel-storage.com', **kwargs)
TypeError: request_json() missing 1 required positional argument: 'endpoint'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### api:yelp-fusion-api
- API sandbox failed: unittest failed:

WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
ERROR:root:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-qcyt37cj/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-qcyt37cj/api_client.py", line 49, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.002s

FAILED (errors=1)


### api:zendesk-support-api
- api_client.py does not implement the endpoint host '{subdomain}.zendesk.com'
- requests.http: does not use the endpoint host '{subdomain}.zendesk.com'
- API sandbox failed: unittest failed:

WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
ERROR:root:Max retries exceeded.
E..
======================================================================
ERROR: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-z0ld1pwc/test_mock.py", line 75, in test_http_error_is_handled
    result = api_client.request_json("https://api.example.com/v1/test")
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-z0ld1pwc/api_client.py", line 70, in request_json
    sys.exit(1)
    ~~~~~~~~^^^
SystemExit: 1

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (errors=1)


### workflow:ai-image-generation-pipeline
- workflow.py --dry-run failed: Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-zvkkcmpv/workflow.py", line 181, in <module>
    main()
    ~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-zvkkcmpv/workflow.py", line 173, in main
    run_workflow()
    ~~~~~~~~~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-zvkkcmpv/workflow.py", line 129, in run_workflow
    manifest = upload_to_vercel_blob(images)
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-zvkkcmpv/workflow.py", line 125, in upload_to_vercel_blob
    manifest.append(response_data.get('url'))
                    ^^^^^^^^^^^^^^^^^
AttributeError: 'list' object has no attribute 'get'

### workflow:auth0-sso-provisioning
- workflow kit file 'mock_data.json' is <= 100 bytes
- workflow kit file 'requests.http' is <= 100 bytes
- step 1: technical_explanation too short (0 < 250 chars)
- step 1: 'what you need to do' actions missing
- step 1: checklist missing
- step 1: expected result missing
- step 1: links missing
- step 2: technical_explanation too short (0 < 250 chars)
- step 2: 'what you need to do' actions missing
- step 2: checklist missing
- step 2: expected result missing
- step 2: links missing
- step 3: technical_explanation too short (0 < 250 chars)
- step 3: 'what you need to do' actions missing
- step 3: checklist missing
- step 3: expected result missing
- step 3: links missing
- step 4: technical_explanation too short (0 < 250 chars)
- step 4: 'what you need to do' actions missing
- step 4: checklist missing

### workflow:bank-transaction-enrichment
- workflow.py --dry-run failed: Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-ew14qscv/workflow.py", line 207, in <module>
    main()
    ~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-ew14qscv/workflow.py", line 199, in main
    run_workflow()
    ~~~~~~~~~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-ew14qscv/workflow.py", line 114, in run_workflow
    categorized_merchants = categorize_merchants(transactions)
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-ew14qscv/workflow.py", line 110, in categorize_merchants
    category = json.loads(response.read().decode('utf-8')).get('choices', [{}])[0].get('message', {}).get('content', '')
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'list' object has no attribute 'get'

### workflow:content-localization-pipeline
- workflow kit file 'requests.http' is <= 100 bytes

### workflow:content-similarity-audit
- workflow kit file 'requests.http' is <= 100 bytes
- workflow.py --dry-run failed: Loaded 3 articles.
{'id': '1', 'text': 'This is the first article.'}

Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-cx47q92o/workflow.py", line 183, in <module>
    main()
    ~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-cx47q92o/workflow.py", line 175, in main
    run_workflow()
    ~~~~~~~~~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-cx47q92o/workflow.py", line 103, in run_workflow
    embeddings = embed_articles(articles)
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-cx47q92o/workflow.py", line 101, in embed_articles
    return response_data.get('embeddings', [])  # Use .get() to avoid KeyError
           ^^^^^^^^^^^^^^^^^
AttributeError: 'list' object has no attribute 'get'

### workflow:crypto-portfolio-tracker
- workflow kit file 'requests.http' is <= 100 bytes

### workflow:feature-flag-rollout
- workflow kit file 'mock_data.json' is <= 100 bytes
- workflow kit file 'requests.http' is <= 100 bytes

### workflow:hybrid-search-product-catalog
- workflow kit file 'requests.http' is <= 100 bytes

### workflow:jira-rest-notion-api-for-automation-automation-pipeline
- workflow kit file 'requests.http' is <= 100 bytes

### workflow:llm-evaluation-benchmark
- workflow.py --dry-run failed: Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-7j7mk1pt/workflow.py", line 195, in <module>
    main()
    ~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-7j7mk1pt/workflow.py", line 187, in main
    run_workflow()
    ~~~~~~~~~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-7j7mk1pt/workflow.py", line 98, in run_workflow
    openai_responses = run_openai_baseline(prompts)
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-7j7mk1pt/workflow.py", line 95, in run_openai_baseline
    responses.append(result.get('choices', [{}])[0].get('message', {}).get('content', ''))
                     ^^^^^^^^^^
AttributeError: 'list' object has no attribute 'get'

### workflow:mongodb-data-pipeline
- workflow kit file 'mock_data.json' is <= 100 bytes
- workflow kit file 'requests.http' is <= 100 bytes
- step 1: technical_explanation too short (0 < 250 chars)
- step 1: 'what you need to do' actions missing
- step 1: checklist missing
- step 1: expected result missing
- step 1: links missing
- step 2: technical_explanation too short (0 < 250 chars)
- step 2: 'what you need to do' actions missing
- step 2: checklist missing
- step 2: expected result missing
- step 2: links missing
- step 3: technical_explanation too short (0 < 250 chars)
- step 3: 'what you need to do' actions missing
- step 3: checklist missing
- step 3: expected result missing
- step 3: links missing
- step 4: technical_explanation too short (0 < 250 chars)
- step 4: 'what you need to do' actions missing
- step 4: checklist missing

### workflow:notion-task-sync
- workflow.py --dry-run failed: Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-ezjk0kdi/workflow.py", line 208, in <module>
    main()
    ~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-ezjk0kdi/workflow.py", line 200, in main
    run_workflow()
    ~~~~~~~~~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-ezjk0kdi/workflow.py", line 118, in run_workflow
    sync_tasks_with_asana(open_tasks)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-ezjk0kdi/workflow.py", line 90, in sync_tasks_with_asana
    task_id = task.get('external_id')
              ^^^^^^^^
AttributeError: 'str' object has no attribute 'get'

### workflow:postgres-backup-reporting
- workflow kit file 'mock_data.json' is <= 100 bytes

### workflow:salesforce-rest-weatherapi-automation-pipeline
- workflow kit file 'requests.http' is <= 100 bytes

### workflow:serverless-job-scheduler
- workflow kit file 'mock_data.json' is <= 100 bytes
- step 1: technical_explanation too short (0 < 250 chars)
- step 1: 'what you need to do' actions missing
- step 1: checklist missing
- step 1: expected result missing
- step 1: links missing
- step 2: technical_explanation too short (0 < 250 chars)
- step 2: 'what you need to do' actions missing
- step 2: checklist missing
- step 2: expected result missing
- step 2: links missing
- step 3: technical_explanation too short (0 < 250 chars)
- step 3: code_snippet has fewer than 8 lines
- step 3: 'what you need to do' actions missing
- step 3: checklist missing
- step 3: expected result missing
- step 3: links missing
- step 4: technical_explanation too short (0 < 250 chars)
- step 4: 'what you need to do' actions missing
- step 4: checklist missing

### workflow:store-locator-geocoding
- workflow kit file 'requests.http' is <= 100 bytes

### workflow:watson-assistant-helpdesk
- workflow kit file 'requests.http' is <= 100 bytes

