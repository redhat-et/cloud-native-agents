import grpc
from . import agents_pb2, agents_pb2_grpc
from autogen_core.tools import FunctionTool

async def analyze_issue_grpc(issue_link: str) -> str:
    """Call the Issue Analyzer team over gRPC to analyze a GitHub issue and return the response."""
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = agents_pb2_grpc.IssueAnalyzerStub(channel)
        request = agents_pb2.AnalyzeIssueRequest(issue_link=issue_link)
        response = await stub.AnalyzeIssue(request)
        return response.response

analyze_issue_grpc_tool = FunctionTool(
    analyze_issue_grpc,
    description="Analyze a GitHub issue using the Issue Analyzer team over gRPC. Takes an issue_link (str) and returns the analysis (str)."
) 
