# SLM Intent Router Accuracy Report

- **Total Queries tested**: 20
- **Passed**: 20/20
- **Accuracy Score**: 100.0%
- **Required Gate**: >= 85.0% (17/20 passed)
- **Status**: PASSED

## Test Results Table

| Query | Expected Tool | Got Tool | Routed By | Keywords | Status | Latency |
|---|---|---|---|---|---|---|
| What files import the auth module? | `graph` | `graph` | slm | `['auth']` | **PASS** | 9575ms |
| Find the JWT decode function | `vector` | `vector` | slm | `['JWT', 'decode']` | **PASS** | 10310ms |
| Where is rate limiting handled and what depends on it? | `hybrid` | `hybrid` | slm | `['rate limiting']` | **PASS** | 9750ms |
| Show me the database connection module | `vector` | `vector` | slm | `['database', 'connection']` | **PASS** | 10335ms |
| What breaks if I change the middleware? | `hybrid` | `hybrid` | slm | `['middleware']` | **PASS** | 10085ms |
| Find the class UserProfile in user routes | `vector` | `vector` | slm | `['UserProfile', 'user routes']` | **PASS** | 11157ms |
| What imports session.py in the database directory? | `graph` | `graph` | slm | `['session', 'import', 'database']` | **PASS** | 9434ms |
| Where is verification code generated? | `vector` | `vector` | slm | `['verification']` | **PASS** | 10261ms |
| Who depends on config module? | `graph` | `graph` | slm | `['config']` | **PASS** | 9637ms |
| Find API key authentication middleware | `vector` | `vector` | slm | `['API key', 'authentication', 'middleware']` | **PASS** | 10583ms |
| Which files depend on helper.py? | `graph` | `graph` | slm | `['helper.py']` | **PASS** | 11501ms |
| Find the get_status function inside status.py | `vector` | `vector` | slm | `['get_status', 'status']` | **PASS** | 9886ms |
| Where is jwt_middleware and who uses it? | `hybrid` | `hybrid` | slm | `['jwt_middleware']` | **PASS** | 10017ms |
| What dependencies does database session have? | `graph` | `graph` | slm | `['database', 'session']` | **PASS** | 10675ms |
| Locate the class AuthMiddleware | `vector` | `vector` | slm | `['AuthMiddleware']` | **PASS** | 10272ms |
| Is there a custom exception handler for API errors? | `vector` | `vector` | slm | `['custom', 'exception']` | **PASS** | 10517ms |
| Show dependencies of user.py | `graph` | `graph` | slm | `['user.py']` | **PASS** | 10098ms |
| List files importing main.py | `graph` | `graph` | slm | `['main.py']` | **PASS** | 11148ms |
| What depends on the email handler and where is it located? | `hybrid` | `hybrid` | slm | `['email']` | **PASS** | 11255ms |
| Where does the router get initialized? | `vector` | `vector` | slm | `['initialize']` | **PASS** | 11230ms |
