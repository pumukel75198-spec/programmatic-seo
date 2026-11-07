# Customer Audit Report

Generated: 2026-11-07 14:15 UTC

## Summary

| Product type | Checked | OK | Auto-healed | Failed |
| --- | ---: | ---: | ---: | ---: |
| APIs | 106 | 74/106 OK | 24 | 32 |
| Alternatives | 113 | 113/113 OK | 0 | 0 |
| Workflows | 86 | 75/86 OK | 0 | 11 |

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
- API kit file 'requests.http' is <= 100 bytes

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
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-5t1k_7l9/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-5t1k_7l9/test_mock.py", line 76, in test_successful_call_and_auth_header
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
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-wmjf4mt7/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-wmjf4mt7/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: ApiResponse(status_code=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

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
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-09a8qc5z/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-09a8qc5z/test_mock.py", line 76, in test_successful_call_and_auth_header
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
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-nsaj77cr/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-nsaj77cr/test_mock.py", line 76, in test_successful_call_and_auth_header
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
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-5yh0ypcp/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-5yh0ypcp/test_mock.py", line 76, in test_successful_call_and_auth_header
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
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-466ogvls/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-466ogvls/test_mock.py", line 76, in test_successful_call_and_auth_header
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
- API kit file 'requests.http' is <= 100 bytes

### api:plaid-financial-api
- API kit file 'requests.http' is <= 100 bytes
- API sandbox failed:  500: server error. Retrying in 16 seconds...
WARNING:api_client:HTTPError 500: server error. Retrying in 32 seconds...
ERROR:api_client:Max retries exceeded.
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-n6cy3u65/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-n6cy3u65/test_mock.py", line 76, in test_successful_call_and_auth_header
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
- API kit file 'requests.http' is <= 100 bytes

### api:sendinblue-sms-api
- api_client.py does not implement the endpoint host 'api.sendinblue.com'
- requests.http: does not use the endpoint host 'api.sendinblue.com'
- API kit file 'requests.http' is <= 100 bytes

### api:sentry-performance-api
- API kit file 'requests.http' is <= 100 bytes

### api:shopify-admin-api
- requests.http: does not use the endpoint host '{shop}.myshopify.com'
- API kit file 'requests.http' is <= 100 bytes

### api:squarespace-api
- API sandbox failed: unittest failed:

F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-wnr_0tus/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-wnr_0tus/test_mock.py", line 76, in test_successful_call_and_auth_header
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
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-0ndgd04_/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-0ndgd04_/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: ApiResponse(status='success', data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:telegram-bot-api
- API kit file 'requests.http' is <= 100 bytes

### api:tibber-api
- API kit file 'requests.http' is <= 100 bytes

### api:tinkr-api
- API kit file 'requests.http' is <= 100 bytes

### api:together-ai-api
- API kit file 'requests.http' is <= 100 bytes

### api:twilio-messaging-api
- requests.http: does not use the endpoint host 'api.twilio.com'

### api:twitch-helix-api
- API kit file 'requests.http' is <= 100 bytes

### api:upstash-redis-api
- API sandbox failed: unittest failed:

F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-qrgdphsh/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-qrgdphsh/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: RedisResponse(status='success', data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=2)


### api:vercel-blob-api
- API kit file 'requests.http' is <= 100 bytes
- API sandbox failed: .
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
WARNING:root:HTTPError 500: server error. Retrying...
F.F
======================================================================
FAIL: test_http_error_is_handled (test_mock.ApiClientTest.test_http_error_is_handled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-c604j9m_/test_mock.py", line 103, in test_http_error_is_handled
    self.assertTrue(result is None or isinstance(result, (dict, list, str)))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true

======================================================================
FAIL: test_successful_call_and_auth_header (test_mock.ApiClientTest.test_successful_call_and_auth_header)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-api-c604j9m_/test_mock.py", line 76, in test_successful_call_and_auth_header
    self.assertIsInstance(result, dict)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: BlobResponse(status=200, data={'ok': True}, error=None) is not an instance of <class 'dict'>

----------------------------------------------------------------------
Ran 3 tests in 0.002s

FAILED (failures=2)


### workflow:ai-image-generation-pipeline
- workflow.py --dry-run failed: Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-dy2fskct/workflow.py", line 181, in <module>
    main()
    ~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-dy2fskct/workflow.py", line 173, in main
    run_workflow()
    ~~~~~~~~~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-dy2fskct/workflow.py", line 129, in run_workflow
    manifest = upload_to_vercel_blob(images)
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-dy2fskct/workflow.py", line 125, in upload_to_vercel_blob
    manifest.append(response_data.get('url'))
                    ^^^^^^^^^^^^^^^^^
AttributeError: 'list' object has no attribute 'get'

### workflow:auth0-sso-provisioning
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
- step 3: 'what you need to do' actions missing
- step 3: checklist missing
- step 3: expected result missing
- step 3: links missing
- step 4: technical_explanation too short (0 < 250 chars)
- step 4: 'what you need to do' actions missing
- step 4: checklist missing
- step 4: expected result missing

### workflow:bank-transaction-enrichment
- workflow.py --dry-run failed: Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-yop39jvo/workflow.py", line 207, in <module>
    main()
    ~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-yop39jvo/workflow.py", line 199, in main
    run_workflow()
    ~~~~~~~~~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-yop39jvo/workflow.py", line 114, in run_workflow
    categorized_merchants = categorize_merchants(transactions)
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-yop39jvo/workflow.py", line 110, in categorize_merchants
    category = json.loads(response.read().decode('utf-8')).get('choices', [{}])[0].get('message', {}).get('content', '')
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'list' object has no attribute 'get'

### workflow:content-similarity-audit
- workflow kit file 'requests.http' is <= 100 bytes
- workflow.py --dry-run failed: Loaded 3 articles.
{'id': '1', 'text': 'This is the first article.'}

Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-77t54hj7/workflow.py", line 183, in <module>
    main()
    ~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-77t54hj7/workflow.py", line 175, in main
    run_workflow()
    ~~~~~~~~~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-77t54hj7/workflow.py", line 103, in run_workflow
    embeddings = embed_articles(articles)
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-77t54hj7/workflow.py", line 101, in embed_articles
    return response_data.get('embeddings', [])  # Use .get() to avoid KeyError
           ^^^^^^^^^^^^^^^^^
AttributeError: 'list' object has no attribute 'get'

### workflow:feature-flag-rollout
- workflow kit file 'mock_data.json' is <= 100 bytes
- workflow kit file 'requests.http' is <= 100 bytes

### workflow:hybrid-search-product-catalog
- workflow kit file 'requests.http' is <= 100 bytes

### workflow:llm-evaluation-benchmark
- workflow.py --dry-run failed: Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-ppq0v50x/workflow.py", line 195, in <module>
    main()
    ~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-ppq0v50x/workflow.py", line 187, in main
    run_workflow()
    ~~~~~~~~~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-ppq0v50x/workflow.py", line 98, in run_workflow
    openai_responses = run_openai_baseline(prompts)
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-ppq0v50x/workflow.py", line 95, in run_openai_baseline
    responses.append(result.get('choices', [{}])[0].get('message', {}).get('content', ''))
                     ^^^^^^^^^^
AttributeError: 'list' object has no attribute 'get'

### workflow:mongodb-data-pipeline
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
- step 3: 'what you need to do' actions missing
- step 3: checklist missing
- step 3: expected result missing
- step 3: links missing
- step 4: technical_explanation too short (0 < 250 chars)
- step 4: 'what you need to do' actions missing
- step 4: checklist missing
- step 4: expected result missing

### workflow:notion-task-sync
- workflow.py --dry-run failed: Traceback (most recent call last):
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-84409r0a/workflow.py", line 208, in <module>
    main()
    ~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-84409r0a/workflow.py", line 200, in main
    run_workflow()
    ~~~~~~~~~~~~^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-84409r0a/workflow.py", line 118, in run_workflow
    sync_tasks_with_asana(open_tasks)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/private/var/folders/q9/0ynj5p4d53gdzjpwn35lsgx00000gn/T/fm-audit-wf-84409r0a/workflow.py", line 90, in sync_tasks_with_asana
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

