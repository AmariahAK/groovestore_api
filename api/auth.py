"""
OpenID Connect Authentication Implementation
This is a simplified implementation for demonstration purposes.
In production, you would use a proper OIDC library like django-oidc-provider or mozilla-django-oidc.
"""

import requests
import json
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Customer
from .serializers import CustomerSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def oidc_authenticate(request):
    """
    Simulate OpenID Connect authentication
    In a real implementation, this would:
    1. Redirect to OIDC provider
    2. Handle callback
    3. Validate ID token
    4. Create/update user
    
    For this demo, we accept a mock ID token or user info
    """
    
    # For demo purposes, accept direct user info
    user_info = request.data.get('user_info', {})
    id_token = request.data.get('id_token', '')
    
    if not user_info and not id_token:
        return Response({
            'error': 'Either user_info or id_token is required',
            'demo_note': 'For testing, send user_info with email, name, and phone'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # In a real implementation, you would validate the ID token here
        if id_token:
            # Simulate token validation
            if settings.OIDC_ISSUER:
                # In production, validate against OIDC issuer
                user_info = _mock_validate_token(id_token)
            else:
                return Response({
                    'error': 'OIDC_ISSUER not configured'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Extract user information
        email = user_info.get('email')
        name = user_info.get('name', user_info.get('given_name', '') + ' ' + user_info.get('family_name', ''))
        phone = user_info.get('phone', user_info.get('phone_number', ''))
        
        if not email:
            return Response({
                'error': 'Email is required from OIDC provider'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'first_name': name.split(' ')[0] if name else '',
                'last_name': ' '.join(name.split(' ')[1:]) if name and len(name.split(' ')) > 1 else '',
            }
        )
        
        # Get or create customer profile
        customer, customer_created = Customer.objects.get_or_create(
            user=user,
            defaults={
                'name': name or email,
                'email': email,
                'phone': phone or '',
            }
        )
        
        # Update customer info if it has changed
        if not customer_created:
            if name and customer.name != name:
                customer.name = name
            if phone and customer.phone != phone:
                customer.phone = phone
            customer.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        return Response({
            'access_token': str(access_token),
            'refresh_token': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'name': name,
            },
            'customer': CustomerSerializer(customer).data,
            'created': created
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Authentication failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _mock_validate_token(id_token):
    """
    Mock token validation for demo purposes
    In production, this would:
    1. Fetch OIDC provider's public keys
    2. Validate token signature
    3. Verify claims (issuer, audience, expiration)
    4. Return user claims
    """
    
    # For demo, just decode a simple format
    # Real implementation would use PyJWT or similar
    try:
        # Assume token format: base64(json(user_info))
        import base64
        decoded = base64.b64decode(id_token).decode('utf-8')
        user_info = json.loads(decoded)
        return user_info
    except:
        # Fallback to mock data for testing
        return {
            'email': 'test@example.com',
            'name': 'Test User',
            'phone': '+1234567890'
        }


@api_view(['GET'])
@permission_classes([AllowAny])
def oidc_config(request):
    """
    Return OIDC configuration for frontend
    """
    return Response({
        'issuer': settings.OIDC_ISSUER or 'https://example-oidc-provider.com',
        'client_id': settings.OIDC_CLIENT_ID or 'groovestore-client',
        'redirect_uri': request.build_absolute_uri('/api/v1/auth/oidc/callback/'),
        'scope': 'openid profile email phone',
        'demo_mode': not bool(settings.OIDC_ISSUER),
        'instructions': {
            'demo_auth': 'POST to /api/v1/auth/oidc/ with user_info containing email, name, phone',
            'production': 'Configure OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET in settings'
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def oidc_callback(request):
    """
    Handle OIDC callback (for production implementation)
    """
    code = request.data.get('code')
    state = request.data.get('state')
    
    if not code:
        return Response({
            'error': 'Authorization code is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # In production, exchange code for tokens
    return Response({
        'message': 'OIDC callback handler - implement token exchange here',
        'demo_note': 'Use /api/v1/auth/oidc/ endpoint for demo authentication'
    }, status=status.HTTP_501_NOT_IMPLEMENTED)
