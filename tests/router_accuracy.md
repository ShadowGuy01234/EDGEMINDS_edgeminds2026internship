# SLM Intent Router Accuracy Report

- **Total Queries tested**: 20
- **Passed**: 20/20
- **Accuracy Score**: 100.0%
- **Required Gate**: >= 85.0% (17/20 passed)
- **Status**: PASSED

## Test Results Table

| Query | Expected Tool | Got Tool | Routed By | Keywords | Status | Latency |
|---|---|---|---|---|---|---|
| What files import the auth module? | `graph` | `graph` | slm | `['auth']` | **PASS** | 3100ms |
| Find the JWT decode function | `vector` | `vector` | slm | `['JWT', 'decode']` | **PASS** | 3131ms |
| Where is rate limiting handled and what depends on it? | `hybrid` | `hybrid` | slm | `['rate limiting', 'dependencies']` | **PASS** | 3084ms |
| Show me the database connection module | `vector` | `vector` | slm | `['database', 'connection', 'module']` | **PASS** | 3273ms |
| What breaks if I change the middleware? | `hybrid` | `hybrid` | slm | `['middleware', 'change']` | **PASS** | 3133ms |
| Find the class UserProfile in user routes | `vector` | `vector` | slm | `['UserProfile']` | **PASS** | 3134ms |
| What imports session.py in the database directory? | `graph` | `graph` | slm | `['session', 'import', 'database']` | **PASS** | 3220ms |
| Where is verification code generated? | `vector` | `vector` | slm | `['verification', 'code', 'generation']` | **PASS** | 3209ms |
| Who depends on config module? | `graph` | `graph` | slm | `['config']` | **PASS** | 3102ms |
| Find API key authentication middleware | `vector` | `vector` | slm | `['API', 'key', 'authentication', 'middleware']` | **PASS** | 3194ms |
| Which files depend on helper.py? | `graph` | `graph` | slm | `['helper.py']` | **PASS** | 3094ms |
| Find the get_status function inside status.py | `vector` | `vector` | slm | `['get_status', 'status']` | **PASS** | 3195ms |
| Where is jwt_middleware and who uses it? | `hybrid` | `hybrid` | slm | `['jwt_middleware']` | **PASS** | 3230ms |
| What dependencies does database session have? | `graph` | `graph` | slm | `['database', 'session']` | **PASS** | 3190ms |
| Locate the class AuthMiddleware | `vector` | `vector` | slm | `['AuthMiddleware']` | **PASS** | 3174ms |
| Is there a custom exception handler for API errors? | `vector` | `vector` | slm | `['custom', 'exception', 'handler']` | **PASS** | 3209ms |
| Show dependencies of user.py | `graph` | `graph` | slm | `['user.py']` | **PASS** | 3276ms |
| List files importing main.py | `graph` | `graph` | slm | `['main.py']` | **PASS** | 3141ms |
| What depends on the email handler and where is it located? | `hybrid` | `hybrid` | slm | `['email handler']` | **PASS** | 3171ms |
| Where does the router get initialized? | `vector` | `vector` | slm | `['initialize', 'startup', 'initiation']` | **PASS** | 3200ms |
