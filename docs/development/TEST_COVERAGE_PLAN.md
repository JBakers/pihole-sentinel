# Test Coverage Improvement Plan

**Version:** 0.12.0-beta.7  
**Date:** 2025-12-07  
**Target:** 95%+ coverage (from unknown baseline)

---

## Current Test Suite Status

### Existing Tests (86 test cases, 1423 LOC)

| File | Tests | Lines | Coverage Area |
|------|-------|-------|---|
| `test_validation.py` | 24 | 329 | Input validation, injection prevention |
| `test_api_handlers.py` | 26 | 372 | Pi-hole API calls, response handling |
| `test_dhcp_parsing.py` | 26 | 364 | DHCP config parsing, state detection |
| `test_vip_detection.py` | 16 | 304 | VIP location, MAC extraction, ARP |

### Current Coverage Summary

✅ **Well Tested:**
- Input validation (IP, subnet, interface, port, username)
- Injection attack prevention
- DHCP configuration parsing
- VIP/MAC detection logic
- Pi-hole API authentication

⚠️ **Partially Tested:**
- API endpoints (some handlers tested, edge cases missing)
- Connection error handling
- HTTP session management

❌ **Not Tested (Identified Gaps):**
- Error handling (NEW: custom exceptions, handlers)
- Async operations in monitor.py
- HTTP timeout scenarios
- Database operations (SQLite)
- Notification sending (Telegram, Discord, Pushover, etc.)
- Configuration file operations
- Version checking
- Update detection
- Snooze functionality
- Template rendering
- Rate limiting

---

## Gap Analysis & Improvements

### Gap 1: ERROR HANDLING (New - 6 Exception Classes)

**Current Status:** ❌ Not tested

**Missing Tests:**
- [ ] `PiholeSentinelException` base exception
- [ ] `ConfigurationError` (400 responses)
- [ ] `AuthenticationError` (403 responses)
- [ ] `RateLimitError` (429 responses)
- [ ] `NotificationError` (service-specific failures)
- [ ] `DatabaseError` (500 responses)
- [ ] Global exception handlers
- [ ] Error response format validation
- [ ] Logging of all errors (no silent failures)

**Test Cases to Add:**
```python
# tests/test_error_handling.py

class TestExceptionHierarchy:
    def test_pihole_exception_base()
    def test_configuration_error_400()
    def test_authentication_error_403()
    def test_rate_limit_error_429()
    def test_notification_error_service()
    def test_database_error_500()

class TestExceptionHandlers:
    def test_pihole_exception_response_format()
    def test_http_exception_standardization()
    def test_generic_exception_fallback()
    def test_error_logging_enabled()
    def test_no_sensitive_data_in_errors()
```

**Effort:** 4 hours  
**Priority:** 🔴 HIGH (Critical new functionality)

---

### Gap 2: ASYNC OPERATIONS IN MONITOR.PY

**Current Status:** ⚠️ Minimal testing

**Missing Tests:**
- [ ] `lifespan()` context manager (startup/shutdown)
- [ ] `init_db()` database initialization
- [ ] `monitor_loop()` main monitoring loop
- [ ] `send_notification()` async notification sending
- [ ] `check_and_send_reminders()` reminder logic
- [ ] HTTP session management
- [ ] Connection timeouts
- [ ] Retry logic

**Test Cases to Add:**
```python
# tests/test_async_operations.py

class TestMonitorLifecycle:
    @pytest.mark.asyncio
    async def test_lifespan_startup()
    
    @pytest.mark.asyncio
    async def test_lifespan_shutdown()
    
    @pytest.mark.asyncio
    async def test_database_initialization()

class TestNotificationSending:
    @pytest.mark.asyncio
    async def test_send_notification_telegram()
    
    @pytest.mark.asyncio
    async def test_send_notification_discord()
    
    @pytest.mark.asyncio
    async def test_notification_timeout()
    
    @pytest.mark.asyncio
    async def test_notification_retry_on_failure()

class TestHTTPSessionManagement:
    @pytest.mark.asyncio
    async def test_session_creation()
    
    @pytest.mark.asyncio
    async def test_session_reuse()
    
    @pytest.mark.asyncio
    async def test_session_cleanup_on_shutdown()
```

**Effort:** 8 hours  
**Priority:** 🟠 HIGH (Core functionality)

---

### Gap 3: API ENDPOINT RESPONSES (monitor.py)

**Current Status:** ❌ Not tested (NEW endpoints with Pydantic models)

**Missing Tests:**
- [ ] `GET /api/version`
- [ ] `GET /api/check-update`
- [ ] `GET /api/status` (StatusResponse model)
- [ ] `GET /api/history`
- [ ] `GET /api/events` (EventsResponse model)
- [ ] `GET /api/notifications/settings`
- [ ] `POST /api/notifications/settings`
- [ ] `POST /api/notifications/test`
- [ ] `POST /api/notifications/test-template`
- [ ] `GET /api/notifications/snooze`
- [ ] `POST /api/notifications/snooze`
- [ ] `DELETE /api/notifications/snooze`

**Test Cases to Add:**
```python
# tests/test_api_endpoints.py

class TestVersionEndpoint:
    def test_version_response_format()
    def test_version_file_not_found()
    def test_version_file_corrupted()

class TestStatusEndpoint:
    @pytest.mark.asyncio
    async def test_status_response_model_valid()
    
    @pytest.mark.asyncio
    async def test_status_missing_api_key()
    
    @pytest.mark.asyncio
    async def test_status_invalid_api_key()
    
    @pytest.mark.asyncio
    async def test_status_database_error()

class TestNotificationEndpoints:
    @pytest.mark.asyncio
    async def test_get_settings_masked_secrets()
    
    @pytest.mark.asyncio
    async def test_save_settings_partial_update()
    
    @pytest.mark.asyncio
    async def test_test_notification_rate_limit()
    
    @pytest.mark.asyncio
    async def test_snooze_valid_duration()
    
    @pytest.mark.asyncio
    async def test_snooze_max_duration_exceeded()
```

**Effort:** 6 hours  
**Priority:** 🟠 MEDIUM (API needs validation)

---

### Gap 4: CONFIGURATION EDGE CASES

**Current Status:** ⚠️ Partial (validation tests exist)

**Missing Tests:**
- [ ] Missing environment variables
- [ ] Invalid JSON in config files
- [ ] Corrupted notification settings
- [ ] File permission errors
- [ ] Path traversal attempts in file operations
- [ ] Config merging with masked values
- [ ] Settings serialization

**Test Cases to Add:**
```python
# tests/test_configuration_edge_cases.py

class TestConfigurationLoading:
    def test_missing_required_env_vars()
    def test_invalid_env_var_types()
    def test_config_file_not_found()
    def test_config_file_corrupted_json()

class TestSettingsPersistence:
    def test_save_settings_valid_json()
    def test_save_settings_permission_denied()
    def test_load_settings_empty_file()
    def test_merge_settings_with_masked_values()
```

**Effort:** 3 hours  
**Priority:** 🟡 MEDIUM (Edge cases)

---

### Gap 5: DATABASE OPERATIONS

**Current Status:** ❌ Not tested

**Missing Tests:**
- [ ] Database initialization
- [ ] Query execution errors
- [ ] Connection handling
- [ ] Data persistence
- [ ] Cleanup/retention policies
- [ ] Concurrent access

**Test Cases to Add:**
```python
# tests/test_database_operations.py

class TestDatabaseOperations:
    @pytest.mark.asyncio
    async def test_database_create_tables()
    
    @pytest.mark.asyncio
    async def test_insert_status_record()
    
    @pytest.mark.asyncio
    async def test_query_history()
    
    @pytest.mark.asyncio
    async def test_database_error_handling()
```

**Effort:** 4 hours  
**Priority:** 🟡 MEDIUM (Storage)

---

### Gap 6: SECURITY & INJECTION PREVENTION

**Current Status:** ✅ Good (validation tests comprehensive)

**Additional Tests Needed:**
- [ ] SQL injection attempts in database queries
- [ ] XSS attempts in notification templates
- [ ] API key validation robustness
- [ ] Rate limiting enforcement
- [ ] CORS policy enforcement

**Test Cases to Add:**
```python
# tests/test_security_hardening.py

class TestSQLInjectionPrevention:
    @pytest.mark.asyncio
    async def test_parameterized_queries()

class TestAPIKeySecurity:
    @pytest.mark.asyncio
    async def test_missing_api_key_rejected()
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected()
    
    @pytest.mark.asyncio
    async def test_valid_api_key_accepted()

class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_threshold()
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset_after_window()
```

**Effort:** 3 hours  
**Priority:** 🔴 HIGH (Security)

---

## Implementation Roadmap

### Phase 1: Critical (Week 1)
| Task | Hours | Status |
|------|-------|--------|
| Error handling tests | 4 | TODO ▪️ |
| API endpoint tests | 6 | TODO ▪️ |
| Security hardening | 3 | TODO ▪️ |
| **Phase 1 Total** | **13h** | |

### Phase 2: Important (Week 2)
| Task | Hours | Status |
|------|-------|--------|
| Async operations tests | 8 | TODO ▪️ |
| Configuration edge cases | 3 | TODO ▪️ |
| Database operations | 4 | TODO ▪️ |
| **Phase 2 Total** | **15h** | |

### Phase 3: Polish (Week 3)
| Task | Hours | Status |
|------|-------|--------|
| Coverage analysis & gaps | 2 | TODO ▪️ |
| Refactor test organization | 2 | TODO ▪️ |
| Documentation updates | 2 | TODO ▪️ |
| **Phase 3 Total** | **6h** | |

**Grand Total: 34 hours** → ~95%+ coverage target

---

## Coverage Targets by Module

| Module | Current | Target | Gap |
|--------|---------|--------|-----|
| `dashboard/monitor.py` | ~40% | 85% | 45% |
| `setup.py` | ~60% | 90% | 30% |
| `tests/` | N/A | 100% | - |
| **Overall** | ~50% | 95% | 45% |

---

## Test Infrastructure

### Tools & Frameworks
- `pytest` - Test runner
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `unittest.mock` - Mocking/patching
- `aioresponses` - Mock aiohttp responses
- `pytest-timeout` - Timeout protection

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_error_handling.py -v

# Run with coverage
pytest --cov=dashboard --cov=setup --cov-report=html

# Run specific test class
pytest tests/test_async_operations.py::TestNotificationSending -v

# Run with markers
pytest -m asyncio        # Only async tests
pytest -m "not slow"     # Skip slow tests
```

### Continuous Integration

```yaml
# .github/workflows/test.yml
- Run tests on every push
- Generate coverage reports
- Upload to codecov
- Fail if coverage < 95%
```

---

## Success Metrics

✅ **Coverage Goals:**
- Overall: 95%+
- `dashboard/monitor.py`: 85%+
- `setup.py`: 90%+
- All files: >80%

✅ **Test Quality:**
- All async operations tested
- All error paths covered
- No untested exceptions
- All API endpoints validated
- All edge cases covered

✅ **Documentation:**
- Test cases documented
- Expected behaviors clear
- Edge cases explained
- Mock strategies documented

---

## Next Steps

1. **Create test files** for each gap:
   - `tests/test_error_handling.py`
   - `tests/test_async_operations.py`
   - `tests/test_api_endpoints.py`
   - `tests/test_configuration_edge_cases.py`
   - `tests/test_database_operations.py`
   - `tests/test_security_hardening.py`

2. **Add test utilities:**
   - Fixtures for async operations
   - Mock repositories
   - Sample data generators

3. **Configure CI/CD:**
   - Coverage threshold enforcement
   - Automated test reporting
   - Coverage trend tracking

4. **Review & iterate:**
   - Run coverage analysis
   - Identify remaining gaps
   - Update tests as needed

---

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Python Testing Best Practices](https://docs.pytest.org/en/7.1.x/goodpractices.html)

