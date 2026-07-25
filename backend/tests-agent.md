# Antigravity AI - API Test Creation Guidelines

Whenever you are asked to develop tests for this API, strictly follow the instructions, tools, and standards below.

## 1. Technology Stack and Tools
* **Main Framework:** FastAPI (Python 3.11+)
* **Testing Tool:** Pytest + httpx (AsyncClient) + pytest-asyncio
* **Supporting Tools:** Use mocks whenever necessary to isolate the database and permissions.

## 2. Test Writing Standard
* **Structure:** Use the AAA (Arrange, Act, Assert) pattern.

* **Naming Convention:** Test files must end with `_test.py` and be located in the `/tests` folder.

## 3. Required Test Cases per Endpoint
For any generated endpoint, you must create scenarios for:
1. **Success (Happy Path):** Status 200, 201, or 204 with the correct payload.

2. **Validation Error (Bad Request):** Status 422/400 if required fields are missing or invalid data is present.

3. **Unauthorized:** Status 401 if the endpoint requires authentication and the token is not sent/is not valid.

4. **Not Found:** Status 404 for non-existent IDs.

*In short: Always create tests covering both successful flows and the main error scenarios.*

## 4. Pattern for `conftest.py` and Fixtures
Whenever tasks require the repetitive creation of authenticated models or clients, use Pytest fixtures according to the pattern below:

```python
    import pytest
    from httpx import AsyncClient
    from main import app # Or the path to your FastAPI app

    @pytest.fixture
    def manager_user():

    return User(
    email="manager@example.com",
    password="hashed_password_here",
    profile=Profiles.MANAGER,

    )

    # Helper to provide an already authenticated asynchronous HTTP client
    @pytest.fixture
    async def authenticated_client(manager_user):

    async with AsyncClient(app=app, base_url="http://test") as client:

    # Injects the mock authentication header or Generated for the manager_user

    client.headers.update({"Authorization": "Bearer mock_token_manager"})

    yield client
```

## 5. Observations
1. Whenever a repository to be tested uses custom exceptions, in the test use an isinstance() to verify if the exception thrown is the expected one.

2. Whenever a repository to be tested uses services, mock the service in the test.
3. To perform the tests, run the command `make test /folder-to-be-tested`.
4. When writing code, make sure it is formatted according to the Ruff standard in pyproject.com (commands: make ruff-check, make ruff-format, make ruff-fix).