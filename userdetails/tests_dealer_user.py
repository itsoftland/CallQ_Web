from django.test import TestCase, Client
from django.urls import reverse
from userdetails.models import User
from companydetails.models import Company, DealerCustomer

class DealerUserCreationTest(TestCase):
    def setUp(self):
        # Create a Dealer Company
        self.dealer_company = Company.objects.create(
            company_name="Test Dealer",
            company_type="DEALER",
            company_email="dealer@example.com",
            contact_person="Dealer Person",
            contact_number="1234567890",
            address="Dealer Address",
            city="Dealer City",
            state="Dealer State",
            zip_code="123456"
        )
        
        # Create a Dealer Admin User
        self.dealer_user = User.objects.create_user(
            username="dealer_admin",
            email="dealer_admin@example.com",
            password="password123",
            role="DEALER_ADMIN",
            company_relation=self.dealer_company
        )
        
        # Create a Dealer Customer (Contact Record)
        self.dealer_customer = DealerCustomer.objects.create(
            dealer=self.dealer_company,
            customer_id="DEALER-001",
            company_name="Test Customer",
            company_email="customer@example.com",
            contact_person="Customer Person",
            contact_number="0987654321",
            address="Customer Address",
            city="Customer City",
            state="Customer State",
            zip_code="654321"
        )
        
        # Create the corresponding Company record (as if created via Register Customer)
        self.customer_company = Company.objects.create(
            company_id="DEALER-001",
            company_name="Test Customer",
            company_type="CUSTOMER",
            parent_company=self.dealer_company,
            is_dealer_created=True,
            company_email="customer@example.com",
            contact_person="Customer Person",
            contact_number="0987654321",
            address="Customer Address",
            city="Customer City",
            state="Customer State",
            zip_code="654321"
        )
        
        self.client = Client()
        self.client.login(username="dealer_admin", password="password123")
        
    def test_create_user_for_dealer_customer(self):
        """
        Test that creating a user for a dealer customer links the user to the Customer Company,
        NOT the Dealer Company.
        """
        url = reverse('user_create')
        data = {
            'email': 'new_customer_user@example.com',
            'password': 'newpassword123',
            'role': 'COMPANY_ADMIN', # Dealer selects this role usually
            'company': self.dealer_customer.id, # Form sends DealerCustomer ID for dealers
            'display_name': 'New Customer User',
            'is_web_user': 'on'
        }
        
        response = self.client.post(url, data)
        
        # Check for redirect (success)
        self.assertEqual(response.status_code, 302, "User creation failed, validation errors might exist.")
        
        # Fetch the created user
        new_user = User.objects.get(email='new_customer_user@example.com')
        
        # Assertion: User should be linked to the Customer Company
        self.assertEqual(new_user.company_relation, self.customer_company, 
                         f"User linked to {new_user.company_relation} instead of {self.customer_company}")
        
    def test_create_user_with_no_corresponding_company(self):
        """
        Test fallback: If no Company exists for the DealerCustomer, link to Dealer as fallback.
        """
        # Create a contact-only dealer customer
        contact_only = DealerCustomer.objects.create(
            dealer=self.dealer_company,
            customer_id="NO-COMPANY-001",
            company_name="Contact Only",
            company_email="contact@example.com",
            contact_person="Contact Person",
            contact_number="1111111111",
            address="Contact Address",
            city="Contact City",
            state="Contact State",
            zip_code="111111",
            country="India"
        )
        
        url = reverse('user_create')
        data = {
            'email': 'contact_user@example.com',
            'password': 'password123',
            'role': 'COMPANY_ADMIN',
            'company': contact_only.id,
            'display_name': 'Contact User',
            'is_web_user': 'on'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        new_user = User.objects.get(email='contact_user@example.com')
        
        # Fallback behavior: Linked to Dealer Company because no Customer Company exists
        self.assertEqual(new_user.company_relation, self.dealer_company)

