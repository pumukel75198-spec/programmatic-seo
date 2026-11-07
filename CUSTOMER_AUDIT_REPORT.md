# Customer Audit Report

Generated: 2026-11-07 15:05 UTC

## Summary

| Product type | Checked | OK | Auto-healed | Failed |
| --- | ---: | ---: | ---: | ---: |
| APIs | 0 | 0/0 OK | 0 | 0 |
| Alternatives | 0 | 0/0 OK | 0 | 0 |
| Workflows | 3 | 2/3 OK | 2 | 1 |

- `npm run build`: OK
- git commit & push: OK

## Remaining issues

### api:api-ai-image-generator
- api_client.py does not mention the API title

### api:aws-rekognition-api
- requests.http: does not use the endpoint host 'rekognition.us-west-2.amazonaws.com'

### api:aws-ses-api
- requests.http: does not use the endpoint host 'email.us-east-1.amazonaws.com'

### api:aws-transcribe-api
- requests.http: does not use the endpoint host 'transcribe.us-east-1.amazonaws.com'

### api:braintree-payments-api
- api_client.py does not implement the endpoint host 'api.braintreegateway.com'
- requests.http: does not use the endpoint host 'api.braintreegateway.com'

### api:clerk-authentication-api
- api_client.py does not mention the API title

### api:deepgram-speech-api
- API sandbox failed: ing...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
ERROR:root:Max attempts reached. Request failed.
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-sao43qee/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-sao43qee/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: DeepgramResponse(status='success', data={'ok': True}) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:google-sheets-api
- requests.http: does not use the endpoint host 'sheets.googleapis.com'

### api:hubspot-crm-api
- requests.http: does not use the endpoint host 'api.hubapi.com'

### api:ibm-cloud-object-storage-api
- API sandbox failed: RNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-4le3gqpy/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-4le3gqpy/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: ApiResponse(status_code=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.002s

FAILED (failures=2)


### api:ibm-watson-assistant-api
- API sandbox failed:  Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
WARNING:root:HTTP Error 500: server error. Retrying...
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-176obli8/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-176obli8/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: WatsonAssistantResponse(status_code=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:microsoft-azure-cognitive-services-api
- API sandbox failed: unittest failed:

F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-6s1dcopw/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-6s1dcopw/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: CognitiveServiceResponse(status_code=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:microsoft-graph-api
- API sandbox failed: unittest failed:

F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-0qlnzsrb/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-0qlnzsrb/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: GraphAPIResponse(status_code=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:mongodb-atlas-api
- API sandbox failed: RNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-fogasq21/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-fogasq21/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: ApiResponse(status_code=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:neon-postgres-api
- test_mock.py: does not use the endpoint host 'neon.tech'

### api:pinecone-vector-api
- api_client.py does not mention the API title

### api:plaid-financial-api
- API sandbox failed:  500: server error. Retrying in 16 seconds...
WARNING:api_client:HTTPError 500: server error. Retrying in 32 seconds...
ERROR:api_client:Max retries exceeded.
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-czsifmyg/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-czsifmyg/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: ApiResponse(status='success', data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:planetscale-database-api
- test_mock.py: does not use the endpoint host 'planetscale.com'

### api:sendinblue-email-api
- api_client.py does not implement the endpoint host 'api.sendinblue.com'
- requests.http: does not use the endpoint host 'api.sendinblue.com'

### api:sendinblue-sms-api
- api_client.py does not implement the endpoint host 'api.sendinblue.com'
- requests.http: does not use the endpoint host 'api.sendinblue.com'

### api:shopify-admin-api
- requests.http: does not use the endpoint host '{shop}.myshopify.com'

### api:squarespace-api
- API sandbox failed: unittest failed:

F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-oxd7_cfy/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-oxd7_cfy/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: ApiResponse(status_code=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:stability-ai-image-api
- api_client.py does not mention the API title
- API sandbox failed: NING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-m8deditd/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-m8deditd/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: ApiResponse(status='success', data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:twilio-messaging-api
- requests.http: does not use the endpoint host 'api.twilio.com'

### api:upstash-redis-api
- API sandbox failed: unittest failed:

F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-jn6e77n3/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-jn6e77n3/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: RedisResponse(status='success', data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:vercel-blob-api
- API sandbox failed: .
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-nee9wewp/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-nee9wewp/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: BlobResponse(status=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### workflow:postgres-backup-reporting
- workflow kit file 'mock_data.json' is <= 100 bytes

