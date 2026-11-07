# Customer Audit Report

Generated: 2026-11-07 14:27 UTC

## Summary

| Product type | Checked | OK | Auto-healed | Failed |
| --- | ---: | ---: | ---: | ---: |
| APIs | 106 | 80/106 OK | 6 | 26 |
| Alternatives | 113 | 113/113 OK | 0 | 0 |
| Workflows | 86 | 80/86 OK | 5 | 6 |

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


### workflow:auth0-sso-provisioning
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
- step 4: expected result missing
- step 4: links missing

### workflow:bank-transaction-enrichment
- workflow.py --dry-run failed: Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-aq1ndhpf/workflow.py", line 207, in <module>
    main()
    ~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-aq1ndhpf/workflow.py", line 199, in main
    run_workflow()
    ~~~~~~~~~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-aq1ndhpf/workflow.py", line 155, in run_workflow
    summary = summarize_spending(categorized_merchants)
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-aq1ndhpf/workflow.py", line 149, in summarize_spending
    if category in spending_summary:
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: cannot use 'dict' as a dict key (unhashable type: 'dict')

### workflow:mongodb-data-pipeline
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
- step 4: expected result missing
- step 4: links missing

### workflow:notion-task-sync
- workflow.py --dry-run failed: Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-aj4j0mdr/workflow.py", line 208, in <module>
    main()
    ~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-aj4j0mdr/workflow.py", line 200, in main
    run_workflow()
    ~~~~~~~~~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-aj4j0mdr/workflow.py", line 118, in run_workflow
    sync_tasks_with_asana(open_tasks)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-aj4j0mdr/workflow.py", line 90, in sync_tasks_with_asana
    task_id = task.get('external_id')
              ^^^^^^^^
AttributeError: 'str' object has no attribute 'get'

### workflow:postgres-backup-reporting
- workflow kit file 'mock_data.json' is <= 100 bytes

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

