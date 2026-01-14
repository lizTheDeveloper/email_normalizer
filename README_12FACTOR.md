# 12-Factor Agent for Release Notes Generation

This implementation follows the principles from [12-Factor Agents](https://github.com/humanlayer/12-factor-agents).

## The 12 Factors Applied

### ✅ Factor 1: Natural Language to Tool Calls
- Clean, type-safe tool definitions with `@function_tool`
- Tools have clear docstrings and parameter descriptions
- Natural language flows through to structured function calls

### ✅ Factor 2: Own Your Prompts
- **Explicit system prompt** stored as `SYSTEM_PROMPT` constant
- Version-controlled in code, not hidden in framework
- Easy to modify, test, and iterate on

### ✅ Factor 3: Own Your Context Window
- `AgentContext` dataclass explicitly manages context
- Clear visibility into what goes into the LLM
- Can track and debug context window usage

### ✅ Factor 4: Tools are Structured Outputs
- `GitLogResult` dataclass provides type-safe tool results
- Enum-based status codes (`ToolResult`)
- Consistent structure for success, error, and empty cases

### ✅ Factor 5: Unify Execution State and Business State
- Agent state is explicit and traceable
- No hidden framework state
- Clear separation of concerns

### ✅ Factor 6: Launch/Pause/Resume with Simple APIs
- Stateless `ReleaseNotesAgent` class
- Simple async `generate_release_notes()` method
- Can be paused/resumed because no internal state

### ✅ Factor 7: Contact Humans with Tool Calls
- Not applicable for this use case
- Could add approval tools if needed for human-in-the-loop

### ✅ Factor 8: Own Your Control Flow
- Explicit control in `generate_release_notes()`
- Not relying on framework magic
- Clear execution path

### ✅ Factor 9: Compact Errors into Context Window
- Structured error handling with compact messages
- `GitLogResult.to_context()` method formats errors efficiently
- Timeout protection (30s limit)
- Shortened common error messages

### ✅ Factor 10: Small, Focused Agents
- **Single responsibility**: Convert git history → release notes
- Does one thing well
- Easy to test and maintain

### ✅ Factor 11: Trigger from Anywhere
- Multiple invocation patterns:
  - `generate_release_notes_cli()` - CLI interface
  - `generate_release_notes_api()` - API interface
  - `main()` - Direct execution
- Can be called from cron, webhook, API, CLI, etc.

### ✅ Factor 12: Make Your Agent a Stateless Reducer
- `generate_release_notes()` is a pure function
- Takes inputs → produces outputs
- No shared state between invocations
- Easy to parallelize and scale

## Usage

### Basic Usage

```python
from agent_12factor import ReleaseNotesAgent

agent = ReleaseNotesAgent()
notes = await agent.generate_release_notes(
    repository_path="/path/to/repo",
    file_path="",  # optional: specific file
    max_commits=50
)
print(notes)
```

### CLI Usage

```bash
# Set environment variables
export GROQ_API_KEY="your-key"
export REPO_PATH="/Users/annhoward/src/docusign_clone"

# Run
python agent_12factor.py
```

### API Integration

```python
from agent_12factor import generate_release_notes_api

result = await generate_release_notes_api(
    repository_path="/path/to/repo",
    file_path=""
)
# Returns: {"status": "success", "release_notes": "...", ...}
```

## Key Improvements Over Original

1. **Explicit vs Implicit**: Everything is explicit and visible
2. **Type Safety**: Structured data classes instead of raw strings
3. **Error Handling**: Comprehensive, compact error messages
4. **Testability**: Small, focused functions are easy to test
5. **Flexibility**: Multiple invocation patterns for different contexts
6. **Maintainability**: Clear structure makes changes straightforward
7. **Production Ready**: Timeouts, validation, error handling

## Configuration

```bash
# Required
export GROQ_API_KEY="your-groq-api-key"

# Optional
export MODEL_NAME="groq/openai/gpt-oss-120b"  # default
export REPO_PATH="/path/to/default/repo"
export FILE_PATH=""  # optional file filter
```

## Architecture

```
┌─────────────────────────────────────────┐
│  Trigger Layer (Factor 11)              │
│  - CLI, API, Webhook, Cron              │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  ReleaseNotesAgent (Factor 10)          │
│  - Focused on one task                  │
│  - Stateless reducer (Factor 12)        │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  Agent Core (Factors 1,2,8)             │
│  - Natural language → tool calls        │
│  - Owned prompts & control flow         │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  Tools Layer (Factors 4,9)              │
│  - Structured outputs                   │
│  - Compact error handling               │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  Context Management (Factor 3)          │
│  - Explicit context window              │
└─────────────────────────────────────────┘
```

## Testing

The architecture makes testing straightforward:

```python
# Test tool directly
result = await get_git_commits(ctx, "/path/to/repo", "", 10)

# Test agent with mock
agent = ReleaseNotesAgent()
notes = await agent.generate_release_notes("/path/to/repo")

# Test specific invocation patterns
result = await generate_release_notes_api("/path/to/repo")
```

## Production Considerations

1. **Rate Limiting**: Add rate limits for API usage
2. **Caching**: Cache git log results for frequently accessed repos
3. **Monitoring**: Add observability (logs, metrics, traces)
4. **Validation**: Validate repository paths against allowlist
5. **Async Scaling**: Run multiple agents in parallel safely (Factor 12)
