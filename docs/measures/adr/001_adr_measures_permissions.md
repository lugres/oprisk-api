# Architecture Decision Record: Permission Enforcement Strategy, Measures

**Status:** Accepted  
**Date:** 2025-01-19  
**Decision Makers:** Development Team 
**Technical Area:** Security, Architecture, API Design

---

## Context

The Operational Risk Management (ORM) system requires a robust permission enforcement mechanism for the Measures module. Measures represent corrective/preventive actions with complex business rules governing who can perform which operations based on:

- User roles (Employee, Manager, Risk Officer)
- User relationships (responsible, creator, manager hierarchies)
- Object state (measure status: OPEN, IN_PROGRESS, PENDING_REVIEW, etc.)
- Participation context (who is involved with a specific measure)

The system has been designed using a **3-Layer Architecture**:
1. **Domain Layer** (`workflows.py`) - Pure business logic, framework-agnostic
2. **Application Layer** (`services.py`) - Orchestration, transaction management, business rule enforcement
3. **Interface Layer** (`views.py`, `serializers.py`) - HTTP concerns, data presentation

Two approaches were evaluated for implementing permission enforcement:

1. **Service-Layer Gateway Pattern** - All permission checks enforced in the Application Layer
2. **DRF-Native Permission Classes** - Permission checks using Django REST Framework's built-in permission system

---

## Decision

**We will implement the Service-Layer Gateway Pattern**, where all business rules and permission checks are enforced exclusively in the Application Layer (`services.py`), with complex permission logic extracted to pure functions in the Domain Layer (`workflows.py`).

The Interface Layer will only verify **authentication** (IsAuthenticated), delegating all authorization decisions to service functions.

---

## Approaches Considered

### Approach 1: Service-Layer Gateway Pattern (Selected)

**Architecture:**

```
┌─────────────────────────────────────────────────────┐
│ Interface Layer (views.py, serializers.py)         │
│ Responsibilities:                                   │
│ - HTTP request/response handling                    │
│ - Authentication check (IsAuthenticated only)       │
│ - Data serialization/deserialization                │
│ - Delegates to services for all business logic      │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ Application Layer (services.py)                     │
│ Responsibilities:                                   │
│ - Single enforcement gateway for ALL business rules │
│ - Transaction management                            │
│ - Orchestration of domain logic                     │
│ - Database operations                               │
│ - Calls domain functions for permission logic       │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ Domain Layer (workflows.py)                         │
│ Responsibilities:                                   │
│ - Pure business logic (framework-agnostic)          │
│ - Permission logic as pure boolean functions        │
│ - State machine transitions                         │
│ - No database access, no Django/DRF dependencies    │
└─────────────────────────────────────────────────────┘
```

**Implementation Example:**

```python
# workflows.py (Domain Layer)
def can_user_delete_measure(measure, user) -> bool:
    """Pure function: checks deletion permission."""
    is_creator_or_mgr = (
        measure.created_by and
        (user.id == measure.created_by.id or 
         (measure.created_by.manager and 
          user.id == measure.created_by.manager.id))
    )
    return measure.status.code == 'OPEN' and is_creator_or_mgr

def can_user_add_comment(measure, user) -> bool:
    """Pure function: checks comment permission."""
    is_responsible_party = (
        measure.responsible and 
        (user.id == measure.responsible.id or 
         (measure.responsible.manager and 
          user.id == measure.responsible.manager.id))
    )
    is_creator_party = (
        measure.created_by and 
        (user.id == measure.created_by.id or 
         (measure.created_by.manager and 
          user.id == measure.created_by.manager.id))
    )
    is_risk_officer = (user.role and user.role.name == "Risk Officer")
    
    return is_responsible_party or is_creator_party or is_risk_officer

# services.py (Application Layer)
@transaction.atomic
def delete_measure(*, measure: Measure, user: User):
    """Service enforces business rules via domain functions."""
    if not can_user_delete_measure(measure, user):
        raise MeasurePermissionError(
            "You do not have permission to delete this measure."
        )
    measure.delete()

@transaction.atomic
def add_comment(*, measure: Measure, user: User, comment: str) -> Measure:
    """Service enforces business rules via domain functions."""
    if not can_user_add_comment(measure, user):
        raise MeasurePermissionError(
            "You do not have permission to comment on this measure."
        )
    _append_to_notes(measure, user, "COMMENT", comment)
    measure.save(update_fields=["notes"])
    return measure

# views.py (Interface Layer)
class MeasureViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]  # Only authentication
    
    def destroy(self, request, *args, **kwargs):
        """View delegates to service."""
        measure = self.get_object()
        try:
            services.delete_measure(measure=measure, user=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except MeasurePermissionError as e:
            return Response({"error": str(e)}, status=403)
```

---

### Approach 2: DRF-Native Permission Classes (Not Selected)

**Architecture:**

```
┌─────────────────────────────────────────────────────┐
│ Interface Layer (views.py, permissions.py)          │
│ Responsibilities:                                   │
│ - HTTP request/response handling                    │
│ - Permission enforcement via DRF classes            │
│ - Database queries for permission checks            │
│ - Data serialization/deserialization                │
└────────────┬────────────────────────────────────────┘
             │
       ┌─────┴─────┐
       ▼           ▼
┌─────────────┐ ┌──────────────────────────────────┐
│ Permissions │ │ Application Layer (services.py)  │
│ (Interface) │ │ Responsibilities:                │
│ - Access    │ │ - Business logic enforcement     │
│   checks    │ │ - Transaction management         │
│ - DB queries│ │ - Orchestration                  │
└─────────────┘ └────────────┬─────────────────────┘
                              │
                              ▼
                   ┌──────────────────────────┐
                   │ Domain Layer             │
                   │ - State transitions only │
                   └──────────────────────────┘
```

**Implementation Example:**

```python
# permissions.py (Interface Layer)
class IsCreatorOrManagerForDelete(permissions.BasePermission):
    """DRF permission class with database access."""
    def has_object_permission(self, request, view, obj):
        if not obj.created_by:
            return False
        return (
            request.user == obj.created_by
            or request.user == obj.created_by.manager
        )

class IsMeasureParticipant(permissions.BasePermission):
    """DRF permission class with complex relationship checks."""
    def has_object_permission(self, request, view, obj):
        is_resp_or_mgr = obj.responsible and (
            request.user == obj.responsible
            or request.user == obj.responsible.manager
        )
        is_creator_or_mgr = obj.created_by and (
            request.user == obj.created_by
            or request.user == obj.created_by.manager
        )
        is_risk = request.user.role.name == "Risk Officer"
        return is_resp_or_mgr or is_creator_or_mgr or is_risk

# views.py (Interface Layer)
class MeasureViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        """Map actions to permission classes."""
        if self.action == "destroy":
            return [IsAuthenticated(), IsCreatorOrManagerForDelete()]
        if self.action == "add_comment":
            return [IsAuthenticated(), IsMeasureParticipant()]
        return [IsAuthenticated()]
    
    def destroy(self, request, *args, **kwargs):
        """DRF checks permissions before this runs."""
        measure = self.get_object()  # Permission checked here
        services.delete_measure(measure=measure, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
```

---

## Comparative Analysis

### 1. Architectural Purity

| Aspect | Service-Layer Gateway | DRF Permission Classes |
|--------|----------------------|------------------------|
| **Layer Separation** | ✅ Perfect - business logic isolated | ❌ Poor - business logic in interface layer |
| **Single Responsibility** | ✅ Each layer has one job | ❌ Mixed - interface does HTTP + business rules |
| **Dependency Direction** | ✅ Correct - interface depends on application | ⚠️ Inverted - permission classes query domain |
| **Framework Coupling** | ✅ Minimal - only in interface layer | ❌ High - business rules depend on DRF |

### 2. Maintainability

| Aspect | Service-Layer Gateway | DRF Permission Classes |
|--------|----------------------|------------------------|
| **Single Source of Truth** | ✅ All rules in services.py | ❌ Rules split between permissions & services |
| **Code Duplication** | ✅ None - rules defined once | ❌ High - logic duplicated across layers |
| **Change Impact** | ✅ Localized - change one place | ❌ Widespread - change multiple classes |
| **Rule Discovery** | ✅ Clear - look in services | ⚠️ Unclear - scattered across permissions |

### 3. Testability

| Aspect | Service-Layer Gateway | DRF Permission Classes |
|--------|----------------------|------------------------|
| **Unit Testing** | ✅ Pure functions, no mocking | ❌ Requires Django test framework |
| **Test Complexity** | ✅ Simple - test boolean functions | ❌ Complex - mock requests, views, objects |
| **Test Speed** | ✅ Fast - no database | ❌ Slow - database fixtures required |
| **Coverage** | ✅ Easy - test domain functions | ❌ Hard - must test permissions + services |

### 4. Performance

| Aspect | Service-Layer Gateway | DRF Permission Classes |
|--------|----------------------|------------------------|
| **Database Queries** | ✅ Optimized - single fetch in view | ❌ Redundant - permissions query, then services |
| **Permission Check Timing** | ⚠️ Later in request cycle | ✅ Earlier - fail fast |
| **Query Optimization** | ✅ Easy - control in get_queryset() | ⚠️ Hard - must coordinate with permissions |
| **Caching Strategy** | ✅ Simple - cache in view layer | ❌ Complex - cache across layers |

### 5. Developer Experience

| Aspect | Service-Layer Gateway | DRF Permission Classes |
|--------|----------------------|------------------------|
| **Learning Curve** | ⚠️ Requires understanding 3-layer pattern | ✅ Standard DRF - familiar to Django devs |
| **Documentation** | ⚠️ Custom - need to document pattern | ✅ Extensive DRF documentation available |
| **IDE Support** | ✅ Standard Python - full autocomplete | ✅ DRF support in major IDEs |
| **Debugging** | ✅ Clear flow - view → service → domain | ⚠️ Complex - permission check invisible |

### 6. Framework Independence

| Aspect | Service-Layer Gateway | DRF Permission Classes |
|--------|----------------------|------------------------|
| **Portability** | ✅ Business logic framework-agnostic | ❌ Tied to DRF permission system |
| **Framework Migration** | ✅ Easy - only change interface layer | ❌ Hard - rewrite all permissions |
| **Multiple Interfaces** | ✅ Reuse services for REST/GraphQL/CLI | ❌ Duplicate logic for each interface |
| **Technology Risk** | ✅ Low - own the business logic | ⚠️ Medium - depend on DRF evolution |

### 7. Security & Compliance

| Aspect | Service-Layer Gateway | DRF Permission Classes |
|--------|----------------------|------------------------|
| **Audit Trail** | ✅ Centralized logging in services | ⚠️ Fragmented - log in multiple places |
| **Rule Verification** | ✅ Single place to audit | ❌ Must audit permissions + services |
| **Compliance** | ✅ Clear - all rules documented in one layer | ⚠️ Unclear - rules scattered |
| **Security Review** | ✅ Focused - review services only | ❌ Broad - review permissions + services |

### 8. Scalability

| Aspect | Service-Layer Gateway | DRF Permission Classes |
|--------|----------------------|------------------------|
| **Complex Rules** | ✅ Natural - any logic in services | ⚠️ Awkward - forced into permission API |
| **Multi-object Rules** | ✅ Easy - services coordinate | ❌ Difficult - permissions limited to one object |
| **Rule Evolution** | ✅ Flexible - change services freely | ⚠️ Constrained - permission API limitations |
| **Integration** | ✅ Simple - services as API | ⚠️ Complex - permissions don't expose API |

---

## Detailed Rationale

### Why Service-Layer Gateway Was Selected

#### 1. **Architectural Consistency**

The system has been deliberately designed with a 3-layer architecture following Domain-Driven Design principles. This decision maintains that architectural vision:

- **Domain Layer** remains pure and framework-agnostic
- **Application Layer** serves as the single gateway for all business rules
- **Interface Layer** handles only HTTP concerns

Introducing DRF permission classes would violate this architecture by moving business logic into the interface layer, creating an inconsistent hybrid that undermines the benefits of both approaches.

#### 2. **Complex Permission Rules**

The Measures module has sophisticated permission rules that involve:

- **Multi-level relationships**: User → Manager → Responsible → Creator
- **State-dependent logic**: Different rules for different statuses
- **Participation context**: Complex "who is involved" calculations
- **Role-based access**: Dynamic role determination based on context

These rules are **too complex** for DRF's permission class API, which is designed for simpler object-level checks. Forcing them into `has_object_permission()` would result in:

- Convoluted, hard-to-read code
- Brittle implementation dependent on DRF internals
- Difficult debugging and maintenance

#### 3. **Single Source of Truth**

With the Service-Layer Gateway pattern, all business rules live in one place: `services.py` (calling pure functions in `workflows.py`). This provides:

- **One place to look** when understanding authorization rules
- **One place to change** when business rules evolve
- **One place to audit** for compliance and security reviews
- **One place to log** for security monitoring

With DRF permissions, rules would be split between:
- Permission classes (interface layer)
- Service functions (application layer)
- Domain functions (domain layer)

This fragmentation increases maintenance burden and risk of inconsistency.

#### 4. **Framework Independence**

The business logic in `services.py` and `workflows.py` has zero dependency on Django REST Framework:

```python
# This code could work with FastAPI, Flask, GraphQL, CLI, or any interface
def can_user_delete_measure(measure, user) -> bool:
    # Pure Python, no framework dependencies
    return measure.status.code == 'OPEN' and is_creator_or_mgr
```

This independence provides:

- **Technology flexibility**: Can switch to FastAPI, GraphQL, or other frameworks
- **Multiple interfaces**: Can expose same logic via REST API, CLI tools, background jobs
- **Reduced vendor lock-in**: Business rules don't depend on DRF's evolution
- **Easier migration**: If DRF is deprecated, only interface layer needs rewrite

#### 5. **Superior Testability**

Permission logic as pure functions enables:

```python
# Fast, simple unit test - no mocking, no database
def test_can_user_delete_measure():
    measure = Mock(status=Mock(code='OPEN'), created_by=Mock(id=1))
    user = Mock(id=1)
    assert can_user_delete_measure(measure, user) == True
```

With DRF permission classes, tests require:
- Django test framework setup
- Database fixtures
- Request and view mocking
- More complex test setup and teardown

Pure functions are:
- **Faster to test** (no database)
- **Easier to write** (no framework setup)
- **More reliable** (fewer moving parts)
- **Better coverage** (can test edge cases easily)

#### 6. **Reduced Database Query Redundancy**

With DRF permissions:
1. Permission class loads `measure.responsible`, `measure.created_by`, their managers
2. Service function loads the same data again
3. Result: 2x database queries for the same data

With Service-Layer Gateway:
1. View layer pre-fetches all needed relationships via `select_related()`
2. Service uses already-loaded data
3. Result: Optimal query performance

#### 7. **Clearer Request Flow**

Service-Layer Gateway provides a clear, linear flow:

```
Request → Authentication → View → Service → Domain → Database
                                    ↓
                            All rules enforced here
```

With DRF permissions, the flow is branched:

```
Request → Authentication → Permissions → View → Service → Domain
                              ↓                    ↓
                        Some rules here      Other rules here
```

The branched flow is harder to:
- Debug (permissions run before view code)
- Trace (need to check multiple places)
- Understand (rule enforcement is fragmented)

#### 8. **Better Alignment with Business Domain**

The system models real-world operational risk management processes. Permission rules are **business rules**, not technical concerns:

- "Only the creator or their manager can delete an open measure"
- "Participants (responsible, creator, managers, risk officers) can comment"
- "Only risk officers can complete a measure"

These are **domain concepts** that belong in the Application and Domain layers, not in the Interface layer which should only care about HTTP mechanics.

---

## Consequences

### Positive Consequences

1. **Clear Architectural Boundaries**: Each layer has a well-defined, single responsibility
2. **Maintainable Codebase**: Business rules centralized in one place
3. **Testable Logic**: Pure functions enable fast, simple unit tests
4. **Framework Flexibility**: Can switch frameworks or add new interfaces easily
5. **Optimized Performance**: No redundant database queries
6. **Clear Audit Trail**: All permission checks logged in one place
7. **Simplified Security Review**: All rules auditable in services layer
8. **Reduced Complexity**: No need to understand DRF permission internals

### Negative Consequences (Trade-offs Accepted)

1. **Non-Standard Pattern**: Diverges from typical DRF best practices
   - **Mitigation**: Comprehensive documentation of the pattern
   - **Justification**: Standard pattern insufficient for our complexity

2. **Learning Curve**: New team members must understand 3-layer architecture
   - **Mitigation**: Architecture Decision Records, code comments, onboarding docs
   - **Justification**: One-time learning cost vs. ongoing maintenance benefit

3. **Later Permission Checks**: Authorization happens after routing
   - **Impact**: Negligible - authentication still happens early
   - **Mitigation**: Proper logging of permission denials
   - **Justification**: Performance impact minimal, benefits outweigh cost

4. **Less Tool Integration**: DRF admin tools expect permission classes
   - **Impact**: OpenAPI docs won't auto-document permissions
   - **Mitigation**: Custom documentation in docstrings and API docs
   - **Justification**: Our API is for programmatic access, not browseable API

5. **View Tests Require Services**: Cannot test views in isolation
   - **Impact**: View tests are more integration-style
   - **Mitigation**: Service layer is well-tested independently
   - **Justification**: Integration tests provide better confidence anyway

---

## Implementation Guidelines

### 1. Domain Layer (workflows.py)

**Purpose**: Pure business logic, framework-agnostic

**Rules**:
- No Django/DRF imports
- No database access
- Pure boolean functions
- Accept simple types or domain objects as parameters
- Return boolean or raise domain exceptions

**Example**:
```python
def can_user_delete_measure(measure, user) -> bool:
    """
    Domain rule: Users can delete measures if:
    - Measure status is OPEN, AND
    - User is the creator OR creator's manager
    """
    is_creator_or_mgr = (
        measure.created_by and
        (user.id == measure.created_by.id or 
         (measure.created_by.manager and user.id == measure.created_by.manager.id))
    )
    return measure.status.code == 'OPEN' and is_creator_or_mgr
```

### 2. Application Layer (services.py)

**Purpose**: Enforce business rules, orchestrate operations

**Rules**:
- All functions use `@transaction.atomic`
- Call domain functions for permission logic
- Raise `MeasurePermissionError` for authorization failures
- Raise `MeasureTransitionError` for business logic violations
- Include logging for security events
- Return domain objects or None

**Example**:
```python
@transaction.atomic
def delete_measure(*, measure: Measure, user: User):
    """
    Delete a measure if user has permission.
    
    Raises:
        MeasurePermissionError: User lacks permission
    """
    if not can_user_delete_measure(measure, user):
        logger.warning(
            f"Delete permission denied: measure_id={measure.id}, user_id={user.id}",
            extra={"measure_id": measure.id, "user_id": user.id}
        )
        raise MeasurePermissionError(
            "You do not have permission to delete this measure."
        )
    
    logger.info(f"Measure {measure.id} deleted by user {user.id}")
    measure.delete()
```

### 3. Interface Layer (views.py)

**Purpose**: HTTP request/response handling only

**Rules**:
- Only `IsAuthenticated` in permission_classes
- Delegate all business logic to services
- Catch service exceptions and return appropriate HTTP status codes
- Use `MeasurePermissionError` → 403 Forbidden
- Use `MeasureTransitionError` → 400 Bad Request
- Log unexpected exceptions
- Document permissions in docstrings

**Example**:
```python
class MeasureViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing measures.
    
    Permissions (enforced in service layer):
    - destroy: Creator or their manager, status must be OPEN
    - add_comment: Participants (responsible, creator, managers, Risk Officer)
    """
    
    permission_classes = [IsAuthenticated]
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a measure.
        Permission: Creator or their manager (status: OPEN).
        """
        measure = self.get_object()
        
        try:
            services.delete_measure(measure=measure, user=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except MeasurePermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except MeasureTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
```

### 4. Exception Handling Pattern

**Consistent exception mapping**:

| Exception | HTTP Status | Use Case |
|-----------|-------------|----------|
| `MeasurePermissionError` | 403 Forbidden | User lacks authorization |
| `MeasureTransitionError` | 400 Bad Request | Invalid state transition |
| `ValidationError` (DRF) | 400 Bad Request | Invalid input data |
| `Measure.DoesNotExist` | 404 Not Found | Resource not found |
| `Exception` (unexpected) | 500 Internal Server Error | System errors (log for debugging) |

### 5. Logging Standards

**Security-relevant events must be logged**:

```python
# Permission denials
logger.warning(
    f"Permission denied: action={action}, measure_id={id}, user_id={user_id}",
    extra={
        "action": action,
        "measure_id": measure.id,
        "user_id": user.id,
        "measure_status": measure.status.code,
    }
)

# Successful privileged operations
logger.info(
    f"Measure {measure.id} deleted by user {user.id}",
    extra={"measure_id": measure.id, "user_id": user.id}
)
```

---

## Testing Strategy

### 1. Domain Layer Tests (Fast, Simple)

**Test pure boolean functions with mocked objects**:

```python
def test_can_user_delete_measure_as_creator():
    """Test creator can delete OPEN measure."""
    measure = Mock(
        status=Mock(code='OPEN'),
        created_by=Mock(id=1, manager=None)
    )
    user = Mock(id=1)
    
    assert can_user_delete_measure(measure, user) == True

def test_cannot_delete_in_progress_measure():
    """Test cannot delete non-OPEN measure."""
    measure = Mock(
        status=Mock(code='IN_PROGRESS'),
        created_by=Mock(id=1, manager=None)
    )
    user = Mock(id=1)
    
    assert can_user_delete_measure(measure, user) == False
```

**Benefits**: No database, no Django, extremely fast

### 2. Application Layer Tests (Service Tests)

**Test service functions with database fixtures**:

```python
def test_delete_measure_success(self):
    """Test successful measure deletion."""
    measure = Measure.objects.create(
        description="Test",
        created_by=self.user,
        status=self.status_open
    )
    
    services.delete_measure(measure=measure, user=self.user)
    
    # Verify measure deleted
    self.assertFalse(Measure.objects.filter(id=measure.id).exists())

def test_delete_measure_permission_denied(self):
    """Test deletion fails for unauthorized user."""
    measure = Measure.objects.create(
        description="Test",
        created_by=self.user,
        status=self.status_open
    )
    other_user = User.objects.create_user(email="other@test.com")
    
    with self.assertRaises(MeasurePermissionError):
        services.delete_measure(measure=measure, user=other_user)
```

### 3. Interface Layer Tests (API Tests)

**Test HTTP responses and status codes**:

```python
def test_delete_measure_as_creator_succeeds(self):
    """Test DELETE endpoint as creator."""
    self.client.force_authenticate(user=self.creator_user)
    url = measure_detail_url(self.measure_open.id)
    res = self.client.delete(url)
    
    self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
    self.assertFalse(Measure.objects.filter(id=self.measure_open.id).exists())

def test_delete_measure_as_other_user_fails(self):
    """Test DELETE endpoint as unauthorized user."""
    self.client.force_authenticate(user=self.other_user)
    url = measure_detail_url(self.measure_open.id)
    res = self.client.delete(url)
    
    # get_queryset filters out measure, so 404 before permission check
    self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
```

---

## Documentation Requirements

### 1. Code Documentation

**Every service function must document permissions**:

```python
@transaction.atomic
def delete_measure(*, measure: Measure, user: User):
    """
    Delete a measure if user has permission.
    
    Business Rules:
    - Measure status must be OPEN
    - User must be creator OR creator's manager
    
    Args:
        measure: The measure to delete
        user: User attempting deletion
        
    Raises:
        MeasurePermissionError: User lacks permission
        MeasureTransitionError: Measure status not OPEN
    """
```

### 2. API Documentation

**ViewSet docstrings must list all permission rules**:

```python
class MeasureViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing measures.
    
    All business rules enforced in service layer.
    
    Permissions:
    - list: Any authenticated user (filtered by access rules)
    - retrieve: Any authenticated user (filtered by access rules)
    - create: Manager or Risk Officer
    - update: Any authenticated user (field-level security in serializer)
    - destroy: Creator or their manager (status must be OPEN)
    - start_progress: Responsible user or their manager
    - submit_for_review: Responsible user or their manager
    - return_to_progress: Risk Officer
    - complete: Risk Officer
    - cancel: Risk Officer
    - add_comment: Participants (responsible, creator, managers, Risk Officer)
    - link_to_incident: Participants
    - unlink_from_incident: Participants
    """
```

### 3. Architecture Documentation

**This ADR serves as the primary architecture documentation**. Additionally:

- README.md explains the 3-layer pattern
- Developer onboarding includes architecture overview
- Code review guidelines enforce pattern adherence

---

## Migration Path (If Needed)

If future requirements necessitate switching to DRF permission classes:

1. **Low Risk**: Permission logic already extracted to pure functions in `workflows.py`
2. **Straightforward**: Create permission classes that call the same domain functions
3. **Incremental**: Can migrate one action at a time
4. **No Business Logic Changes**: Pure functions remain unchanged

**Example migration**:

```python
# Can create permission class wrapper around existing logic
class CanDeleteMeasure(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Reuse existing domain function
        return can_user_delete_measure(obj, request.user)
```

The domain logic remains pure and reusable.

---

## References

### Internal Documents
- `measures/workflows.py` - Domain layer implementation
- `measures/services.py` - Application layer implementation
- `measures/views.py` - Interface layer implementation
- Test suite: `measures/tests/test_api.py`

### External Resources
- Clean Architecture by Robert C. Martin
- Domain-Driven Design by Eric Evans
- Django REST Framework Documentation: https://www.django-rest-framework.org/
- Hexagonal Architecture (Ports and Adapters)

### Related ADRs
- ADR-001: 3-Layer Architecture Pattern (if exists)
- ADR-002: Service Layer Transaction Management (if exists)

---

## Review and Approval

**Decision Date**: 2025-01-19  
**Approved By**: Development Team  
**Review Date**: 2026-01-19 (12 months)

**Signatures**:
- Technical Lead: _______________________
- Senior Developer: _______________________
- Security Officer: _______________________

---

## Appendix A: Code Examples

### Complete Delete Operation Flow

**Domain Layer** (`workflows.py`):
```python
def can_user_delete_measure(measure, user) -> bool:
    """
    Pure domain logic for deletion permission.
    
    Business Rule:
    - Status must be OPEN
    - User must be creator OR creator's manager
    
    Args:
        measure: Measure object with status and created_by
        user: User object with id attribute
        
    Returns:
        bool: True if user can delete, False otherwise
    """
    # Check status requirement
    if measure.status.code != 'OPEN':
        return False
    
    # Check user relationship requirement
    if not measure.created_by:
        return False
    
    is_creator = user.id == measure.created_by.id
    is_creator_manager = (
        measure.created_by.manager and 
        user.id == measure.created_by.manager.id
    )
    
    return is_creator or is_creator_manager
```

**Application Layer** (`services.py`):
```python
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

@transaction.atomic
def delete_measure(*, measure: Measure, user: User):
    """
    Delete a measure, enforcing business rules.
    
    This is the single enforcement point for deletion rules.
    
    Args:
        measure: The measure to delete
        user: User attempting deletion
        
    Raises:
        MeasurePermissionError: User lacks permission to delete
        
    Business Rules (enforced via domain layer):
        - Measure status must be OPEN
        - User must be creator OR creator's manager
    """
    # Enforce permission via domain function
    if not can_user_delete_measure(measure, user):
        logger.warning(
            f"Delete permission denied: measure_id={measure.id}, user_id={user.id}",
            extra={
                "action": "delete_measure",
                "measure_id": measure.id,
                "user_id": user.id,
                "measure_status": measure.status.code,
                "is_creator": measure.created_by_id == user.id if measure.created_by else False,
            }
        )
        raise MeasurePermissionError(
            "You do not have permission to delete this measure."
        )
    
    # Log successful privileged operation
    logger.info(
        f"Measure {measure.id} deleted by user {user.id}",
        extra={"measure_id": measure.id, "user_id": user.id}
    )
    
    # Execute deletion
    measure.delete()
```

**Interface Layer** (`views.py`):
```python
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class MeasureViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing measures.
    
    Permissions (enforced in service layer):
    - destroy: Creator or their manager (status must be OPEN)
    """
    
    permission_classes = [IsAuthenticated]
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a measure.
        
        Permission: Creator or their manager.
        Validation: Status must be OPEN.
        
        Returns:
            204 No Content: Deletion successful
            400 Bad Request: Status not OPEN
            403 Forbidden: User lacks permission
            404 Not Found: Measure not found or not visible to user
        """
        measure = self.get_object()
        
        try:
            services.delete_measure(measure=measure, user=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except MeasurePermissionError as e:
            # User lacks authorization
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        except MeasureTransitionError as e:
            # Business rule violation (status not OPEN)
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
```

---

## Appendix B: Permission Rules Summary

### Complete Permission Matrix

| Action | Required Permission | Status Constraint | Enforced In |
|--------|---------------------|-------------------|-------------|
| **list** | Authenticated user | Any | `get_queryset()` |
| **retrieve** | Authenticated user | Any | `get_queryset()` |
| **create** | Manager OR Risk Officer | N/A (creates OPEN) | `services.create_measure()` |
| **update** | Authenticated user | Any | Serializer (field-level) |
| **destroy** | Creator OR Creator's Manager | Must be OPEN | `services.delete_measure()` |
| **start_progress** | Responsible OR Responsible's Manager | Must be OPEN | `services.start_progress()` |
| **submit_for_review** | Responsible OR Responsible's Manager | Must be IN_PROGRESS | `services.submit_for_review()` |
| **return_to_progress** | Risk Officer | Must be PENDING_REVIEW | `services.return_to_progress()` |
| **complete** | Risk Officer | Must be PENDING_REVIEW | `services.complete()` |
| **cancel** | Risk Officer | Must be IN_PROGRESS or PENDING_REVIEW | `services.cancel()` |
| **add_comment** | Participant* | Any non-terminal | `services.add_comment()` |
| **link_to_incident** | Participant* | Cannot be CANCELLED | `services.link_measure_to_incident()` |
| **unlink_from_incident** | Participant* | Any | `services.unlink_measure_from_incident()` |

*Participant = Responsible OR Responsible's Manager OR Creator OR Creator's Manager OR Risk Officer

---

## Appendix C: Comparison with Alternative Patterns

### Pattern Comparison Matrix

| Pattern | Layer Separation | Testability | Framework Coupling | Complexity | Recommended For |
|---------|------------------|-------------|-------------------|------------|-----------------|
| **Service-Layer Gateway** (Selected) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Complex business rules, enterprise systems |
| **DRF Permission Classes** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | Simple CRUD APIs, standard Django projects |
| **Django Guardian** (object permissions) | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ACL-based systems, CMS platforms |
| **RBAC with Permissions Table** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Multi-tenant apps, configurable permissions |
| **Policy-Based (ABAC)** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Highly dynamic rules, government systems |

---

## Appendix D: Risk Mitigation Strategies

### Risk 1: Team Unfamiliarity with Pattern

**Risk**: New developers unfamiliar with Service-Layer Gateway pattern

**Probability**: High  
**Impact**: Medium  
**Mitigation**:
- Comprehensive onboarding documentation
- Code review guidelines enforcing pattern
- Pair programming for first few tasks
- Architecture Decision Records (this document)
- Example code in documentation
- Mentor assignment for new team members

### Risk 2: Debugging Complexity

**Risk**: Permission failures harder to trace without DRF permission error messages

**Probability**: Medium  
**Impact**: Low  
**Mitigation**:
- Comprehensive logging in service layer
- Clear exception messages with context
- Development environment debug logging
- Integration with error tracking (Sentry, etc.)
- Standardized exception format

### Risk 3: Documentation Drift

**Risk**: API documentation doesn't reflect actual permission rules

**Probability**: Medium  
**Impact**: Medium  
**Mitigation**:
- Permissions documented in service docstrings (single source of truth)
- Automated tests verify documented behavior
- Code review checklist includes documentation check
- Quarterly documentation review
- Docstring validation in CI/CD pipeline

### Risk 4: Performance Concerns

**Risk**: Later permission checks might impact performance

**Probability**: Low  
**Impact**: Very Low  
**Mitigation**:
- Authentication still happens early (IsAuthenticated)
- Database queries optimized with select_related()
- Performance monitoring in production
- Load testing includes permission-denied scenarios
- Most requests are authorized users performing valid operations

### Risk 5: Framework Migration Complexity

**Risk**: Misunderstanding how to migrate if switching frameworks

**Probability**: Very Low  
**Impact**: Low  
**Mitigation**:
- Clear migration path documented (Appendix A)
- Pure domain functions are framework-agnostic
- Only interface layer needs rewriting
- Service and domain layers are portable
- Example migrations documented

---

## Appendix E: Metrics and Monitoring

### Success Metrics

Track these metrics to validate the decision:

1. **Code Maintainability**
   - Lines of code per feature
   - Time to implement new permission rules
   - Number of bugs related to permissions
   - Code review feedback on permission logic

2. **Performance**
   - Average request latency for authenticated requests
   - Database query count per request
   - Permission check overhead
   - Response time for denied requests

3. **Developer Productivity**
   - Time for new developers to understand permission system
   - Time to add new actions with permissions
   - Number of permission-related support tickets
   - Code review turnaround time

4. **Security**
   - Number of permission bypass vulnerabilities
   - Audit log completeness
   - Time to respond to security review findings
   - False positive rate in permission checks

### Monitoring Dashboard

**Recommended metrics to track**:

```python
# Permission denial rate by action
measure_permission_denials_total{action="delete"} 
measure_permission_denials_total{action="comment"}

# Permission check performance
measure_permission_check_duration_seconds{action="delete"}

# Service layer execution time
measure_service_duration_seconds{function="delete_measure"}

# Exception rates
measure_permission_errors_total
measure_transition_errors_total
```

---

## Appendix F: Frequently Asked Questions

### Q1: Why not use Django's built-in permissions system?

**A**: Django's permission system is designed for model-level permissions (can user X edit Measures?), not instance-level business rules (can user X edit THIS specific measure based on their relationship to it?). Our rules are too complex and context-dependent for Django's built-in system.

### Q2: What if we need to expose permissions to the frontend?

**A**: The `MeasureDetailSerializer` already includes `available_transitions` and `permissions` fields that are populated by the service layer. Frontends can use this to show/hide UI elements.

Example response:
```json
{
  "id": 1,
  "description": "Fix vulnerability",
  "permissions": {
    "can_edit": true,
    "can_delete": false,
    "can_transition": true
  },
  "available_transitions": [
    {"action": "start-progress", "name": "Start Progress"}
  ]
}
```

### Q3: How do we handle permissions in background tasks?

**A**: Background tasks (Celery, etc.) call the same service functions, passing a system user or the relevant user object. The service layer enforces the same rules regardless of the interface.

```python
# Celery task
@shared_task
def auto_close_completed_measures():
    system_user = User.objects.get(email='system@example.com')
    measures = Measure.objects.filter(status='PENDING_REVIEW', ...)
    
    for measure in measures:
        try:
            services.complete(
                measure=measure,
                user=system_user,
                closure_comment="Auto-closed by system"
            )
        except MeasurePermissionError:
            # System user lacks permission - log and skip
            logger.error(f"System cannot close measure {measure.id}")
```

### Q4: What about GraphQL or other API styles?

**A**: The service layer is framework-agnostic. GraphQL resolvers would call the same service functions:

```python
# GraphQL resolver
class Mutation:
    def resolve_delete_measure(self, info, measure_id):
        user = info.context.user
        measure = Measure.objects.get(id=measure_id)
        
        try:
            services.delete_measure(measure=measure, user=user)
            return DeleteMeasureSuccess(message="Deleted")
        except MeasurePermissionError as e:
            return DeleteMeasureError(message=str(e))
```

### Q5: How do we test permission logic in isolation?

**A**: Test the pure functions in `workflows.py`:

```python
def test_can_delete_as_creator():
    measure = Mock(status=Mock(code='OPEN'), created_by=Mock(id=1))
    user = Mock(id=1)
    assert can_user_delete_measure(measure, user) == True

def test_cannot_delete_as_other_user():
    measure = Mock(status=Mock(code='OPEN'), created_by=Mock(id=1))
    user = Mock(id=2)
    assert can_user_delete_measure(measure, user) == False
```

No database, no Django, extremely fast tests.

### Q6: What if business rules become even more complex?

**A**: The pattern scales well. Add new pure functions to `workflows.py`:

```python
def can_user_reassign_measure(measure, user, new_responsible) -> bool:
    """Complex rule for reassignment."""
    # Multi-object logic is natural in service layer
    is_risk_officer = user.role and user.role.name == "Risk Officer"
    is_current_manager = measure.responsible and user == measure.responsible.manager
    new_responsible_in_same_bu = new_responsible.business_unit == measure.responsible.business_unit
    
    return (is_risk_officer or is_current_manager) and new_responsible_in_same_bu
```

Then use in service:
```python
@transaction.atomic
def reassign_measure(*, measure, user, new_responsible):
    if not can_user_reassign_measure(measure, user, new_responsible):
        raise MeasurePermissionError(...)
    measure.responsible = new_responsible
    measure.save()
```

### Q7: How do we handle role changes?

**A**: Roles are checked at request time, not cached. If a user's role changes, the next request uses the new role:

```python
# In views.py get_queryset()
user = self._get_fully_loaded_user()  # Fetches current role from DB

# Service functions check current role
role = get_contextual_role_name(measure, user)  # Uses current user.role
```

No need to invalidate caches or sessions.

### Q8: What about caching permission results?

**A**: Generally not recommended because:
- Permissions depend on database state (status, relationships)
- User roles can change
- Measures can be reassigned

If needed, cache at the request level only:
```python
@lru_cache(maxsize=128)
def _check_permission_cached(self, measure_id, user_id, action):
    # Only valid for duration of single request
    return services.check_permission(...)
```

---

## Appendix G: Evolution Path

### Phase 1: Current Implementation (Complete)
- ✅ Pure permission functions in domain layer
- ✅ Service layer enforces all rules
- ✅ Views delegate to services
- ✅ Comprehensive test coverage

### Phase 2: Enhanced Observability (Next 3 months)
- [ ] Add structured logging with correlation IDs
- [ ] Implement permission denial metrics
- [ ] Create Grafana dashboard for permission analytics
- [ ] Add request tracing for debugging

### Phase 3: Advanced Features (6-12 months)
- [ ] Dynamic permission configuration (database-driven rules)
- [ ] Temporal permissions (time-based access)
- [ ] Delegation mechanism (user A grants permission to user B)
- [ ] Permission history and audit trail UI

### Phase 4: Optimization (As needed)
- [ ] Query optimization based on production metrics
- [ ] Request-level permission result caching
- [ ] Lazy loading of permission checks
- [ ] Performance profiling and tuning

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-19 | Development Team | Initial version |
| | | | Complete analysis and decision |

---

## Approval Signatures

**Technical Lead**: _______________________ Date: _______

**Senior Backend Developer**: _______________________ Date: _______

**Security Officer**: _______________________ Date: _______

**Product Owner**: _______________________ Date: _______

---

**End of Architecture Decision Record**