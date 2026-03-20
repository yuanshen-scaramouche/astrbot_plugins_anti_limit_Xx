# Agent Guidelines for AstrBot Rate Limit Plugin

## 1. Build/Lint/Test Commands

### Linting & Formatting
- **Ruff check**: `ruff check .`
- **Ruff auto-fix**: `ruff check --fix .`
- **Ruff format**: `ruff format .`
- **Check format only**: `ruff format --check .`

### Testing
Currently, there are no tests in this repository. When tests are added:
- **Run all tests**: `pytest`
- **Run single test**: `pytest path/to/test_file.py::test_function_name`
- **Run with coverage**: `pytest --cov=src tests/`
- **Run specific module**: `pytest tests/test_module.py`
- **Run tests verbosely**: `pytest -v`

### Dependencies
- **Install**: `pip install -r requirements.txt`
- **Development**: `pip install -r requirements-dev.txt` (if exists)
- Note: This plugin has no external dependencies beyond AstrBot core framework

### Python Version
- Target Python 3.9+ (supports built-in collection types for type hints)

## 2. Code Style Guidelines

### Imports (PEP 8)
1. Standard library imports first (alphabetically sorted)
2. Third-party imports (alphabetically sorted)
3. Local application/library imports (alphabetically sorted)
4. Each import on its own line
5. Use absolute imports for local modules
6. Avoid wildcard imports (`from module import *`)

Example from codebase:
```python
import time
import json
import math
from pathlib import Path
from collections import defaultdict

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.event.filter import EventMessageType, PermissionType
from astrbot.api.star import Context, Star, register
```

### Formatting (Ruff/Black Defaults)
- **Line length**: 88 characters maximum
- **Indentation**: 4 spaces (no tabs)
- **One statement per line**
- **Blank lines**:
  - 2 blank lines between top-level definitions (functions, classes)
  - 1 blank line between method definitions in a class
  - Use blank lines sparingly in functions for logical sections
- **Trailing commas**: Use in multi-line containers when it aids readability
- **Whitespace**:
  - No whitespace inside parentheses/brackets/braces
  - No whitespace before commas, semicolons, colons
  - Whitespace around operators and after commas

### Type Hints (PEP 484)
- Use type hints for all function parameters and return values
- For Python 3.9+, use built-in types: `list[str]`, `dict[str, int]`
- Use `typing` module for complex types when needed
- Use `-> None` for functions without return value
- Use `-> NoReturn` for functions that never return
- Annotate `self` and `cls` parameters in class methods
- Use forward references (quoted types) for circular dependencies

Example:
```python
def process_data(items: list[str], options: dict[str, int] | None = None) -> bool:
    """Process a list of items with optional configuration."""
    if options is None:
        options = {}
    return True
```

### Naming Conventions
- **Classes**: CapWords (PascalCase) - `AntiRepeatPlugin`
- **Functions/variables**: snake_case - `process_data`, `user_count`
- **Constants**: UPPER_SNAKE_CASE - `MAX_RETRIES`, `DEFAULT_TIMEOUT`
- **Module names**: snake_case - `data_utils`, `http_client`
- **Private**: single leading underscore - `_helper`, `_internal_value`
- **Strongly private**: double leading underscore - `__private_attr`
- **Boolean variables**: use `is_`, `has_`, `should_` prefixes - `is_valid`
- Avoid single-character variables except for counters in short loops
- Prefer clarity over brevity

### Error Handling
- Use try-except blocks to catch specific exceptions
- Avoid bare `except:` clauses
- Handle exceptions appropriately or re-raise
- Log exceptions using `logger` module (not `print`)
- Clean up resources in `finally` blocks or use context managers
- Don't suppress exceptions unless necessary and well-documented
- Validate inputs in public API functions, raise `ValueError`/`TypeError`

Example from codebase:
```python
try:
    with open(self.config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    logger.info("Config file not found, using defaults.")
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON: {e}")
except Exception as e:
    logger.error(f"Read config failed: {e}")
```

### Documentation
- **Docstrings**: Use triple double quotes (`"""`)
- **Style**: NumPy or Google style docstrings
- **Module docstring**: Describe module purpose at top
- **Class docstring**: Describe class purpose and usage
- **Function docstring**: Describe parameters, returns, side effects, exceptions
- Keep docstrings updated when code changes
- Add inline comments explaining **why** (not **what**) for non-obvious code
- Avoid commenting out large blocks; use version control

### AstrBot Plugin Specific Guidelines
- Inherit from `Star` class
- Use `@register` decorator with metadata: `(name, author, description, version)`
- Use AstrBot event filters properly:
  - `@filter.command("command_name", alias={"alias1"})`
  - `@filter.command_group("group_name")`
  - `@filter.event_message_type(EventMessageType.ALL, priority=10)`
  - `@filter.permission_type(PermissionType.ADMIN)`
- Handle async operations with `async/await`
- Access context via `self.context`
- Send messages: `self.context.send_message()`
- Store plugin data in instance variables
- Load/save config using JSON files in plugin directory
- Use `yield event.plain_result()` for command responses
- Respect permissions using `PermissionType` constants
- Keep command handlers focused, delegate complex logic to helpers

Example from codebase:
```python
@register("anti_repeat", "星汐", "防重复指令拦截器", "1.1.0")
class AntiRepeatPlugin(Star):
    def __init__(self, context: Context, config_file="config.json"):
        super().__init__(context)
        self.cooldown_seconds = 3.0
        self.load_config()

    @filter.command("Xxhelp", alias={"拦截帮助"})
    async def Xxhelp(self, event: AstrMessageEvent):
        yield event.plain_result("Help message")
```

### Security Considerations
- Validate and sanitize all user inputs
- Avoid command injection in system commands
- Never log sensitive data (tokens, passwords)
- Use principle of least privilege for permissions
- Validate file paths in file operations
- Consider rate limiting for external API calls
- Update dependencies regularly

### Performance Considerations
- Avoid blocking operations in async functions
- Use efficient data structures: `set` for lookups, `dict` for mappings
- Cache expensive computations when appropriate
- Use `defaultdict` to reduce key lookup overhead
- Be mindful of memory with large data structures
- Use async alternatives for I/O-bound operations
- Pre-compile regex patterns and cache frequently used data

### Version Control
- Write clear, descriptive commit messages
- Keep commits focused on single changes
- Don't commit generated files or dependencies
- Use `.gitignore` for local environment files
- Branch naming: `feature/`, `bugfix/`, `hotfix/`

### Additional Notes
- The plugin uses Ruff for linting (no config file currently)
- Follow existing code style in `main.py`
- When in doubt, prioritize readability over cleverness
- Test edge cases and error conditions
- Keep dependencies minimal and up-to-date
- Chinese comments are acceptable in this codebase
- Configuration stored in `config.json` with snake_case keys
- Plugin data directory obtained via `self.get_data_dir()`
- Use `logger` from `astrbot.api` for all logging operations
