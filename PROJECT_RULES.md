# Project Rules & Lessons Learned

## Type Checking & Protocol Design

### Protocol vs Direct Type Usage
**Lesson Learned**: When working with external libraries, prefer direct type imports over custom protocols when possible.

**Problem**: Created `MCPSessionProtocol` to match `ClientSession` interface, but struggled with return type mismatches and method signature differences.

**Solution**: Use direct import `from mcp import ClientSession` instead of creating a protocol.

**Rule**: 
- Use protocols only when you need to abstract over multiple different types
- For single external library interfaces, prefer direct type imports
- Always verify actual method signatures before creating protocols

### Decorator Type Preservation
**Lesson Learned**: Decorators can interfere with type inference, especially when they don't preserve return types.

**Problem**: `@handle_config_errors` decorator caused "Unknown" return type issues.

**Solution**: Remove problematic decorators and handle error wrapping manually when type checking is critical.

**Rule**:
- Avoid complex decorators on methods where precise type checking is needed
- If decorators are necessary, ensure they preserve type annotations
- Consider manual error handling for critical type-checked methods

## Error Handling Patterns

### Systematic Error: Decorator Type Interference
**Pattern**: When type checker reports "Unknown" return types on decorated methods.

**Root Cause**: Decorators returning generic `Callable` instead of preserving specific return types.

**Detection**: Look for `reportUnknownMemberType` errors on decorated methods.

**Fix**: 
1. Remove decorator and handle manually
2. Or fix decorator to preserve types using `TypeVar` and `cast`
3. Or use `@typing.overload` for complex cases

### Systematic Error: Protocol Mismatch
**Pattern**: `reportArgumentType` errors when passing concrete types to protocols.

**Root Cause**: Protocol definition doesn't match actual interface signatures.

**Detection**: Compare protocol methods with actual library methods using `inspect.signature()`.

**Fix**:
1. Update protocol to match actual signatures exactly
2. Or use direct type imports instead of protocols
3. Or use `Union[ConcreteType, Protocol]` for flexibility

## Code Organization Rules

### Import Order
```python
# 1. Standard library imports
import json
import logging
from typing import Any, ClassVar

# 2. Third-party imports  
from mcp import ClientSession

# 3. Local imports
from .exceptions import ConfigurationError
from .utils import extract_tool_content
```

### Type Annotation Rules
- Always annotate function parameters and return types
- Use `Any` sparingly - prefer specific types when possible
- For external library types, import directly rather than creating protocols
- Use `# noqa: ANN401` only when `Any` is truly necessary

### Error Handling Rules
- Use structured exception hierarchy
- Include error codes for programmatic handling
- Log errors with context before re-raising
- Avoid bare `except:` clauses - catch specific exceptions

## Testing Rules

### Type Checking Tests
- Run `python -m py_compile` on changed files
- Use `mypy` or `pyright` for static type checking
- Test protocol compatibility with actual types

### Error Handling Tests
- Test both success and failure paths
- Verify error codes and messages
- Test exception wrapping and re-raising

## Debugging Type Issues

### When Type Checker Reports "Unknown"
1. Check if method is decorated
2. Verify return type annotations
3. Check for protocol mismatches
4. Look for circular imports

### When Protocol Doesn't Match
1. Use `inspect.signature()` to check actual method signatures
2. Compare return types using `type()` or `inspect.get_annotations()`
3. Consider using direct type imports instead of protocols

## Performance & Best Practices

### Avoid Over-Engineering
- Don't create protocols unless you need to abstract over multiple types
- Prefer simple, direct solutions over complex abstractions
- Focus on functionality over enterprise patterns for hobby projects

### Code Complexity
- Keep files under 300 lines (soft limit)
- Limit public symbols per file to 3-5
- Use single responsibility principle

## Common Anti-Patterns to Avoid

### ❌ Protocol Over-Engineering
```python
# Don't create protocols for single external library
class ExternalLibProtocol(Protocol):
    def method(self) -> Any: ...

# Do use direct imports
from external_lib import ConcreteClass
```

### ❌ Decorator Type Loss
```python
# Don't use decorators that lose type information
@problematic_decorator
def method(self) -> SpecificType: ...

# Do handle manually when types matter
def method(self) -> SpecificType:
    try:
        return self._implementation()
    except Exception as e:
        self._handle_error(e)
```

### ❌ Generic Error Handling
```python
# Don't catch all exceptions
try:
    do_something()
except:  # Bare except
    pass

# Do catch specific exceptions
try:
    do_something()
except (ValueError, RuntimeError) as e:
    handle_specific_error(e)
```

## Tools & Commands

### Type Checking
```bash
# Check if file compiles
python -m py_compile path/to/file.py

# Check method signatures
python -c "from module import Class; import inspect; print(inspect.signature(Class.method))"

# Check return types
python -c "from module import Class; print(type(Class().method()))"
```

### Error Investigation
```bash
# Check for circular imports
python -c "import module; print('Import successful')"

# Verify decorator behavior
python -c "from module import decorated_function; print(decorated_function.__annotations__)"
```

## Future Improvements

### Type Safety Enhancements
- Consider using `mypy` for stricter type checking
- Add runtime type validation for critical paths
- Use `dataclasses` or `pydantic` for structured data

### Error Handling Improvements
- Implement structured logging with correlation IDs
- Add error recovery mechanisms
- Create error reporting system for production

### Testing Improvements
- Add property-based testing for complex logic
- Implement integration tests for external library interactions
- Add performance benchmarks for critical paths 