from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal
from .models import Customer, Category, Product, Order, OrderItem


class ModelTestCase(TestCase):
    """Test cases for model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            user=self.user,
            name='Test Customer',
            email='test@example.com',
            phone='+1234567890'
        )
        
        # Create category hierarchy: Electronics > Computers > Laptops
        self.electronics = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        self.computers = Category.objects.create(
            name='Computers',
            slug='computers',
            parent=self.electronics
        )
        self.laptops = Category.objects.create(
            name='Laptops',
            slug='laptops',
            parent=self.computers
        )

    def test_customer_creation(self):
        """Test customer model creation and string representation"""
        self.assertEqual(str(self.customer), 'Test Customer (test@example.com)')
        self.assertEqual(self.customer.user, self.user)

    def test_category_hierarchy(self):
        """Test category hierarchy functionality"""
        # Test full path
        self.assertEqual(self.laptops.get_full_path(), 'Electronics > Computers > Laptops')
        
        # Test descendants
        electronics_descendants = self.electronics.get_descendants()
        self.assertIn(self.computers, electronics_descendants)
        self.assertIn(self.laptops, electronics_descendants)
        
        # Test ancestors
        laptop_ancestors = self.laptops.get_ancestors()
        self.assertIn(self.electronics, laptop_ancestors)
        self.assertIn(self.computers, laptop_ancestors)

    def test_product_creation(self):
        """Test product model creation"""
        product = Product.objects.create(
            name='Test Laptop',
            description='A test laptop',
            price=Decimal('999.99'),
            category=self.laptops,
            sku='LAPTOP001',
            stock_quantity=10
        )
        
        self.assertEqual(str(product), 'Test Laptop - $999.99')
        self.assertEqual(product.category, self.laptops)

    def test_order_creation_and_calculation(self):
        """Test order creation and total calculation"""
        product1 = Product.objects.create(
            name='Product 1',
            price=Decimal('10.00'),
            category=self.laptops,
            sku='PROD001',
            stock_quantity=100
        )
        product2 = Product.objects.create(
            name='Product 2',
            price=Decimal('20.00'),
            category=self.laptops,
            sku='PROD002',
            stock_quantity=100
        )
        
        order = Order.objects.create(customer=self.customer)
        
        # Create order items
        item1 = OrderItem.objects.create(
            order=order,
            product=product1,
            quantity=2,
            unit_price=product1.price
        )
        item2 = OrderItem.objects.create(
            order=order,
            product=product2,
            quantity=1,
            unit_price=product2.price
        )
        
        # Test subtotal calculation
        self.assertEqual(item1.subtotal, Decimal('20.00'))
        self.assertEqual(item2.subtotal, Decimal('20.00'))
        
        # Test order total calculation
        total = order.calculate_total()
        self.assertEqual(total, Decimal('40.00'))
        self.assertEqual(order.total_amount, Decimal('40.00'))


class APITestCase(APITestCase):
    """Test cases for API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            user=self.user,
            name='Test Customer',
            email='test@example.com',
            phone='+1234567890'
        )
        
        # Create authentication token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Create test categories
        self.root_category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        self.sub_category = Category.objects.create(
            name='Laptops',
            slug='laptops',
            parent=self.root_category
        )
        
        # Create test products
        self.product1 = Product.objects.create(
            name='Laptop 1',
            price=Decimal('999.99'),
            category=self.sub_category,
            sku='LAP001',
            stock_quantity=10
        )
        self.product2 = Product.objects.create(
            name='Laptop 2',
            price=Decimal('1299.99'),
            category=self.sub_category,
            sku='LAP002',
            stock_quantity=5
        )

    def authenticate(self):
        """Helper method to authenticate requests"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_customer_list_requires_authentication(self):
        """Test that customer list requires authentication"""
        url = reverse('api:customer-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_list_authenticated(self):
        """Test authenticated customer list"""
        self.authenticate()
        url = reverse('api:customer-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_category_list(self):
        """Test category list endpoint"""
        self.authenticate()
        url = reverse('api:category-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_category_creation(self):
        """Test category creation via API"""
        self.authenticate()
        url = reverse('api:category-list-create')
        data = {
            'name': 'New Category',
            'description': 'A new test category'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Category')

    def test_product_list(self):
        """Test product list endpoint"""
        self.authenticate()
        url = reverse('api:product-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 2)

    def test_product_creation_with_category_path(self):
        """Test product creation with nested category path"""
        self.authenticate()
        url = reverse('api:product-list-create')
        data = {
            'name': 'New Laptop',
            'description': 'A brand new laptop',
            'price': '1599.99',
            'category_path': ['Electronics', 'Computers', 'Gaming Laptops'],
            'sku': 'NEWLAP001',
            'stock_quantity': 15
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Laptop')

    def test_category_average_price(self):
        """Test category average price calculation"""
        self.authenticate()
        url = reverse('api:category-average-price', kwargs={'category_id': self.sub_category.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Calculate expected average: (999.99 + 1299.99) / 2 = 1149.99
        expected_avg = (self.product1.price + self.product2.price) / 2
        self.assertEqual(float(response.data['average_price']), float(expected_avg))

    def test_order_creation(self):
        """Test order creation via API"""
        self.authenticate()
        url = reverse('api:order-list-create')
        data = {
            'customer': self.customer.id,
            'notes': 'Test order',
            'items': [
                {'product_id': str(self.product1.id), 'quantity': '2'},
                {'product_id': str(self.product2.id), 'quantity': '1'}
            ]
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that stock was updated
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.stock_quantity, 8)  # 10 - 2
        self.assertEqual(self.product2.stock_quantity, 4)  # 5 - 1

    def test_bulk_product_upload(self):
        """Test bulk product upload endpoint"""
        self.authenticate()
        url = reverse('api:product-bulk-upload')
        data = [
            {
                'name': 'Bulk Product 1',
                'description': 'First bulk product',
                'price': '99.99',
                'category_path': ['Bulk', 'Category1'],
                'sku': 'BULK001',
                'stock_quantity': 50
            },
            {
                'name': 'Bulk Product 2',
                'description': 'Second bulk product',
                'price': '149.99',
                'category_path': ['Bulk', 'Category2'],
                'sku': 'BULK002',
                'stock_quantity': 30
            }
        ]
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['created_count'], 2)
        self.assertEqual(response.data['error_count'], 0)

    def test_oidc_authentication_demo(self):
        """Test OIDC authentication demo endpoint"""
        url = reverse('api:oidc_authenticate')
        data = {
            'user_info': {
                'email': 'oidc@example.com',
                'name': 'OIDC User',
                'phone': '+1987654321'
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)

    def test_oidc_config(self):
        """Test OIDC configuration endpoint"""
        url = reverse('api:oidc_config')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('issuer', response.data)
        self.assertIn('demo_mode', response.data)


class CategoryHierarchyTestCase(TestCase):
    """Test complex category hierarchy scenarios"""
    
    def setUp(self):
        # Create a deeper hierarchy for testing
        # All Products
        # ├── Bakery
        # │   ├── Bread
        # │   └── Cookies
        # └── Produce
        #     ├── Fruits
        #     │   ├── Apples
        #     │   └── Bananas
        #     └── Vegetables
        #         └── Carrots
        
        self.all_products = Category.objects.create(name='All Products', slug='all-products')
        
        self.bakery = Category.objects.create(name='Bakery', slug='bakery', parent=self.all_products)
        self.bread = Category.objects.create(name='Bread', slug='bread', parent=self.bakery)
        self.cookies = Category.objects.create(name='Cookies', slug='cookies', parent=self.bakery)
        
        self.produce = Category.objects.create(name='Produce', slug='produce', parent=self.all_products)
        self.fruits = Category.objects.create(name='Fruits', slug='fruits', parent=self.produce)
        self.vegetables = Category.objects.create(name='Vegetables', slug='vegetables', parent=self.produce)
        
        self.apples = Category.objects.create(name='Apples', slug='apples', parent=self.fruits)
        self.bananas = Category.objects.create(name='Bananas', slug='bananas', parent=self.fruits)
        self.carrots = Category.objects.create(name='Carrots', slug='carrots', parent=self.vegetables)

    def test_deep_hierarchy_paths(self):
        """Test full path generation for deep hierarchies"""
        self.assertEqual(self.apples.get_full_path(), 'All Products > Produce > Fruits > Apples')
        self.assertEqual(self.carrots.get_full_path(), 'All Products > Produce > Vegetables > Carrots')

    def test_descendant_calculation(self):
        """Test descendant calculation for various levels"""
        # All products should have all categories as descendants
        all_descendants = self.all_products.get_descendants()
        self.assertEqual(len(all_descendants), 8)  # All except root
        
        # Produce should have 5 descendants
        produce_descendants = self.produce.get_descendants()
        self.assertEqual(len(produce_descendants), 5)
        
        # Fruits should have 2 descendants
        fruit_descendants = self.fruits.get_descendants()
        self.assertEqual(len(fruit_descendants), 2)
        
        # Leaf nodes should have no descendants
        apple_descendants = self.apples.get_descendants()
        self.assertEqual(len(apple_descendants), 0)

    def test_ancestor_calculation(self):
        """Test ancestor calculation"""
        apple_ancestors = self.apples.get_ancestors()
        expected_ancestors = [self.fruits, self.produce, self.all_products]
        self.assertEqual(list(reversed(apple_ancestors)), expected_ancestors)


class OrderCalculationTestCase(TestCase):
    """Test order calculation edge cases"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.customer = Customer.objects.create(
            user=self.user,
            name='Test Customer',
            email='test@example.com',
            phone='+1234567890'
        )
        self.category = Category.objects.create(name='Test', slug='test')

    def test_order_with_decimal_prices(self):
        """Test order calculation with various decimal prices"""
        product1 = Product.objects.create(
            name='Product 1',
            price=Decimal('9.99'),
            category=self.category,
            sku='PROD001',
            stock_quantity=100
        )
        product2 = Product.objects.create(
            name='Product 2',
            price=Decimal('15.50'),
            category=self.category,
            sku='PROD002',
            stock_quantity=100
        )
        
        order = Order.objects.create(customer=self.customer)
        
        OrderItem.objects.create(
            order=order,
            product=product1,
            quantity=3,
            unit_price=product1.price
        )
        OrderItem.objects.create(
            order=order,
            product=product2,
            quantity=2,
            unit_price=product2.price
        )
        
        total = order.calculate_total()
        expected = Decimal('9.99') * 3 + Decimal('15.50') * 2  # 29.97 + 31.00 = 60.97
        self.assertEqual(total, expected)

    def test_empty_order_calculation(self):
        """Test calculation of empty order"""
        order = Order.objects.create(customer=self.customer)
        total = order.calculate_total()
        self.assertEqual(total, Decimal('0.00'))
