from django.test import TestCase, Client
from django.urls import reverse
from userdetails.models import User
from companydetails.models import Company, DealerCustomer

class UserMappingTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a dealer company
        self.dealer_company = Company.objects.create(
            company_id="DLR001",
            company_name="Test Dealer",
            company_type=Company.CompanyType.DEALER,
            company_email="dealer@test.com"
        )
        # Create a dealer admin
        self.dealer_admin = User.objects.create_user(
            username="dealer_admin",
            email="dealer@test.com",
            password="password123",
            role="DEALER_ADMIN",
            company_relation=self.dealer_company
        )
        # Create a dealer customer
        self.dealer_customer = DealerCustomer.objects.create(
            dealer=self.dealer_company,
            customer_id="DLR001-CST0001",
            company_name="Test Customer",
            company_email="customer@test.com",
            contact_person="John Doe",
            contact_number="1234567890",
            address="Test Address",
            city="Test City",
            state="Test State",
            zip_code="123456"
        )
        # Create a company record for the dealer customer (to match my new registration logic)
        self.customer_company = Company.objects.create(
            company_id="DLR001-CST0001",
            company_name="Test Customer",
            company_email="customer@test.com",
            company_type=Company.CompanyType.CUSTOMER,
            parent_company=self.dealer_company,
            is_dealer_created=True
        )

    def test_user_creation_mapping(self):
        self.client.login(username="dealer_admin", password="password123")
        url = reverse('user_create')
        data = {
            'username': 'cust_admin',
            'email': 'cust_admin@test.com',
            'role': 'COMPANY_ADMIN',
            'company': self.dealer_customer.id, # As per prepare_relations logic
            'is_active': 'on'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        user = User.objects.get(username='cust_admin')
        self.assertEqual(user.dealer_customer_relation, self.dealer_customer)
        self.assertEqual(user.company_relation, self.dealer_company)
        self.assertEqual(user.role, 'COMPANY_ADMIN')

    def test_profile_data_fetching(self):
        # Create a user manually with the relation
        user = User.objects.create_user(
            username="test_user",
            email="test@test.com",
            password="password123",
            role="COMPANY_ADMIN",
            company_relation=self.dealer_company,
            dealer_customer_relation=self.dealer_customer
        )
        self.client.login(username="test_user", password="password123")
        url = reverse('profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.dealer_customer.company_name)
        self.assertContains(response, self.dealer_customer.contact_person)
        # Ensure it's readonly
        self.assertContains(response, 'readonly')
