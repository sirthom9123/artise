# Artise - Artisan Field Service Platform

A Django web platform for artisan and trade service businesses to manage organizations, jobs, technicians, customers, invoicing, and a public directory for customers to find and book nearby service providers.

## Features

### Authentication & Onboarding
- Email-based signup with email verification
- Onboarding flow: registration &rarr; create organization &rarr; select service category &rarr; onboard pre-defined services
- Technician invite system (admin sends invite link, technician joins with temp password)
- Forced password change for invited technicians

### Organization Management
- Business profile with name, address, contact details
- Service category assignment (Home Repairs, Automotive, Construction, Appliances, Outdoor Services)
- VAT registration toggle (15% VAT applied to invoices when enabled)
- Automatic geocoding of address via Mapbox API (latitude/longitude)

### Services
- Pre-defined service templates loaded from `mock-services.json` (organized by category and subcategory)
- Quick-add services from pre-defined list (multi-select) or add manually
- Configurable pricing: per hour, per day, or fixed rate (entire job)
- Services linked to subcategories (e.g. Plumbing, Electrical under Home Repairs)

### Job Management
- Create and assign jobs to technicians
- Job lifecycle: Scheduled &rarr; Assigned &rarr; In Progress &rarr; Completed / Cancelled
- Job checklists, before/after photo uploads
- Customer signature capture
- Technician ETA tracking (lat/lng)

### Invoicing
- Generate invoices from completed jobs
- Invoice number format: `{org_name}-{invoice_id}`
- Amount calculation based on service price type and duration
- VAT support (15% when org is VAT-registered)
- Payment plans: full, partial, or installments
- PDF invoice generation and email to customer
- Mark invoices as paid

### Customer Management
- Add and manage customers per organization
- View customer invoices and payment status
- Customer detail with job history

### Technician Management
- Invite technicians via email
- Technician list with role management
- Technicians view and manage assigned jobs

### Public Directory (`directory` app)
- Search for nearby artisans by category and subcategory
- Location-based search using Mapbox geocoding
- Interactive map showing nearby organizations
- Distance calculation using geopy
- View organization details: distance, reviews, number of jobs completed
- Select a service and book directly through the booking form
- Organization notified via email on new bookings

### Public Booking
- Booking form accessible at `/artisan/book/` or per-organization at `/artisan/book/org/<id>/`
- Job status tracking page for customers
- Leave a review after job completion

## Tech Stack

- **Backend**: Django 6.0
- **Database**: MySQL (production/staging), SQLite available for local dev
- **Frontend**: Django templates, vanilla CSS, minimal JavaScript
- **Geocoding**: Mapbox API (forward geocoding for address &rarr; lat/lng)
- **Distance**: geopy (geodesic distance calculation)
- **PDF Generation**: ReportLab + xhtml2pdf
- **Digital Signatures**: pyHanko (PDF signing)
- **Data Import/Export**: django-import-export

## Project Structure

```
artise/
├── app/                          # Django project settings & root URL config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── artisans/                     # Core application
│   ├── models.py                 # Organization, UserProfile, ServiceType, Job, Invoice, etc.
│   ├── views.py                  # Dashboard, jobs, invoices, services, booking views
│   ├── forms.py                  # Django forms
│   ├── services.py               # Email sending, geocoding helpers
│   ├── admin.py                  # Django admin configuration
│   ├── middleware.py             # Password change enforcement middleware
│   ├── context_processors.py     # Profile context processor
│   ├── urls.py                   # URL routing (/artisan/...)
│   └── management/commands/      # Management commands for seeding data
│       ├── load_services.py      # Load categories & pre-defined services from JSON
│       ├── load_artisans.py      # Load organizations from artisans.json
│       └── seed_org_users_and_services.py  # Create dummy users & link services to orgs
├── directory/                    # Public directory app
│   ├── views.py                  # Search, org list (map), org detail
│   ├── services.py               # Geocoding, distance, booking notifications
│   └── urls.py                   # URL routing (/)
├── templates/                    # HTML templates
│   ├── base.html                 # Base layout
│   ├── artisans/                 # Artisan app templates
│   │   ├── auth/                 # Login, signup, onboarding, email verification
│   │   ├── booking/              # Public booking form, status, review
│   │   ├── customers/            # Customer list, detail, form
│   │   ├── invoices/             # Invoice list, detail, form, PDF
│   │   ├── jobs/                 # Job list, detail, form
│   │   ├── services/             # Service list, add, form
│   │   ├── technicians/          # Technician list, invite
│   │   ├── dashboard.html
│   │   ├── profile.html
│   │   └── organization_edit.html
│   └── directory/                # Directory app templates
│       ├── search.html           # Category/subcategory search with location
│       ├── org_list.html         # Map view of nearby organizations
│       ├── org_detail.html       # Organization detail with services & reviews
│       └── services.html         # Service picker
├── static/                       # Static files (CSS, JS, images)
├── serviceCategory.json          # Service category & subcategory definitions
├── mock-services.json            # Pre-defined service templates (per provider type)
├── artisans.json                 # Seed data for organizations
├── requirements.txt              # Python dependencies
└── manage.py
```

## Setup

### Prerequisites

- Python 3.12+
- MySQL (or SQLite for local development)
- A Mapbox API key (for geocoding and maps)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd artise
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv

   # Windows
   .\venv\Scripts\Activate.ps1

   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secret-key-here

   # Database
   DB_NAME=artise_db
   DB_USER=root
   DB_PASSWORD=your-db-password
   DB_HOST=localhost
   DB_PORT=3306

   # Mapbox (required for geocoding and directory maps)
   MAPBOX_KEY=your-mapbox-access-token

   # Email (optional - defaults to console backend)
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.example.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@example.com
   EMAIL_HOST_PASSWORD=your-email-password
   DEFAULT_FROM_EMAIL=Artise <noreply@example.com>

   # PayFast (production only - sandbox values used in DEBUG mode)
   PAYFAST_MERCHANT_KEY=your-merchant-key
   PAYFAST_RETURN_URL=https://yourdomain.com/payment/return/
   PAYFAST_CANCEL_URL=https://yourdomain.com/payment/cancel/
   PAYFAST_NOTIFY_URL=https://yourdomain.com/payment/notify/
   PAYFAST_PASSPHRASE=your-passphrase
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser** (for Django admin)
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

8. **Open** http://127.0.0.1:8000

## Seeding Data

Load service categories, pre-defined services, sample organizations, and dummy users in order:

```bash
# 1. Load service categories and pre-defined service templates
python manage.py load_services

# 2. Load sample organizations from artisans.json (geocodes addresses via Mapbox)
python manage.py load_artisans

# 3. Create dummy users (one per org), link profiles, and create ServiceTypes
python manage.py seed_org_users_and_services
```

### Seed command options

```bash
# load_artisans: skip geocoding (useful without Mapbox key)
python manage.py load_artisans --no-geocode

# seed_org_users_and_services: custom password
python manage.py seed_org_users_and_services --password "YourPassword123!"

# seed_org_users_and_services: only create users, skip ServiceType creation
python manage.py seed_org_users_and_services --skip-services
```

### Default credentials for seeded users

All seeded users are created with the password: `SeedPass123!`

Usernames follow the pattern `{org_name_slug}_{org_id}`, for example:
- `eastview_electrical_services_16`
- `silverline_plumbing_solutions_17`
- `profix_auto_mechanics_18`

Each user is linked to their organization as an `admin` role.

## Service Categories

| Category         | Subcategories                                  |
|------------------|------------------------------------------------|
| Home Repairs     | Plumbing, Electrical, Painting, Tiling, Carpentry |
| Automotive       | Mechanical Repairs, Body Repairs, Diagnostics, Servicing |
| Construction     | Welding, Roofing, Steel Works, Renovations     |
| Appliances       | Kitchen Appliances, Laundry Appliances, Cooling Systems |
| Outdoor Services | Landscaping, Tree Services, Irrigation, Paving |

## URL Reference

### Artisan App (`/artisan/...`)

| URL | Description |
|-----|-------------|
| `/artisan/login/` | Login |
| `/artisan/signup/` | Sign up |
| `/artisan/onboarding/` | Onboarding (create org) |
| `/artisan/onboard-services/` | Select pre-defined services |
| `/artisan/` | Dashboard |
| `/artisan/profile/` | User profile |
| `/artisan/organization/` | Edit organization |
| `/artisan/services/` | Service list |
| `/artisan/services/add/` | Add service (pre-defined or manual) |
| `/artisan/jobs/` | Job list |
| `/artisan/jobs/new/` | Create job |
| `/artisan/jobs/<id>/` | Job detail |
| `/artisan/invoices/` | Invoice list |
| `/artisan/invoices/<id>/` | Invoice detail |
| `/artisan/invoices/<id>/pdf/` | Download invoice PDF |
| `/artisan/customers/` | Customer list |
| `/artisan/technicians/` | Technician list |
| `/artisan/technicians/invite/` | Invite technician |
| `/artisan/book/` | Public booking form |

### Directory App (`/`)

| URL | Description |
|-----|-------------|
| `/` | Search for artisans by category and location |
| `/services/` | Pick a service from search results |
| `/orgs/` | Map view of nearby organizations |
| `/org/<id>/` | Organization detail (services, reviews, book) |

## Models Overview

| Model | Description |
|-------|-------------|
| `ServiceCategory` | Top-level category (e.g. Home Repairs, Automotive) |
| `ServiceSubcategory` | Subcategory under a category (e.g. Plumbing, Electrical) |
| `Organization` | Business entity with address, contact info, VAT, geolocation |
| `UserProfile` | Extended user profile with role (admin/technician/customer) and org link |
| `PreDefinedService` | Service template for onboarding (from `mock-services.json`) |
| `ServiceType` | Actual service offered by an organization (pricing, subcategory) |
| `Customer` | Customer record per organization |
| `Job` | Work order with scheduling, assignment, status tracking |
| `JobChecklistItem` | Checklist items attached to a job |
| `JobPhoto` | Before/after photos for jobs |
| `JobSignature` | Customer signature capture |
| `Invoice` | Invoice for a job (amount, VAT, payment plan, status) |
| `EmailVerification` | Email verification tokens for signup |
| `TechnicianInvite` | Invite tokens for technicians to join an organization |
| `Review` | Customer review (rating + comment) for completed jobs |

## Deployment Notes

- For **cPanel/shared hosting**: `pycairo` and `rlPyCairo` have been removed from requirements as they require system-level C libraries not available on most shared hosts. PDF generation works without them.
- Set `DEBUG=False` in production to enable security headers (HSTS, secure cookies, SSL redirect).
- Configure `ALLOWED_HOSTS` in `settings.py` for your domain.
- Run `python manage.py collectstatic` for production static file serving.
- PayFast sandbox is used automatically in `DEBUG=True` mode; production credentials are loaded from `.env`.
