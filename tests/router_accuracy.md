# SLM Intent Router Accuracy Report

- **Total Queries tested**: 20
- **Passed**: 0/20
- **Accuracy Score**: 0.0%
- **Required Gate**: >= 85.0% (17/20 passed)
- **Status**: FAILED

## Test Results Table

| Query | Expected Tool | Got Tool | Routed By | Keywords | Status | Latency |
|---|---|---|---|---|---|---|
| What files import the auth module? | `graph` | `hybrid` | fallback | `['files', 'import', 'auth']` | **FAIL** | 4574ms |
| Find the JWT decode function | `vector` | `hybrid` | fallback | `['jwt', 'decode']` | **FAIL** | 4505ms |
| Where is rate limiting handled and what depends on it? | `hybrid` | `hybrid` | fallback | `['rate', 'limiting', 'handled', 'depends', 'on']` | **FAIL** | 4512ms |
| Show me the database connection module | `vector` | `hybrid` | fallback | `['database', 'connection']` | **FAIL** | 4466ms |
| What breaks if I change the middleware? | `hybrid` | `hybrid` | fallback | `['breaks', 'middleware']` | **FAIL** | 4490ms |
| Find the class UserProfile in user routes | `vector` | `hybrid` | fallback | `['userprofile', 'user', 'routes']` | **FAIL** | 4521ms |
| What imports session.py in the database directory? | `graph` | `hybrid` | fallback | `['imports', 'sessionpy', 'database']` | **FAIL** | 4472ms |
| Where is verification code generated? | `vector` | `hybrid` | fallback | `['verification', 'generated']` | **FAIL** | 4451ms |
| Who depends on config module? | `graph` | `hybrid` | fallback | `['depends', 'on', 'config']` | **FAIL** | 4546ms |
| Find API key authentication middleware | `vector` | `hybrid` | fallback | `['api', 'key', 'authentication', 'middleware']` | **FAIL** | 4461ms |
| Which files depend on helper.py? | `graph` | `hybrid` | fallback | `['files', 'depend', 'on', 'helperpy']` | **FAIL** | 4445ms |
| Find the get_status function inside status.py | `vector` | `hybrid` | fallback | `['get_status', 'inside', 'statuspy']` | **FAIL** | 4488ms |
| Where is jwt_middleware and who uses it? | `hybrid` | `hybrid` | fallback | `['jwt_middleware', 'uses']` | **FAIL** | 4536ms |
| What dependencies does database session have? | `graph` | `hybrid` | fallback | `['dependencies', 'database', 'session', 'have']` | **FAIL** | 4522ms |
| Locate the class AuthMiddleware | `vector` | `hybrid` | fallback | `['locate', 'authmiddleware']` | **FAIL** | 4579ms |
| Is there a custom exception handler for API errors? | `vector` | `hybrid` | fallback | `['there', 'custom', 'exception', 'for', 'api']` | **FAIL** | 4568ms |
| Show dependencies of user.py | `graph` | `hybrid` | fallback | `['dependencies', 'userpy']` | **FAIL** | 4480ms |
| List files importing main.py | `graph` | `hybrid` | fallback | `['list', 'files', 'importing', 'mainpy']` | **FAIL** | 4543ms |
| What depends on the email handler and where is it located? | `hybrid` | `hybrid` | fallback | `['depends', 'on', 'email', 'located']` | **FAIL** | 4498ms |
| Where does the router get initialized? | `vector` | `hybrid` | fallback | `['router', 'get', 'initialized']` | **FAIL** | 4552ms |
