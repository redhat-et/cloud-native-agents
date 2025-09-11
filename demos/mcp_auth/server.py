"""MCP server with Github auth."""

from email.policy import default
from typing import Any, Literal, get_args
import click
from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider
from fastmcp.server.dependencies import get_access_token

mcp = FastMCP(name="GitHub whoami MCP Server")


# Add a protected tool to test authentication
@mcp.tool
async def whoami() -> dict[str, Any]:
    """Returns information about the authenticated GitHub user."""

    token = get_access_token()

    if not token:
        return {}
    # The GitHubProvider stores user data in token claims
    return {
        "github_user": token.claims.get("login"),
        "name": token.claims.get("name"),
        "email": token.claims.get("email"),
    }


Transport = Literal["stdio", "http", "sse"]


@click.command()
@click.option(
    "--client_id",
    envvar="GITHUB_CLIENT_ID",
    required=True,
    help="GitHub OAuth App Client ID",
)
@click.option(
    "--client_secret",
    envvar="GITHUB_CLIENT_SECRET",
    required=True,
    help="GitHub OAuth App Client Secret",
)
@click.option(
    "--transport",
    type=click.Choice(get_args(Transport)),
    default="http",
    help="MCP Transport protocol",
)
@click.option(
    "--port", default=8080, type=int, help="MCP server port for HTTP/SSE transport"
)
@click.option(
    "--host", default="localhost", help="MCP server host for HTTP/SSE transport"
)
def main(
    client_id: str,
    client_secret: str,
    transport: Transport,
    port: str,
    host: str,
):
    """MCP server with Github auth."""

    auth_provider = GitHubProvider(
        client_id=client_id,
        client_secret=client_secret,
        base_url=f"http://{host}:{port}",
    )
    mcp.auth = auth_provider
    if transport == 'stdio':
        mcp.run()
    else:
        mcp.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
