from agents import Agent, FunctionTool, RunContextWrapper, function_tool, Runner, set_tracing_disabled
from openai import OpenAI
import os
import subprocess
from typing import Any
from agents.extensions.models.litellm_model import LitellmModel
model = 'groq/openai/gpt-oss-120b'
api_key = os.environ.get("GROQ_API_KEY")

@function_tool(name_override="fetch_data")  
def git_log(ctx: RunContextWrapper[Any], directory: str, path: str) -> str:
    """Get git commit history for a repository or file.

    Args:
        directory: The directory/path to the git repository.
        path: Path to a specific file within the repository, or empty string for entire repo.
    """
    ## run the git log command to get the commit history
    if path and path.strip():
        cmd = ["git", "-C", directory, "log", "--oneline", "--no-decorate", "-50", path]
    else:
        cmd = ["git", "-C", directory, "log", "--oneline", "--no-decorate", "-50"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "Unknown error"
            return f"Error: {error_msg}"
        final_result = result.stdout
        if not final_result.strip():
            return "No commits found in the repository."
        return final_result
    except Exception as e:
        return f"Error accessing repository: {str(e)}"

agent = Agent(name="Release Notes Writer", instructions="Your role is to write release notes given a repo, by checking the commit history since the last release.", tools=[git_log], model=LitellmModel(model=model, api_key=api_key))

# Configure OpenAI client to use Groq
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

async def main():
    # Using a git repository that exists - let's test with email_normalizer itself
    result = await Runner.run(agent, "Get the commit history for the repository at /Users/annhoward/src/docusign_clone. Use an empty string for the path parameter to get the full repo history.")
    print(result.final_output)
    return result
    
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())