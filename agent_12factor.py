"""
12-Factor Agent Implementation for Release Notes Generation

Applying principles from https://github.com/humanlayer/12-factor-agents:
1. Natural Language to Tool Calls - Using structured tool definitions
2. Own your prompts - Explicit, version-controlled prompts
3. Own your context window - Explicit context management
4. Tools are structured outputs - Type-safe tool definitions
5. Unify execution state and business state - Clear state tracking
6. Launch/Pause/Resume - Stateless design for resumability
7. Contact humans with tool calls - (Not needed for this use case)
8. Own your control flow - Explicit control, not hidden in framework
9. Compact Errors into Context - Error handling with compact messages
10. Small, Focused Agents - Single responsibility: release notes
11. Trigger from anywhere - Flexible invocation
12. Make your agent a stateless reducer - Pure function design
"""

import os
import subprocess
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from agents import Agent, function_tool, Runner, RunContextWrapper
from agents.extensions.models.litellm_model import LitellmModel


# ============================================================================
# Factor 2: Own your prompts - Version controlled, explicit prompts
# ============================================================================

SYSTEM_PROMPT = """You are a Release Notes Writer specialized in creating clear, 
professional release notes from git commit history.

Your task:
1. Analyze the git commit history provided
2. Group commits by category (Features, Fixes, Improvements, etc.)
3. Write concise, user-friendly release notes
4. Focus on what changed, not how it was implemented
5. Use professional tone suitable for production releases

Format the output as:
- Clear section headings
- Bullet points for each change
- Highlight breaking changes if any
- Keep it concise but informative
"""


# ============================================================================
# Factor 4: Tools are structured outputs - Type-safe definitions
# ============================================================================

class ToolResult(Enum):
    """Standardized tool result types"""
    SUCCESS = "success"
    ERROR = "error"
    EMPTY = "empty"


@dataclass
class GitLogResult:
    """Structured output from git log tool"""
    status: ToolResult
    commits: List[str]
    error_message: Optional[str] = None
    commit_count: int = 0
    
    def to_context(self) -> str:
        """Factor 9: Compact errors into context window"""
        if self.status == ToolResult.ERROR:
            return f"Error accessing repository: {self.error_message}"
        if self.status == ToolResult.EMPTY:
            return "No commits found in the repository."
        return f"Found {self.commit_count} commits:\n" + "\n".join(self.commits)


# ============================================================================
# Factor 3: Own your context window - Explicit context management
# ============================================================================

@dataclass
class AgentContext:
    """Explicit context window management"""
    system_prompt: str
    user_request: str
    tool_results: List[Dict[str, Any]]
    
    def to_messages(self) -> List[Dict[str, str]]:
        """Convert context to message format"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_request}
        ]
        
        # Add tool results to context
        for result in self.tool_results:
            messages.append({
                "role": "assistant",
                "content": json.dumps(result)
            })
        
        return messages
    
    def add_tool_result(self, tool_name: str, result: str) -> None:
        """Add a tool result to context"""
        self.tool_results.append({
            "tool": tool_name,
            "result": result
        })


# ============================================================================
# Factor 1: Natural Language to Tool Calls - Clean tool definitions
# Factor 9: Compact Errors into Context - Error handling
# ============================================================================

@function_tool(name_override="get_git_commits")
def get_git_commits(ctx: RunContextWrapper[Any], directory: str, path: str, max_commits: int = 50) -> str:
    """Fetch git commit history for a repository.
    
    Args:
        directory: Absolute path to the git repository
        path: Optional path to specific file (use empty string for full repo)
        max_commits: Maximum number of commits to retrieve (default: 50)
    
    Returns:
        Formatted string with commit history or error message
    """
    # Input validation
    if not directory or not os.path.isabs(directory):
        result = GitLogResult(
            status=ToolResult.ERROR,
            commits=[],
            error_message="Directory must be an absolute path"
        )
        return result.to_context()
    
    if not os.path.exists(directory):
        result = GitLogResult(
            status=ToolResult.ERROR,
            commits=[],
            error_message=f"Directory does not exist: {directory}"
        )
        return result.to_context()
    
    # Build git command
    cmd = ["git", "-C", directory, "log", "--oneline", "--no-decorate", f"-{max_commits}"]
    if path and path.strip():
        cmd.append(path)
    
    try:
        # Execute git command
        result_proc = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=30  # Factor 9: Prevent hanging
        )
        
        if result_proc.returncode != 0:
            # Factor 9: Compact error message
            error_msg = result_proc.stderr.strip() or "Git command failed"
            if "not a git repository" in error_msg:
                error_msg = "Not a git repository"
            result = GitLogResult(
                status=ToolResult.ERROR,
                commits=[],
                error_message=error_msg
            )
            return result.to_context()
        
        commits = [line for line in result_proc.stdout.strip().split('\n') if line]
        
        if not commits:
            result = GitLogResult(
                status=ToolResult.EMPTY,
                commits=[]
            )
            return result.to_context()
        
        result = GitLogResult(
            status=ToolResult.SUCCESS,
            commits=commits,
            commit_count=len(commits)
        )
        return result.to_context()
        
    except subprocess.TimeoutExpired:
        result = GitLogResult(
            status=ToolResult.ERROR,
            commits=[],
            error_message="Git command timed out after 30s"
        )
        return result.to_context()
    except Exception as e:
        # Factor 9: Compact generic errors
        result = GitLogResult(
            status=ToolResult.ERROR,
            commits=[],
            error_message=f"Unexpected error: {type(e).__name__}"
        )
        return result.to_context()


# ============================================================================
# Factor 8: Own your control flow - Explicit agent control
# Factor 10: Small, Focused Agents - Single responsibility
# ============================================================================

class ReleaseNotesAgent:
    """
    Small, focused agent for generating release notes.
    Factor 10: Does one thing well - converts git history to release notes
    """
    
    def __init__(self, model_name: str = None, api_key: str = None):
        """Initialize agent with explicit configuration.
        
        Factor 2: Own your prompts - Explicit system prompt
        Factor 6: Launch/Pause/Resume - Stateless initialization
        """
        self.model_name = model_name or os.environ.get("MODEL_NAME", "groq/openai/gpt-oss-120b")
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        
        if not self.api_key:
            raise ValueError("API key required: set GROQ_API_KEY environment variable")
        
        # Factor 2: Own your prompts
        self.system_prompt = SYSTEM_PROMPT
        
        # Initialize agent with explicit configuration
        self.agent = Agent(
            name="Release Notes Writer",
            instructions=self.system_prompt,
            tools=[get_git_commits],
            model=LitellmModel(model=self.model_name, api_key=self.api_key)
        )
    
    async def generate_release_notes(
        self, 
        repository_path: str, 
        file_path: str = "",
        max_commits: int = 50
    ) -> str:
        """
        Generate release notes for a repository.
        
        Factor 12: Stateless reducer - Pure function design
        Factor 8: Own your control flow - Explicit execution
        
        Args:
            repository_path: Absolute path to git repository
            file_path: Optional specific file path (empty for full repo)
            max_commits: Maximum commits to analyze
            
        Returns:
            Formatted release notes as string
        """
        # Factor 3: Own your context window - Build explicit context
        user_request = f"""Generate release notes for the git repository at: {repository_path}
        
File filter: {file_path or "entire repository"}
Max commits to analyze: {max_commits}

Use the get_git_commits tool to fetch the commit history, then create professional release notes."""
        
        # Factor 8: Explicit control flow
        result = await Runner.run(self.agent, user_request)
        
        return result.final_output


# ============================================================================
# Factor 11: Trigger from anywhere - Flexible invocation patterns
# ============================================================================

async def generate_release_notes_cli(
    repository_path: str,
    file_path: str = "",
    output_file: Optional[str] = None
) -> str:
    """
    CLI-friendly interface for generating release notes.
    Factor 11: Can be called from CLI, API, webhook, cron, etc.
    """
    agent = ReleaseNotesAgent()
    notes = await agent.generate_release_notes(repository_path, file_path)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(notes)
        print(f"Release notes written to: {output_file}")
    
    return notes


async def generate_release_notes_api(
    repository_path: str,
    file_path: str = "",
) -> Dict[str, Any]:
    """
    API-friendly interface returning structured data.
    Factor 11: Same core logic, different interface
    """
    agent = ReleaseNotesAgent()
    notes = await agent.generate_release_notes(repository_path, file_path)
    
    return {
        "status": "success",
        "repository": repository_path,
        "file_path": file_path,
        "release_notes": notes,
        "generated_at": "2026-01-14"  # In production, use actual timestamp
    }


# ============================================================================
# Factor 12: Stateless reducer - Entry point
# ============================================================================

async def main():
    """
    Factor 6: Simple launch API
    Factor 12: Stateless - no shared state, can be resumed
    """
    # Configuration from environment (Factor 2)
    repo_path = os.environ.get("REPO_PATH", "/Users/annhoward/src/docusign_clone")
    file_path = os.environ.get("FILE_PATH", "")
    
    print(f"Generating release notes for: {repo_path}")
    print("-" * 60)
    
    # Factor 11: Trigger from anywhere
    agent = ReleaseNotesAgent()
    notes = await agent.generate_release_notes(repo_path, file_path)
    
    print(notes)
    print("-" * 60)
    print("✅ Release notes generated successfully")
    
    return notes


if __name__ == "__main__":
    asyncio.run(main())
