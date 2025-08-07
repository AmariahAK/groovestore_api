from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views, auth

app_name = 'api'

urlpatterns = [
    # Authentication
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/oidc/', auth.oidc_authenticate, name='oidc_authenticate'),
    path('auth/oidc/config/', auth.oidc_config, name='oidc_config'),
    path('auth/oidc/callback/', auth.oidc_callback, name='oidc_callback'),
    
    # Customers
    path('customers/', views.CustomerListCreateView.as_view(), name='customer-list-create'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer-detail'),
    
    # Categories
    path('categories/', views.CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/all/', views.AllCategoriesView.as_view(), name='category-list-all'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('categories/<int:category_id>/average-price/', views.CategoryAveragePriceView.as_view(), name='category-average-price'),
    
    # Products
    path('products/', views.ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('products/bulk-upload/', views.bulk_upload_products, name='product-bulk-upload'),
    
    # Orders
    path('orders/', views.OrderListCreateView.as_view(), name='order-list-create'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
]
