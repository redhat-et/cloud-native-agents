import asyncio
import grpc
import grpc.aio as grpc_aio
from . import agents_pb2, agents_pb2_grpc
from backend.core.agents import AgentManager

class IssueAnalyzerServicer(agents_pb2_grpc.IssueAnalyzerServicer):
    async def AnalyzeIssue(self, request, context):
        # Use AgentManager to analyze the issue (without posting a comment)
        manager = AgentManager()
        result = await manager.analyze_issue_without_comment(request.issue_link)
        # result is a dict with a 'response' key
        return agents_pb2.AnalyzeIssueResponse(response=str(result['response']))

def serve():
    # Use grpc.aio.server() for async support
    server = grpc_aio.server()
    agents_pb2_grpc.add_IssueAnalyzerServicer_to_server(IssueAnalyzerServicer(), server)
    server.add_insecure_port('[::]:50051')
    print('gRPC server running on port 50051...')
    asyncio.get_event_loop().run_until_complete(server.start())
    asyncio.get_event_loop().run_until_complete(server.wait_for_termination())

if __name__ == '__main__':
    serve() 
