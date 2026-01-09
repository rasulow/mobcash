"""
ViewSet for Data Integration API endpoints
"""
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.integration_api import get_integration_client, IntegrationApiError

from .integration_serializers import (
    IntegrationResponseSerializer,
    IntegrationTransactionsRequestSerializer,
    IntegrationUsersRequestSerializer,
)


class IntegrationViewSet(viewsets.GenericViewSet):
    """
    ViewSet for Data Integration API.
    
    Endpoints:
    - POST /api/integration/users/ - Get users by date range or last updated
    - POST /api/integration/txns/ - Get transactions by type and date range
    """
    
    @swagger_auto_schema(
        method='post',
        request_body=IntegrationUsersRequestSerializer,
        responses={200: IntegrationResponseSerializer}
    )
    @action(detail=False, methods=["post"], url_path="users")
    def get_users(self, request):
        """
        Retrieve users from Integration API.
        
        Request body (Option A - Date Range):
        {
            "startdate": "2023-01-01T00:00:00.000Z",
            "enddate": "2023-01-31T23:59:59.999Z",
            "pagesize": 100,
            "skip": 0
        }
        
        Request body (Option B - Last Updated):
        {
            "lastupdated": "2023-01-01T00:00:00.000Z",
            "pagesize": 100,
            "skip": 0
        }
        
        Response:
        {
            "statusCode": 200,
            "error": null,
            "data": {
                "count": 150,
                "pagesize": 100,
                "result": [...]
            }
        }
        """
        serializer = IntegrationUsersRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        start_date = serializer.validated_data.get('startdate')
        end_date = serializer.validated_data.get('enddate')
        last_updated = serializer.validated_data.get('lastupdated')
        page_size = serializer.validated_data.get('pagesize', 100)
        skip = serializer.validated_data.get('skip', 0)
        
        # Convert datetime objects to ISO format strings
        if start_date:
            start_date = start_date.isoformat()
        if end_date:
            end_date = end_date.isoformat()
        if last_updated:
            last_updated = last_updated.isoformat()
        
        try:
            # Call Integration API
            integration_client = get_integration_client()
            data = integration_client.get_users(
                start_date=start_date,
                end_date=end_date,
                last_updated=last_updated,
                page_size=page_size,
                skip=skip
            )
            
            # Return success response
            return Response(
                {
                    "statusCode": 200,
                    "error": None,
                    "data": data
                },
                status=status.HTTP_200_OK
            )
            
        except IntegrationApiError as e:
            return Response(
                {
                    "statusCode": e.status_code,
                    "error": {
                        "message": str(e),
                        "errorCode": e.error_code
                    },
                    "data": None
                },
                status=e.status_code
            )
        except Exception as e:
            return Response(
                {
                    "statusCode": 500,
                    "error": {
                        "message": f"Internal error: {str(e)}",
                        "errorCode": "INTERNAL_ERROR"
                    },
                    "data": None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        method='post',
        request_body=IntegrationTransactionsRequestSerializer,
        responses={200: IntegrationResponseSerializer}
    )
    @action(detail=False, methods=["post"], url_path="txns")
    def get_transactions(self, request):
        """
        Retrieve transactions from Integration API.
        
        Request body (Date Range):
        {
            "type": "casino",
            "startdate": "2023-01-01T00:00:00.000Z",
            "enddate": "2023-01-02T00:00:00.000Z",
            "pagesize": 50,
            "skip": 0
        }
        
        Request body (Last Updated):
        {
            "type": "deposit",
            "lastupdated": "2023-01-01T12:00:00.000Z",
            "pagesize": 50
        }
        
        Response:
        {
            "statusCode": 200,
            "error": null,
            "data": {
                "count": 75,
                "pagesize": 50,
                "result": [...]
            }
        }
        """
        serializer = IntegrationTransactionsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        txn_type = serializer.validated_data['type']
        start_date = serializer.validated_data.get('startdate')
        end_date = serializer.validated_data.get('enddate')
        last_updated = serializer.validated_data.get('lastupdated')
        page_size = serializer.validated_data.get('pagesize', 100)
        skip = serializer.validated_data.get('skip', 0)
        
        # Convert datetime objects to ISO format strings
        if start_date:
            start_date = start_date.isoformat()
        if end_date:
            end_date = end_date.isoformat()
        if last_updated:
            last_updated = last_updated.isoformat()
        
        try:
            # Call Integration API
            integration_client = get_integration_client()
            data = integration_client.get_transactions(
                txn_type=txn_type,
                start_date=start_date,
                end_date=end_date,
                last_updated=last_updated,
                page_size=page_size,
                skip=skip
            )
            
            # Return success response
            return Response(
                {
                    "statusCode": 200,
                    "error": None,
                    "data": data
                },
                status=status.HTTP_200_OK
            )
            
        except IntegrationApiError as e:
            return Response(
                {
                    "statusCode": e.status_code,
                    "error": {
                        "message": str(e),
                        "errorCode": e.error_code
                    },
                    "data": None
                },
                status=e.status_code
            )
        except Exception as e:
            return Response(
                {
                    "statusCode": 500,
                    "error": {
                        "message": f"Internal error: {str(e)}",
                        "errorCode": "INTERNAL_ERROR"
                    },
                    "data": None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
