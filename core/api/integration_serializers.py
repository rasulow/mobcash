"""
Serializers for Data Integration API endpoints
"""
from rest_framework import serializers


class IntegrationUsersRequestSerializer(serializers.Serializer):
    """Serializer for users request (date range option)"""
    startdate = serializers.DateTimeField(
        required=False,
        help_text="Start date in ISO format (e.g., 2023-01-01T00:00:00.000Z)"
    )
    enddate = serializers.DateTimeField(
        required=False,
        help_text="End date in ISO format (e.g., 2023-01-31T23:59:59.999Z)"
    )
    lastupdated = serializers.DateTimeField(
        required=False,
        help_text="Last updated timestamp in ISO format"
    )
    pagesize = serializers.IntegerField(
        default=100,
        required=False,
        min_value=1,
        max_value=1000,
        help_text="Number of records per page (default 100)"
    )
    skip = serializers.IntegerField(
        default=0,
        required=False,
        min_value=0,
        help_text="Number of records to skip (default 0)"
    )

    def validate(self, data):
        """Validate that either date range or last_updated is provided"""
        has_date_range = 'startdate' in data and 'enddate' in data
        has_last_updated = 'lastupdated' in data
        
        if not has_date_range and not has_last_updated:
            raise serializers.ValidationError(
                "Either (startdate and enddate) or lastupdated must be provided"
            )
        
        if has_date_range and has_last_updated:
            raise serializers.ValidationError(
                "Cannot provide both date range and lastupdated"
            )
        
        if 'startdate' in data and 'enddate' not in data:
            raise serializers.ValidationError("enddate is required when startdate is provided")
        
        if 'enddate' in data and 'startdate' not in data:
            raise serializers.ValidationError("startdate is required when enddate is provided")
        
        return data


class IntegrationTransactionsRequestSerializer(serializers.Serializer):
    """Serializer for transactions request"""
    type = serializers.ChoiceField(
        choices=['casino', 'sports', 'deposit', 'withdraw'],
        help_text="Transaction type: casino, sports, deposit, or withdraw"
    )
    startdate = serializers.DateTimeField(
        required=False,
        help_text="Start date in ISO format (e.g., 2023-01-01T00:00:00.000Z)"
    )
    enddate = serializers.DateTimeField(
        required=False,
        help_text="End date in ISO format (e.g., 2023-01-31T23:59:59.999Z)"
    )
    lastupdated = serializers.DateTimeField(
        required=False,
        help_text="Last updated timestamp in ISO format"
    )
    pagesize = serializers.IntegerField(
        default=100,
        required=False,
        min_value=1,
        max_value=1000,
        help_text="Number of records per page (default 100)"
    )
    skip = serializers.IntegerField(
        default=0,
        required=False,
        min_value=0,
        help_text="Number of records to skip (default 0)"
    )

    def validate(self, data):
        """Validate that either date range or last_updated is provided"""
        has_date_range = 'startdate' in data and 'enddate' in data
        has_last_updated = 'lastupdated' in data
        
        if not has_date_range and not has_last_updated:
            raise serializers.ValidationError(
                "Either (startdate and enddate) or lastupdated must be provided"
            )
        
        if has_date_range and has_last_updated:
            raise serializers.ValidationError(
                "Cannot provide both date range and lastupdated"
            )
        
        if 'startdate' in data and 'enddate' not in data:
            raise serializers.ValidationError("enddate is required when startdate is provided")
        
        if 'enddate' in data and 'startdate' not in data:
            raise serializers.ValidationError("startdate is required when enddate is provided")
        
        return data


class IntegrationResponseSerializer(serializers.Serializer):
    """Serializer for integration API response"""
    statusCode = serializers.IntegerField(
        help_text="HTTP status code"
    )
    error = serializers.JSONField(
        allow_null=True,
        help_text="Error object (null if successful)"
    )
    data = serializers.JSONField(
        help_text="Response data containing count, pagesize, and result array"
    )
