from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Avg, Count
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
import requests
import json
from .models import Customer, Category, Product, Order, OrderItem
from .serializers import (
    CustomerSerializer, CategorySerializer, ProductSerializer,
    ProductWithCategorySerializer, OrderSerializer, CreateOrderSerializer,
    CategoryAveragePriceSerializer
)


class CustomerListCreateView(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.filter(parent=None)  # Root categories only
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class AllCategoriesView(generics.ListAPIView):
    """View to list all categories (not just root ones)"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductWithCategorySerializer
        return ProductSerializer


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]


class CategoryAveragePriceView(APIView):
    """Calculate average product price for a category including nested subcategories"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, category_id):
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return Response(
                {"error": "Category not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get all descendant categories
        descendant_categories = category.get_descendants()
        all_categories = [category] + list(descendant_categories)
        category_ids = [cat.id for cat in all_categories]
        
        # Calculate average price for products in these categories
        products = Product.objects.filter(
            category_id__in=category_ids,
            is_active=True
        )
        
        if not products.exists():
            return Response(
                {"error": "No products found in this category or its subcategories"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        avg_price = products.aggregate(avg_price=Avg('price'))['avg_price']
        product_count = products.count()
        
        data = {
            'category_id': category.id,
            'category_name': category.name,
            'category_path': category.get_full_path(),
            'average_price': round(avg_price, 2) if avg_price else 0,
            'product_count': product_count,
            'includes_subcategories': len(descendant_categories) > 0
        }
        
        serializer = CategoryAveragePriceSerializer(data)
        return Response(serializer.data)


class OrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see their own orders
        if hasattr(self.request.user, 'customer_profile'):
            return Order.objects.filter(customer=self.request.user.customer_profile)
        return Order.objects.none()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateOrderSerializer
        return OrderSerializer
    
    def perform_create(self, serializer):
        order = serializer.save()
        
        # Send notifications
        self._send_sms_notification(order)
        self._send_email_notification(order)
        
        return order
    
    def _send_sms_notification(self, order):
        """Send SMS notification using Africa's Talking API"""
        try:
            url = "https://api.sandbox.africastalking.com/version1/messaging"
            headers = {
                'apiKey': settings.AFRICAS_TALKING_API_KEY,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            data = {
                'username': settings.AFRICAS_TALKING_USERNAME,
                'to': order.customer.phone,
                'message': f"Hi {order.customer.name}, your order #{order.id} for ${order.total_amount} has been placed successfully. Thank you for shopping with us!"
            }
            
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code == 201:
                print(f"SMS sent successfully to {order.customer.phone}")
            else:
                print(f"Failed to send SMS: {response.text}")
                
        except Exception as e:
            print(f"Error sending SMS: {str(e)}")
    
    def _send_email_notification(self, order):
        """Send email notification to admin"""
        try:
            subject = f"New Order Placed - Order #{order.id}"
            
            # Build order details
            items_text = "\n".join([
                f"- {item.product.name} x {item.quantity} @ ${item.unit_price} = ${item.subtotal}"
                for item in order.items.all()
            ])
            
            message = f"""
A new order has been placed:

Order ID: #{order.id}
Customer: {order.customer.name} ({order.customer.email})
Customer Phone: {order.customer.phone}
Status: {order.get_status_display()}
Total Amount: ${order.total_amount}
Order Date: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}

Items:
{items_text}

Notes: {order.notes or 'None'}
"""
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['admin@groovestore.com'],  # Admin email
                fail_silently=False,
            )
            
            print(f"Email notification sent for order #{order.id}")
            
        except Exception as e:
            print(f"Error sending email notification: {str(e)}")


class OrderDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Users can only access their own orders
        if hasattr(self.request.user, 'customer_profile'):
            return Order.objects.filter(customer=self.request.user.customer_profile)
        return Order.objects.none()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_upload_products(request):
    """
    Bulk upload products with nested category creation
    Expected format: [
        {
            "name": "Product Name",
            "description": "Product Description",
            "price": "10.99",
            "category_path": ["Parent Category", "Child Category"],
            "sku": "PROD001",
            "stock_quantity": 100
        }
    ]
    """
    if not isinstance(request.data, list):
        return Response(
            {"error": "Expected a list of products"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    created_products = []
    errors = []
    
    with transaction.atomic():
        for i, product_data in enumerate(request.data):
            serializer = ProductWithCategorySerializer(data=product_data)
            
            if serializer.is_valid():
                try:
                    product = serializer.save()
                    created_products.append(ProductSerializer(product).data)
                except Exception as e:
                    errors.append(f"Product {i+1}: {str(e)}")
            else:
                errors.append(f"Product {i+1}: {serializer.errors}")
    
    response_data = {
        "created_count": len(created_products),
        "error_count": len(errors),
        "created_products": created_products,
        "errors": errors
    }
    
    if errors:
        return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
    
    return Response(response_data, status=status.HTTP_201_CREATED)
