from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from django.utils.text import slugify
from .models import Customer, Category, Product, Order, OrderItem


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Customer
        fields = ['id', 'user', 'name', 'email', 'phone', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    full_path = serializers.CharField(source='get_full_path', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'parent', 'parent_name', 'slug', 
                 'children', 'full_path', 'created_at', 'updated_at']
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
    
    def get_children(self, obj):
        children = obj.children.all()
        return CategorySerializer(children, many=True, context=self.context).data
    
    def create(self, validated_data):
        # Auto-generate slug from name
        validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'name' in validated_data:
            validated_data['slug'] = slugify(validated_data['name'])
        return super().update(instance, validated_data)


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_path = serializers.CharField(source='category.get_full_path', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'category', 'category_name', 
                 'category_path', 'sku', 'stock_quantity', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductWithCategorySerializer(serializers.ModelSerializer):
    """Serializer for creating products with nested category creation"""
    category_path = serializers.ListField(
        child=serializers.CharField(max_length=255),
        write_only=True,
        help_text="Array of category names from root to leaf (e.g., ['Bakery', 'Bread'])"
    )
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_full_path = serializers.CharField(source='category.get_full_path', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'category_path', 'category_name', 
                 'category_full_path', 'sku', 'stock_quantity', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    @transaction.atomic
    def create(self, validated_data):
        category_path = validated_data.pop('category_path')
        
        # Create or get nested categories
        parent = None
        for category_name in category_path:
            slug = slugify(category_name)
            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': category_name, 'parent': parent}
            )
            parent = category
        
        # Assign the final category to the product
        validated_data['category'] = parent
        return super().create(validated_data)


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price', 'subtotal']
        read_only_fields = ['id', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'customer', 'customer_name', 'customer_email', 'status', 
                 'total_amount', 'notes', 'items', 'created_at', 'updated_at']
        read_only_fields = ['id', 'total_amount', 'created_at', 'updated_at']


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating orders with order items"""
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    notes = serializers.CharField(required=False, allow_blank=True)
    items = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        help_text="List of items with 'product_id' and 'quantity' keys"
    )
    
    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required")
        
        for item in value:
            if 'product_id' not in item or 'quantity' not in item:
                raise serializers.ValidationError("Each item must have 'product_id' and 'quantity'")
            
            try:
                product_id = int(item['product_id'])
                quantity = int(item['quantity'])
                if quantity <= 0:
                    raise serializers.ValidationError("Quantity must be positive")
                
                # Check if product exists and is active
                product = Product.objects.get(id=product_id, is_active=True)
                if product.stock_quantity < quantity:
                    raise serializers.ValidationError(f"Insufficient stock for {product.name}")
                    
            except (ValueError, Product.DoesNotExist):
                raise serializers.ValidationError(f"Invalid product_id: {item.get('product_id')}")
        
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Create the order
        order = Order.objects.create(**validated_data)
        
        # Create order items
        for item_data in items_data:
            product = Product.objects.get(id=item_data['product_id'])
            quantity = int(item_data['quantity'])
            
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=product.price
            )
            
            # Update stock
            product.stock_quantity -= quantity
            product.save()
        
        # Calculate and save total
        order.calculate_total()
        order.save()
        
        return order


class CategoryAveragePriceSerializer(serializers.Serializer):
    """Serializer for category average price response"""
    category_id = serializers.IntegerField()
    category_name = serializers.CharField()
    category_path = serializers.CharField()
    average_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    product_count = serializers.IntegerField()
    includes_subcategories = serializers.BooleanField()
