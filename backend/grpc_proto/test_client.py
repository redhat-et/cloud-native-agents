import asyncio
from .client_and_tool import analyze_issue_grpc

async def main():
    # Replace with a real or test issue link
    issue_link = "https://github.com/RHETbot/test-repository/issues/1"
    result = await analyze_issue_grpc(issue_link)
    print("gRPC server response:", result)

if __name__ == "__main__":
    asyncio.run(main())
